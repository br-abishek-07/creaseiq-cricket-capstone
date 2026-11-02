from pathlib import Path
from unittest.mock import patch
import json,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from deployment_info import deployment_info

def test_read_only_identity_and_no_secret_values(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text('print("hello")')
    monkeypatch.setenv('DEEPSEEK_API_KEY','NEVER_EXPOSE_THIS_VALUE')
    with patch('deployment_info.subprocess.check_output',return_value='a'*40+'\n'):
        result=deployment_info(tmp_path)
    assert result['git_commit']=='a'*40
    assert len(result['source_sha256']['app.py'])==64
    assert 'NEVER_EXPOSE_THIS_VALUE' not in json.dumps(result)

def test_missing_git_does_not_claim_a_commit(tmp_path):
    with patch('deployment_info.subprocess.check_output',side_effect=FileNotFoundError):
        assert deployment_info(tmp_path)['git_commit'] is None

def test_git_timeout_does_not_break_home(tmp_path):
    with patch('deployment_info.subprocess.check_output',side_effect=subprocess.TimeoutExpired('git',2)):
        assert deployment_info(tmp_path)['git_commit'] is None

def test_home_diagnostics_are_available_without_api_calls():
    from streamlit.testing.v1 import AppTest
    with patch('openai.OpenAI') as provider:
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
        assert not app.exception
        assert any(e.label=='Deployment diagnostics' for e in app.expander)
        record=json.loads(app.json[-1].value)
        assert record['git_commit'] and 'source_sha256' in record
        provider.assert_not_called()
