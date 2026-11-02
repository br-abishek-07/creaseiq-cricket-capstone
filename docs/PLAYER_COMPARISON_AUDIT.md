# Player Comparison Lab v1.0 — implementation audit

Audit date: 2 November 2026. Target: `dev-phase1-ui`. Baseline commit:
`3abc2c256b011aa8f8820f9766f07cb27ba28b56`. Work was isolated in a clean clone
on `feat/player-comparison-lab`; no pre-existing workspace edits were overwritten.

## A. Files created

| File | Purpose |
| --- | --- |
| `scripts/convert_to_parquet.py` | Reproducible conversion CLI |
| `src/__init__.py` | Extension package |
| `src/metrics/__init__.py` | Metrics package |
| `src/metrics/parquet_store.py` | Typed conversion, integrity checks, manifests and atomic cache publication |
| `src/metrics/query_engine.py` | Parameterized historical DuckDB metrics and evidence queries |
| `src/metrics/comparison_ui.py` | Comparison workspace, controls, tables, charts and evidence exports |
| `tests/test_player_comparison_engine.py` | 38 deterministic/integration test cases |
| `requirements-dev.txt` | Test installation requirements |
| `data/ipl_matches_clean_2008_2026.csv.gz` | Canonical IPL match metadata from the uploaded complete Cricsheet package |
| `data/ipl_innings_clean_2008_2026.csv.gz` | Canonical innings, target and penalty metadata from that package |
| `docs/PLAYER_COMPARISON_LAB.md` | Setup, use, formulas, windows and limitations |
| `docs/PLAYER_COMPARISON_DATA_AUDIT.json` | Exact schemas, hashes, rows, versions, source checks and test outcomes |
| `docs/PLAYER_COMPARISON_AUDIT.md` | This report |

## B. Files modified

- `app.py`: one sidebar option and an isolated lazy-import route. Optional dependency
  failures are confined to the Lab; historical filters do not affect other pages.
- `requirements.txt`: DuckDB 1.5.6 and PyArrow 23.0.1, the tested versions.
- `.gitignore`: excludes reproducible `data/parquet/` cache versions.
- `README.md`: links to the Lab guide and this audit.

Existing agent code, prompts, secrets handling, schemas, Moneyball bands, Pandas
loaders and existing source CSVs were not changed. The two additional compressed
sources total 173,924 bytes; their decompressed bytes match the uploaded ZIP.
No derived Parquet binaries are committed. No add-on package was available locally;
this implementation was reviewed and tested directly against the repository and
full cleaned Cricsheet sources.

## C. Dataset validation

| Table | Input rows | Parquet rows |
| --- | ---: | ---: |
| Matches | 1,243 | 1,243 |
| Deliveries | 295,732 | 295,732 |
| Wickets | 14,705 | 14,705 |
| Innings | 2,514 | 2,514 |

All source columns are retained; the complete input/output schemas and SHA-256
hashes are in the JSON audit. Required fields include stable player/delivery/match
IDs, dates, zero-based overs, legal/batter-ball flags, charged runs and individual
wicket flags. Keys and IDs remain VARCHAR, required counts become validated BIGINT,
match dates become DATE, and planned/target overs retain fractional capability.
Fractional integer counts, missing IDs, incompatible schemas, duplicate keys and
unresolved references are rejected. Both directions of typed row-set comparison
preserve duplicates as well as values. PyArrow independently checks Parquet row counts.

There are 805 observed player IDs and zero unresolved IDs against the existing
registry. Coverage is 2008-04-18 through 2026-05-31. The data contain 295,557 regular
and 175 super-over delivery events. Four overs contain more than six legal balls;
these are flagged and retained. Twenty-three matches have an adjusted-result method.
The archive lacks verified physical-boundary classification. No source events or
missing classifications were fabricated to fill these gaps.

## D. Cricket metrics validation

Manual tests pass for runs, balls faced, strike rate, dismissal-based average,
batter dots, legal bowling balls, charged runs, economy, credited wickets,
bowling strike rate and team-scoreless legal bowling dots. Tests cover wides,
no-balls, byes, leg-byes, penalty runs, run-outs, retired-out/retired-hurt events,
multiple wicket events, super overs, reduced targets, unusual overs and zero
or missing denominators. Non-striker dismissals are attributed to the correct ID.
Delivery totals are never multiplied by the wicket join.

Cutoff tests explicitly exclude 2023-01-01 and every subsequent observation when
that decision date is selected. Inclusive start dates and phase boundaries are
also checked. Lab bands are source overs 0–5, 6–14 and 15–19; overall retains all
regular source overs. Existing Moneyball bands are deliberately untouched.

Independent sampled reference: the [official IPL 2016 final report](https://www.iplt20.com/news/article/match-report-final-rcb-vs-srh),
read 2026-11-02. Tests match Kohli 54/35 and Warner 69/38 batting, plus Jordan
24 legal balls, 45 charged runs and three wickets. Seven fields across three
players in one match were sampled. All-player source reconciliation is not an
independent official-scorecard audit. Career averages, phase/dot conventions and
all source events have not been exhaustively externally certified.

Physical-boundary counts/rates remain unavailable for the actual archive. Tests
with explicit flags distinguish genuine/non-boundary four- and six-run events;
they do not fill the real archive with guessed flags.

## E. Executed tests and checks

| Check | Result |
| --- | --- |
| `python -m pytest tests/test_player_comparison_engine.py -q` | 38 passed, 0 failed, 0 skipped |
| `python -m pytest -q` | 158 passed, 12 failed, 0 skipped; 168 passing subtests |
| Pre-change full-suite baseline | 119 passed, 13 failed; 168 passing subtests |
| New failure IDs compared with baseline | 0 |
| Syntax compilation | Passed for app, src and scripts |
| DuckDB/PyArrow/Streamlit/Pandas imports | Passed on Python 3.12: 1.5.6 / 23.0.1 / 1.66.1 / 2.2.3 |
| Canonical source conversion and representative real queries | Passed |
| Browser checks | Desktop 1440×1000 and mobile 390×844; no application exception panels or page errors |
| Paid API tests | None; agent requests use mocks |
| Blocked automated checks | None of the listed checks was blocked |

The full repository suite is **not green**. The twelve remaining failures already
failed before this work and target production-only UI features or old page names:

- `tests/test_accuracy.py::DossierInterface::test_overview_and_ambiguous_name`
- `tests/test_runtime.py::ReleaseRuntime::test_01_previous_package_cannot_break_home_or_brief`
- `tests/test_runtime.py::ReleaseRuntime::test_06_code_update_invalidates_data_cache_in_same_session`
- `tests/test_startup.py::Startup::test_cached_generic_modules_do_not_break_startup`
- `tests/test_startup.py::Startup::test_startup_from_another_working_directory`
- The seven tests in `tests/test_ui.py` (`Interface::test_01` through `test_07`).

They expect such production routes as “Home”, “Decision desk”, “Player dossier”
and “Squad & auction scenarios”, while this branch uses the Phase 3 workspaces.
These tests were neither deleted nor marked skipped to hide the failures.
The baseline also had an intermittent SQLite database-lock failure in
`Release::test_42_concurrent_quota_limit`; it did not recur in the final run.
That storage implementation was not changed. The third-party pytest plugin emits
one deprecation warning. Failure IDs and baseline differences are recorded in JSON.

## F. Existing-agent compatibility

All 61 current dev-branch regression tests passed as part of the full suite.
They cover the four specialist prompts, shared JSON parsing and citation checks,
provider error handling, report cache/staleness, Moneyball, squad identities,
matchup arithmetic, Home status and warm-process agent/data-module imports.
The new UI test also visits each of the original five workspaces after changing
Lab filters, and asserts no OpenAI client calls while browsing the Lab.

This establishes local compatibility with mocked provider responses, not live
DeepSeek endpoint health or report quality. No new AI agent or evidence schema
was introduced.

## G. Remaining limitations and performance

- The twelve pre-existing production-UI tests need a separate test-suite alignment
  decision; this change does not present the whole repository as green.
- Boundary classification and exhaustive independent scorecard certification are
  unavailable. Original match JSON was not available to recover boundary flags.
- Reduced matches are included with warnings. Official powerplay reconstruction,
  Bayesian shrinkage, bootstrap intervals, peer percentiles and acquisition
  rankings remain postponed.
- Event previews cap at 200 deliveries and 200 wickets; totals use all selected
  observations. Complete match metadata/series and scope/hash exports are available.
- First-run conversion needs writable cache storage and temporary memory. A local
  cold conversion measured 15.354 seconds and peak process RSS of 517.8 MiB; a
  two-player query measured 0.743 seconds and hash-cache validation 0.009 seconds.
  These illustrative measurements occurred alongside local work and are not hosted
  latency, total-app memory guarantees or an SLA. Versions are retained on disk;
  unused derived versions can be removed while the app is stopped.
- Local desktop/mobile rendering was checked. No claim is made about the public
  Streamlit deployment until its hosted rebuild and runtime are actually verified.

## H. GitHub changes

The reviewed feature targets `dev-phase1-ui` with commit message:
`feat: integrate deterministic DuckDB Player Comparison Lab`.
The delivery response provides the final commit SHA and link. `main` is unchanged.
The existing production submission ZIP is not rebuilt by this feature integration.
