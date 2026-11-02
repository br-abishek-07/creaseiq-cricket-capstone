"""Explicit application contracts; the default pytest collection is untouched.

Run: python ci/test_targets.py --target shared|development|production --app-root PATH
"""
import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

DEV_FILES = {
    'test_agent_runtime.py','test_data_runtime.py','test_auction_agent.py','test_matchup_agent.py',
    'test_scout_agent.py','test_squad_agent.py','test_moneyball.py','test_home_overview.py',
    'test_harness.py','test_deployment_info.py','test_player_comparison_engine.py','test_post_integration_qa.py','test_independent_scorecards.py','test_comparison_ux_qa.py',
}
SHARED_FILES = {'test_core.py','test_rebrand.py'}
PRODUCTION_NODES = {
 'tests/test_runtime.py::ReleaseRuntime::test_01_previous_package_cannot_break_home_or_brief',
 'tests/test_runtime.py::ReleaseRuntime::test_06_code_update_invalidates_data_cache_in_same_session',
 'tests/test_startup.py::Startup::test_cached_generic_modules_do_not_break_startup',
 'tests/test_startup.py::Startup::test_startup_from_another_working_directory',
}


def classify(nodeid):
    file = nodeid.split('::')[0].replace('\\','/').split('/')[-1]
    if file in DEV_FILES:
        return 'development'
    if file == 'test_ui.py' or '::DossierInterface::' in nodeid or nodeid in PRODUCTION_NODES:
        return 'production'
    if file in SHARED_FILES or file in {'test_accuracy.py','test_runtime.py','test_startup.py'}:
        return 'shared'
    raise pytest.UsageError(f'Unclassified test: {nodeid}. Assign its contract explicitly in ci/test_targets.py.')


class ContractSelection:
    def __init__(self,target): self.target=target
    def pytest_collection_modifyitems(self,config,items):
        selected=[];excluded=[];counts={'shared':0,'development':0,'production':0}
        for item in items:
            contract=classify(item.nodeid);counts[contract]+=1
            (selected if contract==self.target else excluded).append(item)
        print('\nContract inventory: '+json.dumps(counts,sort_keys=True))
        print(f'Explicit target {self.target}: {len(selected)} selected; {len(excluded)} belong to other contracts.')
        if not selected: raise pytest.UsageError(f'No tests collected for target {self.target}.')
        config.hook.pytest_deselected(items=excluded)
        items[:]=selected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',required=True,choices=['shared','development','production'])
    parser.add_argument('--app-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--junitxml',type=Path)
    args=parser.parse_args();root=args.app_root.resolve()
    source=(root/'app.py').read_text()
    literals={n.value for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    if args.target=='development' and not {'Player Comparison Lab','Home/Overview','Squad Analysis'}<=literals:
        parser.error('Development target requires the six-workspace dev app.')
    if args.target=='production' and not {'Decision desk','Player dossier','Home'}<=literals:
        parser.error('Production target requires the production app. Use --app-root pointing to a separate main checkout; no tests were run.')
    try:sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    except subprocess.CalledProcessError:sha='unavailable'
    print(f'Application: {root}; commit: {sha}; contract: {args.target}',flush=True)
    os.chdir(root);sys.path.insert(0,str(root))
    argv=['-q','tests']
    if args.junitxml:argv+=['--junitxml',str(args.junitxml.resolve())]
    return pytest.main(argv,plugins=[ContractSelection(args.target)])

if __name__=='__main__':raise SystemExit(main())
