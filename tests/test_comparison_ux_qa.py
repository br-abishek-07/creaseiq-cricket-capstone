"""Local filter isolation, duplicate IDs, empty windows and evidence provenance."""
from datetime import date
from pathlib import Path
import json,sys
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def app():return AppTest.from_file(str(ROOT/'app.py'),default_timeout=90).run()

def test_lab_filters_leave_specialist_evidence_unchanged():
    with patch('openai.OpenAI') as provider:
        ui=app();before={}
        for route in ['Player Profile','Team Matchups','Squad Analysis','Auction Trends']:
            ui.sidebar.radio[0].set_value(route).run();assert not ui.exception and not ui.error
            before[route]=json.loads(ui.json[-1].value)
        ui.sidebar.radio[0].set_value('Player Comparison Lab').run()
        ui.date_input[0].set_value(date(2016,1,1)).run()
        ui.date_input[1].set_value(date(2023,1,1)).run()
        next(r for r in ui.radio if r.label=='Comparison type').set_value('Bowling').run()
        next(s for s in ui.selectbox if s.label=='Analytical window').set_value('Death overs (16–20)').run()
        assert not ui.exception and not ui.error
        provenance=json.loads(ui.json[-1].value)
        assert provenance['scope']['decision_as_of_exclusive']=='2023-01-01'
        assert provenance['scope']['phase']=='Death overs (16–20)'
        assert provenance['scope']['comparison_type']=='Bowling'
        for route,packet in before.items():
            ui.sidebar.radio[0].set_value(route).run();assert not ui.exception and not ui.error
            assert json.loads(ui.json[-1].value)==packet,route
        provider.assert_not_called()

def test_duplicate_selection_empty_window_and_date_errors():
    with patch('openai.OpenAI') as provider:
        ui=app();ui.sidebar.radio[0].set_value('Player Comparison Lab').run()
        a=next(s for s in ui.selectbox if s.label=='Player A')
        b=next(s for s in ui.selectbox if s.label=='Player B')
        previous_b=b.value;a.set_value(previous_b).run()
        a=next(s for s in ui.selectbox if s.label=='Player A')
        b=next(s for s in ui.selectbox if s.label=='Player B')
        assert a.value!=b.value
        ui.date_input[0].set_value(date(2000,1,1)).run()
        ui.date_input[1].set_value(date(2001,1,1)).run()
        assert not ui.exception and not ui.error
        assert any('Insufficient observations' in e.value for e in ui.info)
        assert sum(m.value=='N/A' for m in ui.metric)>=6
        ui.date_input[0].set_value(date(2002,1,1)).run()
        assert not ui.exception and any('Start date must be earlier' in e.value for e in ui.error)
        provider.assert_not_called()
