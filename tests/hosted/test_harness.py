"""Harness tests use manually specified evidence, never app metric functions."""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from hosted_audit.connectivity import probe,validate_url
from hosted_audit.validate import reconcile
from hosted_acceptance import Audit


def sample():
 scope={'player_ids':['A','B'],'comparison_type':'Batting','start_inclusive':'2022-01-01','decision_as_of_exclusive':'2023-01-01','phase':'Overall','competition':'IPL','super_overs_excluded':True}
 rows=[{'player_id':p,'runs':'10','balls_faced':'5','dismissals':'1','strike_rate':'200','batting_average':'10','matches':'1'} for p in ['A','B']]
 series=[{'player_id':p,'match_id':'m','match_date':'2022-12-31','runs':'10','balls_faced':'5','dismissals':'1'} for p in ['A','B']]
 return rows,series,{'scope':scope},scope

def test_independent_reconciliation():
 assert len(reconcile(*sample()))==12

def test_cutoff_is_exclusive():
 m,s,p,e=sample();s[0]['match_date']='2023-01-01'
 with pytest.raises(AssertionError,match='Cutoff'):reconcile(m,s,p,e)

def test_wrong_aggregate_fails():
 m,s,p,e=sample();m[0]['runs']='11'
 with pytest.raises(AssertionError,match='reconciliation'):reconcile(m,s,p,e)

def test_scope_mismatch_fails():
 m,s,p,e=sample();p={'scope':{**e,'phase':'Other'}}
 with pytest.raises(AssertionError,match='Scope'):reconcile(m,s,p,e)

@pytest.mark.parametrize('url',['https://creaseiq.streamlit.app/','https://example.com/','http://user:password@127.0.0.1/','file:///tmp/data'])
def test_forbidden_target(url):
 with pytest.raises(ValueError):validate_url(url)

def test_network_denial_is_blocked_not_app_failure(tmp_path):
 import requests
 with patch('hosted_audit.connectivity.socket.getaddrinfo',side_effect=OSError('DNS blocked')),patch('hosted_audit.connectivity.requests.get',side_effect=requests.ConnectionError('proxy denied')):
  result=probe('https://creaseiq-cricket-capstone.streamlit.app/')
 assert not result['reachable'] and result['dns']['status']=='NOT VERIFIED'
 audit=Audit(tmp_path);audit.gate('connectivity','NOT VERIFIED',result)
 assert audit.write()==2
 assert 'FAIL' not in [r['status'] for r in audit.results]

def test_no_partial_run_can_claim_completion(tmp_path):
 audit=Audit(tmp_path);audit.gate('connectivity','PASS');audit.gate('browser','NOT VERIFIED','timed out')
 assert audit.write()==2


def test_reversed_identity_order_is_rejected():
 m,s,p,e=sample();m.reverse()
 with pytest.raises(AssertionError,match='IDs'):reconcile(m,s,p,e)


def test_bowling_empty_and_zero_denominators():
 _,_,p,e=sample();e['comparison_type']='Bowling'
 m=[{'player_id':pid,'runs_charged':'0','legal_balls':'0','wickets':'0','economy':'','bowling_strike_rate':'','matches':'0'} for pid in ['A','B']]
 assert len(reconcile(m,[],p,e))==12


def test_nonfinite_metrics_rejected():
 m,s,p,e=sample();m[0]['runs']='inf'
 with pytest.raises(ValueError,match='Non-finite'):reconcile(m,s,p,e)


def test_manifest_checks_actual_source_bytes(tmp_path):
 import hashlib
 from hosted_audit.validate import validate_manifest
 tables={}
 for name in ['matches','deliveries','wickets','innings']:
  data=b'a,b\n1,2\n';(tmp_path/f'{name}.csv').write_bytes(data)
  tables[name]={'source':f'{name}.csv','source_sha256':hashlib.sha256(data).hexdigest(),'input_rows':1,'output_rows':1}
 scope={'dataset_manifest':{'tables':tables}}
 assert len(validate_manifest(scope,tmp_path))==4
 (tmp_path/'deliveries.csv').write_bytes(b'changed')
 with pytest.raises(AssertionError,match='checksum'):validate_manifest(scope,tmp_path)


def test_manifest_path_escape_rejected(tmp_path):
 from hosted_audit.validate import validate_manifest
 tables={name:{'source':'../outside.csv'} for name in ['matches','deliveries','wickets','innings']}
 with pytest.raises(AssertionError,match='path'):validate_manifest({'dataset_manifest':{'tables':tables}},tmp_path)


def test_unreached_required_gate_is_not_verified(tmp_path):
 audit=Audit(tmp_path);audit.planned=['connectivity','downloads'];audit.gate('connectivity','PASS')
 assert audit.write()==2
 assert audit.results[-1]['status']=='NOT VERIFIED'
