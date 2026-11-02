"""Offline regression against externally transcribed scorecards; no web/API calls."""
from datetime import date,timedelta
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.metrics.query_engine import ComparisonEngine
FIXTURE=json.loads((Path(__file__).parent/'fixtures/independent_ipl_scorecards.json').read_text())
CASES=[(match,record) for match in FIXTURE['matches'] for record in match['records']]

@pytest.fixture(scope='module')
def engine():return ComparisonEngine.from_sources()

@pytest.mark.parametrize('match,record',CASES,ids=[m['match_id']+'-'+r['type']+'-'+r['player_id'] for m,r in CASES])
def test_independent_scorecard(engine,match,record):
    other=next(r['player_id'] for r in match['records'] if r['player_id']!=record['player_id'])
    cutoff=(date.fromisoformat(match['date'])+timedelta(days=1)).isoformat()
    query=engine.get_batting_comparison if record['type']=='Batting' else engine.get_bowling_comparison
    result=query(record['player_id'],other,match['date'],cutoff).iloc[0]
    assert result.matches==1
    for metric,expected in record['expected'].items():
        assert result[metric]==pytest.approx(expected),f"{match['match_id']} {record['player_name']} {metric}: {result[metric]} vs external {expected}"
    evidence=engine.evidence(record['player_id'],other,match['date'],cutoff,mode=record['type'])
    assert match['match_id'] in evidence['matches'].match_id.tolist()
    assert not evidence['deliveries'].is_super_over.any()
