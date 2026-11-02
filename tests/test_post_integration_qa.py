"""QA regression cases for real cache and evidence-export defects."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_player_comparison_engine import fixtures,store,wicket,A,B,C
from src.metrics.parquet_store import ensure_parquet,ComparisonDataError
from src.metrics.query_engine import ComparisonEngine
import duckdb
import pytest

@pytest.mark.parametrize('damage',['array','string','missing_warnings','malformed_tables','source_hash'])
def test_bad_cache_manifest_recovers(tmp_path,damage):
    engine=store(tmp_path,fixtures())
    original=engine.manifest
    if damage=='array':bad=[]
    elif damage=='string':bad='unexpected'
    elif damage=='missing_warnings':bad={k:v for k,v in original.items() if k!='warnings'}
    elif damage=='malformed_tables':bad={**original,'tables':{key:[] for key in original['tables']}}
    else:
        bad=json.loads(json.dumps(original));bad['tables']['deliveries']['source_sha256']='wrong'
    (engine.store/'manifest.json').write_text(json.dumps(bad))
    repaired=ComparisonEngine.from_sources(tmp_path)
    assert repaired.manifest==original or repaired.manifest['tables']==original['tables']
    assert repaired.manifest['warnings']==original['warnings']

def test_cached_engine_rejects_modified_parquet(tmp_path):
    engine=store(tmp_path,fixtures())
    engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01')
    path=engine.store/'deliveries.parquet'
    with duckdb.connect() as con:
        con.execute('CREATE TABLE changed AS SELECT * FROM read_parquet(?)',[str(path)])
        con.execute('UPDATE changed SET batter_runs=99 WHERE delivery_id=(SELECT min(delivery_id) FROM changed)')
        altered=tmp_path/'altered.parquet';con.table('changed').write_parquet(str(altered))
    altered.replace(path)
    with pytest.raises(ComparisonDataError,match='changed|modified|integrity'):
        engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01')
    repaired=ComparisonEngine.from_sources(tmp_path)
    assert repaired.get_batting_comparison(A,B,'2022-01-01','2023-01-01').iloc[0].runs==12

def test_batting_export_includes_dismissal_without_strike(tmp_path):
    frames=fixtures()
    frames['wickets']=wicket(frames['wickets'],frames['deliveries'].iloc[8],B,'run out')
    engine=store(tmp_path,frames)
    summary=engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01').set_index('player_id')
    series=engine.evidence(A,B,'2022-01-01','2023-01-01')['series']
    assert B in series.player_id.tolist()
    row=series.loc[series.player_id.eq(B)].iloc[0]
    assert (row.runs,row.balls_faced,row.dismissals)==(0,0,1)
    assert series.groupby('player_id').dismissals.sum()[B]==summary.loc[B,'dismissals']

def test_bowling_export_reconciles_credit_without_multiplying_runs(tmp_path):
    frames=fixtures();event=frames['deliveries'].iloc[8]
    frames['wickets']=wicket(frames['wickets'],event,B,'run out')
    frames['wickets']=wicket(frames['wickets'],event,A,'caught',1)
    engine=store(tmp_path,frames)
    series=engine.evidence(C,B,'2022-01-01','2023-01-01',mode='Bowling')['series']
    row=series.loc[series.player_id.eq(C)].iloc[0]
    assert (row.runs_charged,row.legal_balls,row.wickets)==(14,7,1)
