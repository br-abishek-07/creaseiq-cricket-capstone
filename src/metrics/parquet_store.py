"""Validated, versioned CSV-to-Parquet conversion with atomic publication."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from threading import RLock

import duckdb
import pyarrow.parquet as pq

VERSION = "comparison-lab-1"
ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "matches": "ipl_matches_clean_2008_2026.csv",
    "deliveries": "ipl_deliveries_clean_2008_2026.csv",
    "wickets": "ipl_wickets_clean_2008_2026.csv",
    "innings": "ipl_innings_clean_2008_2026.csv",
}
REQUIRED = {
    "matches": {"match_id", "date", "match_overs", "balls_per_over", "method_raw"},
    "deliveries": {"delivery_id", "match_id", "match_date", "season_year", "innings_number", "is_super_over",
        "striker_id", "bowler_id", "non_striker_id", "striker_name_original", "bowler_name_original", "delivery_sequence_in_over", "over_number_zero_based", "batter_runs", "extras_total", "total_runs",
        "wides", "noballs", "byes", "legbyes", "penalty_extras", "is_legal_delivery", "is_ball_faced_by_batter", "bowler_runs_charged"},
    "wickets": {"wicket_id", "delivery_id", "match_id", "innings_number", "is_super_over", "player_out_id",
                "dismissal_kind", "is_dismissal", "credited_to_bowler"},
    "innings": {"innings_id", "match_id", "innings_number", "is_super_over", "target_overs_recorded"},
}
INTEGERS = {"season_year", "innings_number", "is_super_over", "over_number_zero_based", "delivery_sequence_in_over",
    "batter_runs", "extras_total", "total_runs", "wides", "noballs", "byes", "legbyes", "penalty_extras",
    "is_legal_delivery", "is_ball_faced_by_batter", "bowler_runs_charged", "wicket_events", "is_dismissal", "credited_to_bowler",
    "balls_per_over", "legal_balls", "delivery_events", "runs_from_deliveries", "penalty_runs_pre", "penalty_runs_post",
    "total_runs_including_innings_penalties", "extras_from_deliveries", "wickets_excluding_retired_hurt"}
DOUBLES = {"match_overs", "target_overs_recorded", "target_runs_recorded", "over_count_recorded"}
_LOCK = RLock()


class ComparisonDataError(ValueError):
    """Source or derived data do not meet the comparison contract."""


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_paths(data_dir):
    result = {}
    for table, filename in SOURCES.items():
        for folder in [Path(data_dir), Path(data_dir) / "IPL_CRICSHEET_VERIFIED_CLEAN_2008_2026"]:
            for suffix in ["", ".gz"]:
                path = folder / (filename + suffix)
                if path.is_file():
                    result[table] = path
                    break
            if table in result:
                break
        if table not in result:
            raise ComparisonDataError(f"Missing comparison source: {filename} (CSV or gzip).")
    return result


def _assert_zero(con, sql, message):
    count = con.execute(sql).fetchone()[0]
    if count:
        raise ComparisonDataError(f"{message}: {count} affected rows.")


def validate_relations(con):
    """Validate primary/foreign keys, cricket flags and cross-table attribution."""
    for table, key in [("matches", "match_id"), ("deliveries", "delivery_id"), ("wickets", "wicket_id"), ("innings", "innings_id")]:
        _assert_zero(con, f"SELECT count(*) FROM {table} WHERE {key} IS NULL OR trim({key})=''", f"Missing {table} key")
        _assert_zero(con, f"SELECT count(*)-count(DISTINCT {key}) FROM {table}", f"Duplicate {table} key")
    for table in ["deliveries", "wickets", "innings"]:
        _assert_zero(con, f"SELECT count(*) FROM {table} t LEFT JOIN matches m USING(match_id) WHERE m.match_id IS NULL", f"Unresolved {table} match")
    _assert_zero(con, "SELECT count(*) FROM deliveries d LEFT JOIN innings i ON i.innings_id=d.match_id||':'||d.innings_number WHERE i.innings_id IS NULL OR i.is_super_over<>d.is_super_over", "Delivery innings mismatch")
    _assert_zero(con, "SELECT count(*) FROM wickets w LEFT JOIN deliveries d USING(delivery_id) WHERE d.delivery_id IS NULL OR w.match_id<>d.match_id OR w.innings_number<>d.innings_number OR w.is_super_over<>d.is_super_over", "Wicket foreign key or innings mismatch")
    for col in ["striker_id", "bowler_id", "non_striker_id"]:
        _assert_zero(con, f"SELECT count(*) FROM deliveries WHERE {col} IS NULL OR trim({col})=''", f"Missing {col}")
    _assert_zero(con, "SELECT count(*) FROM wickets WHERE player_out_id IS NULL OR trim(player_out_id)=''", "Missing dismissed player ID")
    for table, columns in [("deliveries", REQUIRED["deliveries"] & INTEGERS), ("wickets", REQUIRED["wickets"] & INTEGERS)]:
        for col in columns:
            _assert_zero(con, f"SELECT count(*) FROM {table} WHERE {col} IS NULL OR {col}<0", f"Invalid {table}.{col}")
    for table, columns in [("deliveries", ["is_super_over", "is_legal_delivery", "is_ball_faced_by_batter"]), ("wickets", ["is_super_over", "is_dismissal", "credited_to_bowler"])]:
        for col in columns:
            _assert_zero(con, f"SELECT count(*) FROM {table} WHERE {col} NOT IN (0,1)", f"Non-binary {col}")
    _assert_zero(con, "SELECT count(*) FROM matches WHERE date IS NULL OR balls_per_over IS NULL OR balls_per_over<>6", "Missing date or unsupported balls-per-over")
    _assert_zero(con, "SELECT count(*) FROM deliveries d JOIN matches m USING(match_id) WHERE d.match_date IS NULL OR d.match_date<>m.date", "Delivery date mismatch")
    _assert_zero(con, "SELECT count(*) FROM deliveries WHERE is_legal_delivery<>CASE WHEN wides=0 AND noballs=0 THEN 1 ELSE 0 END OR is_ball_faced_by_batter<>CASE WHEN wides=0 THEN 1 ELSE 0 END", "Ball flag mismatch")
    _assert_zero(con, "SELECT count(*) FROM deliveries WHERE bowler_runs_charged<>batter_runs+wides+noballs OR total_runs<>batter_runs+extras_total OR extras_total<>wides+noballs+byes+legbyes+penalty_extras", "Runs or extras mismatch")
    # Retired hurt / obstructing / run out / retired out do not credit the bowler.
    _assert_zero(con, "SELECT count(*) FROM wickets WHERE credited_to_bowler<>CASE WHEN dismissal_kind IN ('bowled','caught','caught and bowled','lbw','stumped','hit wicket') THEN 1 ELSE 0 END OR is_dismissal<>CASE WHEN dismissal_kind='retired hurt' THEN 0 ELSE 1 END", "Inconsistent dismissal flags")
    _assert_zero(con, "SELECT count(*) FROM wickets w JOIN deliveries d USING(delivery_id) WHERE w.player_out_id NOT IN (d.striker_id,d.non_striker_id)", "Dismissal ID not on crease")
    if "is_boundary" in [r[0] for r in con.execute("DESCRIBE deliveries").fetchall()]:
        _assert_zero(con, "SELECT count(*) FROM deliveries WHERE is_boundary IS NULL OR (is_boundary AND batter_runs NOT IN(4,6))", "Invalid verified boundary classification")


def _valid_cached_manifest(manifest, target, version, converter_hash, source_hashes):
    """A JSON file is not a valid manifest merely because it can be decoded."""
    if not isinstance(manifest, dict):
        return False
    if (manifest.get("dataset_version") != version
            or manifest.get("converter_sha256") != converter_hash
            or manifest.get("converter_version") != VERSION):
        return False
    tables = manifest.get("tables")
    warnings = manifest.get("warnings")
    if not isinstance(tables, dict) or set(tables) != set(SOURCES) or not isinstance(warnings, dict):
        return False
    for key in ["overs_with_more_than_six_legal_balls", "regular_events_outside_standard_windows"]:
        if type(warnings.get(key)) is not int or warnings[key] < 0:
            return False
    if type(warnings.get("missing_boundary_classification")) is not bool:
        return False
    for key, meta in tables.items():
        if not isinstance(meta, dict) or meta.get("source_sha256") != source_hashes[key]:
            return False
        count = meta.get("input_rows")
        if type(count) is not int or count < 0 or meta.get("output_rows") != count:
            return False
        if not isinstance(meta.get("schema"), list) or not meta["schema"]:
            return False
        path = target / f"{key}.parquet"
        if not path.is_file() or sha256_file(path) != meta.get("parquet_sha256"):
            return False
    return True


def ensure_parquet(data_dir=None, output_dir=None):
    """Create a hash-versioned store on first use; keep complete prior versions.

    CSVs are streamed by DuckDB. No shared connection crosses Streamlit sessions.
    Each build is validated and renamed atomically. Same-process builds serialize;
    process-level locking also protects workers sharing the output directory.
    """
    data_dir = Path(data_dir) if data_dir else ROOT / "data"
    out = Path(output_dir) if output_dir else data_dir / "parquet"
    paths = source_paths(data_dir)
    hashes = {k: sha256_file(v) for k, v in paths.items()}
    converter_hash = sha256_file(__file__)
    version = hashlib.sha256(json.dumps({"engine": VERSION, "converter_sha256": converter_hash, "sources": hashes}, sort_keys=True).encode()).hexdigest()
    target = out / version
    try:
        out.mkdir(parents=True, exist_ok=True)
        with _LOCK, _process_lock(out):
            manifest_path = target / "manifest.json"
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text())
                    valid = _valid_cached_manifest(manifest, target, version, converter_hash, hashes)
                except (OSError, ValueError, KeyError, TypeError):
                    valid = False
                if valid:
                    return target, manifest
            stage = Path(tempfile.mkdtemp(prefix=".building-", dir=out))
            try:
                tables = {}
                with duckdb.connect() as con:
                    con.execute("SET memory_limit='256MB'")
                    con.execute("SET threads=2")
                    for table, path in paths.items():
                        raw = con.read_csv(str(path), header=True, all_varchar=True, null_padding=False)
                        cols = raw.columns
                        missing = REQUIRED[table] - set(cols)
                        if missing:
                            raise ComparisonDataError(f"Incompatible {table} schema; missing: {', '.join(sorted(missing))}")
                        raw.create_view("raw", replace=True)
                        for col in set(cols) & INTEGERS:
                            number = f"TRY_CAST({quote(col)} AS DOUBLE)"
                            _assert_zero(con, f"SELECT count(*) FROM raw WHERE {quote(col)} IS NOT NULL AND ({number} IS NULL OR NOT isfinite({number}) OR {number}<>floor({number}))", f"Non-integer {table}.{col}")
                        expressions = []
                        for col in cols:
                            typ = "BIGINT" if col in INTEGERS else "DOUBLE" if col in DOUBLES else "DATE" if col in ["date", "match_date"] else "BOOLEAN" if col=="is_boundary" else "VARCHAR"
                            expressions.append(f"CAST({quote(col)} AS {typ}) AS {quote(col)}")
                        con.sql("SELECT " + ", ".join(expressions) + " FROM raw").create_view("typed", replace=True)
                        destination = stage / f"{table}.parquet"
                        con.table("typed").write_parquet(str(destination), compression="zstd")
                        original_count = con.table("typed").count("*").fetchone()[0]
                        if pq.read_metadata(destination).num_rows != original_count:
                            raise ComparisonDataError(f"{table} PyArrow row-count verification failed.")
                        con.read_parquet(str(destination)).create_view("roundtrip", replace=True)
                        _assert_zero(con, "SELECT count(*) FROM ((SELECT * FROM typed EXCEPT ALL SELECT * FROM roundtrip) UNION ALL (SELECT * FROM roundtrip EXCEPT ALL SELECT * FROM typed))", f"{table} Parquet round-trip mismatch")
                        con.read_parquet(str(destination)).create_view(table, replace=True)
                        tables[table] = {"source": path.name, "input_rows": original_count, "output_rows": con.table(table).count("*").fetchone()[0],
                                         "source_sha256": hashes[table], "parquet_sha256": sha256_file(destination),
                                         "schema": [{"name":r[0], "type":r[1]} for r in con.execute(f"DESCRIBE {table}").fetchall()]}
                    validate_relations(con)
                    _assert_zero(con, "SELECT count(*) FROM innings WHERE innings_id<>match_id||':'||innings_number", "Innings key mismatch")
                    warnings = {
                        "overs_with_more_than_six_legal_balls": con.sql("SELECT count(*) FROM (SELECT match_id,innings_number,over_number_zero_based FROM deliveries GROUP BY ALL HAVING sum(is_legal_delivery)>6)").fetchone()[0],
                        "regular_events_outside_standard_windows": con.sql("SELECT count(*) FROM deliveries WHERE is_super_over=0 AND over_number_zero_based>19").fetchone()[0],
                        "missing_boundary_classification": "is_boundary" not in {r[0] for r in con.execute("DESCRIBE deliveries").fetchall()},
                    }
                if any(sha256_file(paths[key]) != digest for key, digest in hashes.items()):
                    raise ComparisonDataError("Source files changed during conversion; retry with a stable source snapshot.")
                manifest = {"dataset_version": version, "converter_version": VERSION, "converter_sha256": converter_hash, "created_utc": datetime.now(timezone.utc).isoformat(),
                            "tables": tables, "validation": "passed: keys, references, dates, flags, run arithmetic and exact typed row round-trip", "warnings": warnings}
                (stage / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
                if target.exists():
                    shutil.rmtree(target)  # only a hash-matched corrupt derived cache; never source data
                stage.rename(target)
            except Exception:
                shutil.rmtree(stage, ignore_errors=True)
                raise
            return target, manifest
    except (duckdb.Error, OSError, KeyError, json.JSONDecodeError) as exc:
        raise ComparisonDataError(f"Could not prepare comparison data: {exc}") from None


@contextmanager
def _process_lock(out):
    # Streamlit Cloud uses Linux. The in-process lock remains available on Windows.
    handle = (out / ".conversion.lock").open("a+b")
    try:
        if os.name == "posix":
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        handle.close()
