"""Hand-calculated cricket edge cases, source integrity and deterministic UI."""
from datetime import date
import gzip
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.metrics.parquet_store import ComparisonDataError, SOURCES, ensure_parquet
from src.metrics.query_engine import ComparisonEngine, PHASES

A, B, C, D = 'aaaaaaaa', 'bbbbbbbb', 'cccccccc', 'dddddddd'


def fixtures():
    matches=pd.DataFrame([{'match_id':mid,'date':day,'match_overs':20,'balls_per_over':6,'method_raw':''}
                          for mid,day in [('m1','2022-12-31'),('m2','2023-01-01'),('m3','2024-05-01')]])
    rows=[]
    def event(mid,day,num,runs=0,wides=0,noballs=0,byes=0,legbyes=0,penalty=0,over=0,superover=0):
        rows.append(dict(delivery_id=f'{mid}:{2 if superover else 1}:{over}:{num}',match_id=mid,match_date=day,season_year=int(day[:4]),
            innings_number=2 if superover else 1,is_super_over=superover,striker_id=A,bowler_id=C,non_striker_id=B,
            striker_name_original='Same Name',bowler_name_original='Bowler',over_number_zero_based=over,delivery_sequence_in_over=num,
            batter_runs=runs,extras_total=wides+noballs+byes+legbyes+penalty,total_runs=runs+wides+noballs+byes+legbyes+penalty,
            wides=wides,noballs=noballs,byes=byes,legbyes=legbyes,penalty_extras=penalty,
            is_legal_delivery=int(not(wides or noballs)),is_ball_faced_by_batter=int(not wides),bowler_runs_charged=runs+wides+noballs))
    event('m1','2022-12-31',1)
    event('m1','2022-12-31',2,wides=1)
    event('m1','2022-12-31',3,4,noballs=1)
    event('m1','2022-12-31',4,byes=2)
    event('m1','2022-12-31',5,legbyes=1)
    event('m1','2022-12-31',6,penalty=5)
    event('m1','2022-12-31',7,4)
    event('m1','2022-12-31',8,4)
    event('m1','2022-12-31',9)  # seventh legal ball in the source over, retained
    event('m1','2022-12-31',1,6,superover=1)
    event('m2','2023-01-01',1,4)
    event('m3','2024-05-01',1,1)
    deliveries=pd.DataFrame(rows)
    wickets=pd.DataFrame(columns=['wicket_id','delivery_id','match_id','innings_number','is_super_over',
                                  'player_out_id','dismissal_kind','is_dismissal','credited_to_bowler'])
    innings=pd.DataFrame([dict(innings_id=f'{mid}:{n}',match_id=mid,innings_number=n,is_super_over=int(n==2),target_overs_recorded=None)
                         for mid,n in [('m1',1),('m1',2),('m2',1),('m3',1)]])
    return {'matches':matches,'deliveries':deliveries,'wickets':wickets,'innings':innings}


def store(tmp, frames):
    tmp=Path(tmp);tmp.mkdir(exist_ok=True)
    for name,frame in frames.items():frame.to_csv(tmp/(SOURCES[name]+'.gz'),index=False,compression='gzip')
    return ComparisonEngine.from_sources(tmp)


def wicket(frame,delivery,who,kind,credited=0,dismissed=1):
    row={'wicket_id':delivery.delivery_id+':'+str(len(frame)+1),'delivery_id':delivery.delivery_id,
         'match_id':delivery.match_id,'innings_number':int(delivery.innings_number),'is_super_over':int(delivery.is_super_over),
         'player_out_id':who,'dismissal_kind':kind,'is_dismissal':dismissed,'credited_to_bowler':credited}
    return pd.concat([frame,pd.DataFrame([row])],ignore_index=True)


@pytest.fixture
def synthetic(tmp_path):
    return store(tmp_path,fixtures())


def test_manual_batting_wides_noballs_byes_legbyes_penalties(synthetic):
    a,b=synthetic.get_batting_comparison(A,B,'2022-01-01','2023-01-01').to_dict('records')
    assert (a['runs'],a['balls_faced'],a['dot_balls'],a['matches'],a['innings'])==(12,8,5,1,1)
    assert a['strike_rate']==150
    assert a['dot_ball_percentage']==62.5
    assert pd.isna(a['batting_average'])
    assert b['matches']==0 and pd.isna(b['strike_rate'])
    assert pd.isna(a['boundary_count']) and pd.isna(a['boundary_percentage'])


def test_manual_bowling_legal_dots_charge_and_economy(synthetic):
    a,b=synthetic.get_bowling_comparison(C,B,'2022-01-01','2023-01-01').to_dict('records')
    assert (a['legal_balls'],a['runs_charged'],a['dot_balls'])==(7,14,2)
    assert a['economy']==12
    assert a['dot_ball_percentage']==pytest.approx(200/7)
    assert pd.isna(a['bowling_strike_rate'])
    assert b['legal_balls']==0 and pd.isna(b['economy'])


@pytest.mark.parametrize('kind,dismissed,credited',[('run out',1,0),('retired out',1,0),('retired hurt',0,0),('caught',1,1),('bowled',1,1)])
def test_dismissal_attribution_and_credit(tmp_path,kind,dismissed,credited):
    frames=fixtures();last=frames['deliveries'].iloc[8]
    frames['wickets']=wicket(frames['wickets'],last,A,kind,credited,dismissed)
    engine=store(tmp_path,frames)
    batting=engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01').iloc[0]
    bowling=engine.get_bowling_comparison(C,B,'2022-01-01','2023-01-01').iloc[0]
    assert batting.dismissals==dismissed
    assert (batting.batting_average==12) if dismissed else pd.isna(batting.batting_average)
    assert bowling.wickets==credited
    assert (bowling.bowling_strike_rate==7) if credited else pd.isna(bowling.bowling_strike_rate)


def test_non_striker_runout_and_multiple_wickets_do_not_duplicate_runs(tmp_path):
    frames=fixtures();last=frames['deliveries'].iloc[8]
    frames['wickets']=wicket(frames['wickets'],last,B,'run out')
    frames['wickets']=wicket(frames['wickets'],last,A,'caught',1)
    frames['wickets']=wicket(frames['wickets'],frames['deliveries'].iloc[9],A,'bowled',1)
    engine=store(tmp_path,frames)
    a,b=engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01').to_dict('records')
    assert (a['runs'],a['balls_faced'],a['dismissals'])==(12,8,1)
    assert b['runs']==0 and b['dismissals']==1 and b['batting_average']==0 and b['innings']==1
    bowl=engine.get_bowling_comparison(C,B,'2022-01-01','2023-01-01').iloc[0]
    assert (bowl.runs_charged,bowl.legal_balls,bowl.wickets)==(14,7,1)


def test_exact_historical_cutoff_and_evidence(synthetic):
    before=synthetic.get_batting_comparison(A,B,'2022-01-01','2023-01-01').iloc[0]
    after=synthetic.get_batting_comparison(A,B,'2023-01-01','2023-01-02').iloc[0]
    assert before.runs==12 and after.runs==4
    evidence=synthetic.evidence(A,B,'2022-01-01','2023-01-01')
    assert set(evidence['matches'].match_id)=={'m1'}
    assert evidence['deliveries'].match_date.max()<pd.Timestamp('2023-01-01')
    assert not evidence['deliveries'].is_super_over.any()


def test_phase_boundaries_and_shortened_matches_retained(tmp_path):
    frames=fixtures();frames['matches'].loc[0,['match_overs','method_raw']]=[5,'D/L']
    frames['innings'].loc[0,'target_overs_recorded']=5
    d=frames['deliveries'].iloc[[0]].copy()
    additions=[]
    for i,over in enumerate([5,6,14,15,19,20]):
        item=d.copy();item['over_number_zero_based']=over;item['delivery_id']=f'm1:1:{over}:1';item['batter_runs']=1;item['total_runs']=1;item['bowler_runs_charged']=1
        additions.append(item)
    frames['deliveries']=pd.concat([frames['deliveries'],*additions],ignore_index=True)
    engine=store(tmp_path,frames)
    runs=[engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01',phase).iloc[0].runs for phase in PHASES]
    assert runs==[18,13,2,2]  # over 20 remains only in overall, never silently dropped
    evidence=engine.evidence(A,B,'2022-01-01','2023-01-01')
    assert evidence['matches'].iloc[0].reduced_target_recorded
    assert engine.manifest['warnings']['regular_events_outside_standard_windows']==1


@pytest.mark.parametrize("value", [4,6])
def test_verified_boundary_flag_distinguishes_non_boundary_runs(tmp_path,value):
    frames=fixtures();frames['deliveries']['is_boundary']=False
    frames['deliveries'].loc[[6,7],['batter_runs','total_runs','bowler_runs_charged']]=value
    frames['deliveries'].loc[6,'is_boundary']=True  # the next four was completed runs, not a boundary
    engine=store(tmp_path,frames)
    a=engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01').iloc[0]
    assert a.boundary_count==1 and a.boundary_percentage==12.5


@pytest.mark.parametrize('error',['duplicate_delivery','duplicate_match','missing_id','invalid_flag','bad_foreign_key','bad_schema','fractional_runs','missing_wicket_fk','duplicate_wicket'])
def test_reject_invalid_integrity(tmp_path,error):
    f=fixtures()
    if error=='duplicate_delivery':f['deliveries']=pd.concat([f['deliveries'],f['deliveries'].iloc[[0]]])
    elif error=='duplicate_match':f['matches']=pd.concat([f['matches'],f['matches'].iloc[[0]]])
    elif error=='missing_id':f['deliveries'].loc[0,'striker_id']=None
    elif error=='invalid_flag':f['deliveries'].loc[0,'is_legal_delivery']=2
    elif error=='bad_foreign_key':f['deliveries'].loc[0,'match_id']='missing'
    elif error=='bad_schema':f['deliveries']=f['deliveries'].drop(columns='bowler_runs_charged')
    elif error in ['missing_wicket_fk','duplicate_wicket']:
        f['wickets']=wicket(f['wickets'],f['deliveries'].iloc[0],A,'caught',1)
        if error=='missing_wicket_fk':f['wickets'].loc[0,'delivery_id']='nonexistent'
        else:f['wickets']=pd.concat([f['wickets'],f['wickets']],ignore_index=True)
    elif error=='fractional_runs':f['deliveries']['batter_runs']=f['deliveries'].batter_runs.astype(float);f['deliveries'].loc[0,'batter_runs']=0.5
    with pytest.raises(ComparisonDataError):store(tmp_path,f)


@pytest.mark.parametrize('a,b,start,cutoff,phase',[(A,A,'2022-01-01','2023-01-01','Overall'),('',B,'2022-01-01','2023-01-01','Overall'),
    ('unknown',B,'2022-01-01','2023-01-01','Overall'),("' OR 1=1 --",B,'2022-01-01','2023-01-01','Overall'),
    (A,B,'invalid','2023-01-01','Overall'),(A,B,'2023-01-01','2023-01-01','Overall'),(A,B,'2022-01-01','2023-01-01','invalid')])
def test_invalid_inputs_are_rejected(synthetic,a,b,start,cutoff,phase):
    with pytest.raises(ComparisonDataError):synthetic.get_batting_comparison(a,b,start,cutoff,phase)


def test_empty_window_and_missing_parquet(synthetic):
    result=synthetic.get_batting_comparison(A,B,'2000-01-01','2001-01-01')
    assert result.runs.eq(0).all() and result.strike_rate.isna().all()
    (synthetic.store/'deliveries.parquet').unlink()
    with pytest.raises(ComparisonDataError):ComparisonEngine(synthetic.store,synthetic.manifest)
    repaired=ComparisonEngine.from_sources(synthetic.store.parents[1])
    assert repaired.store==synthetic.store and (repaired.store/'deliveries.parquet').is_file()


def test_round_trip_cache_and_csv_schema_manifest(synthetic):
    manifest=synthetic.manifest
    assert all(t['input_rows']==t['output_rows'] for t in manifest['tables'].values())
    assert manifest['warnings']['overs_with_more_than_six_legal_balls']==1
    with synthetic.connect() as con:
        assert con.execute('SELECT count(*) FROM deliveries').fetchone()[0]==12
        assert dict(con.execute('DESCRIBE deliveries').fetchall()[i][:2] for i in range(len(con.execute('DESCRIBE deliveries').fetchall())))['match_date']=='DATE'
    path,again=ensure_parquet(synthetic.store.parents[1])
    assert path==synthetic.store and again==manifest


@pytest.fixture(scope='module')
def real_engine():
    return ComparisonEngine.from_sources()


def test_real_rows_sampled_official_match_report(real_engine):
    # Official IPL report, read 2026-11-02; independent of the Cricsheet archive.
    # https://www.iplt20.com/news/article/match-report-final-rcb-vs-srh
    players=real_engine.players()
    by_name={name:pid for pid,name in players.items()}
    assert 'Virat Kohli' in by_name
    a,b=real_engine.get_batting_comparison('ba607b88','dcce6f09','2016-05-29','2016-05-30').to_dict('records')
    assert (a['runs'],a['balls_faced'])==(54,35)
    assert (b['runs'],b['balls_faced'])==(69,38)
    jordan='ffe699c0'
    bowl=real_engine.get_bowling_comparison(jordan,'ba607b88','2016-05-29','2016-05-30').iloc[0]
    assert (bowl.legal_balls,bowl.runs_charged,bowl.wickets)==(24,45,3)


def test_real_data_rows_cutoff_and_registry(real_engine):
    assert {k:v['input_rows'] for k,v in real_engine.manifest['tables'].items()}=={'matches':1243,'deliveries':295732,'wickets':14705,'innings':2514}
    evidence=real_engine.evidence('ba607b88','740742ef','2008-01-01','2023-01-01')
    assert (evidence['matches'].date<pd.Timestamp('2023-01-01')).all()
    assert evidence['deliveries'].match_date.max()<pd.Timestamp('2023-01-01')
    assert evidence['delivery_count']>len(evidence['deliveries'])==200
    alltime=real_engine.get_batting_comparison('ba607b88','740742ef','2008-01-01','2027-01-01').iloc[0]
    assert (alltime.runs,alltime.balls_faced)==(9336,6926)  # source reconciliation, not independent certification
    assert 'ba607b88' in real_engine.players()


def test_ui_no_ai_calls_cutoff_mode_and_existing_workspaces():
    with patch('openai.OpenAI') as client:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        app.sidebar.radio[0].set_value('Player Comparison Lab').run()
        assert not app.exception and not app.error
        assert len(app.metric)==16
        assert app.selectbox[0].value!=app.selectbox[1].value
        app.date_input[1].set_value(date(2023,1,1)).run()
        assert not app.exception and not app.error
        next(r for r in app.radio if r.label=='Comparison type').set_value('Bowling').run()
        app.selectbox[2].set_value('Death overs (16–20)').run()
        assert not app.exception and not app.error
        assert any(m.label=='Economy' for m in app.metric)
        app.date_input[0].set_value(date(2024,1,1)).run()
        assert not app.exception and any('Start date must' in e.value for e in app.error)
        for route in ['Home/Overview','Player Profile','Team Matchups','Auction Trends','Squad Analysis']:
            app.sidebar.radio[0].set_value(route).run()
            assert not app.exception and not app.error,route
        client.assert_not_called()


def test_genuine_zero_rates_and_zero_dismissal_exposure(tmp_path):
    frames=fixtures();frames['deliveries']=frames['deliveries'].iloc[[0]].copy()
    engine=store(tmp_path,frames)
    assert engine.get_batting_comparison(A,B,'2022-01-01','2023-01-01').iloc[0].strike_rate==0
    assert engine.get_bowling_comparison(C,B,'2022-01-01','2023-01-01').iloc[0].economy==0


def test_ui_missing_optional_sources_and_dependencies_preserves_other_pages():
    from src.metrics import comparison_ui
    with patch.object(comparison_ui,'source_paths',side_effect=ComparisonDataError('Fixture missing comparison source')):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        app.sidebar.radio[0].set_value('Player Comparison Lab').run()
        assert not app.exception and any('Fixture missing' in e.value for e in app.error)
        app.sidebar.radio[0].set_value('Home/Overview').run()
        assert not app.exception and not app.error
    import builtins
    original=builtins.__import__
    def blocked(name,*args,**kwargs):
        if name=='src.metrics.comparison_ui':raise ImportError('fixture dependency missing')
        return original(name,*args,**kwargs)
    with patch('builtins.__import__',side_effect=blocked):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=60).run()
        app.sidebar.radio[0].set_value('Player Comparison Lab').run()
        assert not app.exception and any('dependencies are unavailable' in e.value for e in app.error)


def test_same_names_keep_distinct_ids(tmp_path):
    frames=fixtures()
    frames['deliveries'].loc[10,'striker_id']=B
    frames['deliveries'].loc[10,'non_striker_id']=A
    engine=store(tmp_path,frames)
    names=engine.players(tmp_path/'no_registry.json')
    assert names[A]==names[B]=='Same Name'
    rows=engine.get_batting_comparison(A,B,'2022-01-01','2025-01-01')
    assert rows.player_id.tolist()==[A,B]
    assert rows.runs.tolist()==[13,4]


def test_corrupt_derived_manifest_rebuilds(synthetic):
    (synthetic.store/'manifest.json').write_text('{"tables":{}}')
    repaired=ComparisonEngine.from_sources(synthetic.store.parents[1])
    assert set(repaired.manifest['tables'])==set(SOURCES)


def test_parallel_queries_have_isolated_connections(synthetic):
    from concurrent.futures import ThreadPoolExecutor
    def read(_):
        return synthetic.get_batting_comparison(A,B,'2022-01-01','2023-01-01').runs.tolist()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(read,range(4)))==[[12,0]]*4
