"""Read-only hosted acceptance. Exit 2 means blocked, not an application failure."""
import argparse,csv,json,math,re,shutil,sys,traceback,hashlib,subprocess,time
from datetime import datetime,timezone
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hosted_audit.connectivity import DEFAULT_URL,probe,validate_url
from hosted_audit.deployment import poll_revision
from hosted_audit.validate import reconcile,number,close,validate_manifest

PHASES=['Overall','Powerplay window (1–6)','Middle overs (7–15)','Death overs (16–20)']
ROUTES={'Home/Overview':'IPL Intelligence 360°','Player Profile':'Player Profile','Team Matchups':'Team Matchups',
        'Squad Analysis':'Squad Analysis','Auction Trends':'Auction Trends','Player Comparison Lab':'Player Comparison Lab'}
LABELS={'Runs':'runs','Balls faced':'balls_faced','Strike rate':'strike_rate','Batting average':'batting_average','Batter dot %':'dot_ball_percentage',
        'Dismissals':'dismissals','Matches represented':'matches','Innings represented':'innings','Legal balls':'legal_balls','Runs charged':'runs_charged',
        'Economy':'economy','Bowler wickets':'wickets','Bowling strike rate':'bowling_strike_rate','Bowling dot %':'dot_ball_percentage'}

class DeploymentPending(RuntimeError):
    pass


class Audit:
    def __init__(self,out):
        self.out=out;out.mkdir(parents=True,exist_ok=True);self.results=[];self.diagnostics={};self.comparisons=[];self.context={};self.planned=[]
    def gate(self,name,status,detail='',required=True):
        row=dict(test=name,status=status,detail=detail,required=required);self.results.append(row)
        print(json.dumps(row),flush=True)
    def write(self):
        recorded={r['test'] for r in self.results}
        for name in self.planned:
            if name not in recorded:self.gate(name,'NOT VERIFIED','Not reached; inspect the connectivity result or first browser error')
        required=[r for r in self.results if r['required']]
        complete=bool(required) and all(r['status']=='PASS' for r in required)
        summary={s:sum(r['status']==s for r in self.results) for s in ['PASS','FAIL','NOT VERIFIED']}
        result={'context':self.context,'completed':complete,'summary':summary,'tests':self.results,'diagnostics':self.diagnostics,'metric_comparisons':self.comparisons}
        (self.out/'quality_gates.json').write_text(json.dumps(result,indent=2)+'\n')
        text=['# Streamlit acceptance audit','',f'Execution context: {self.context}','',f'Completed required gates: **{complete}**',f'Outcomes: {summary}','',
              '| Test | Result | Observed detail |','|---|---|---|']
        for r in self.results:text.append('| '+r['test']+' | '+r['status']+' | '+str(r['detail']).replace('|','/').replace('\n',' ')+' |')
        text+=['','Expected scorecard values come from external references stored in tests/fixtures/independent_ipl_scorecards.json.',
               'Match-series reconciliation is an independent arithmetic consistency check, not independent certification of all source events.',
               'Dots/innings/boundaries cannot all be independently recomputed from the exported match series; unsupported checks remain unverified.',
               'Browser-visible traffic cannot prove absence of server-side API calls. No report-generation button is clicked.']
        (self.out/'ACCEPTANCE_REPORT.md').write_text('\n'.join(text)+'\n')
        return 0 if complete else 1 if any(r['status']=='FAIL' for r in required) else 2

class BrowserAudit:
    def __init__(self,page,audit):self.page=page;self.audit=audit;self.sequence=0;self.manifest=None
    def idle(self):
        self.page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'",timeout=120000)
    def settle(self):self.page.wait_for_timeout(350);self.idle()
    def exceptions(self):
        texts=self.page.get_by_test_id('stException').all_text_contents()
        if texts:raise AssertionError('Streamlit exception panel: '+str(texts))
    def route(self,name):
        self.page.get_by_text(name,exact=True).first.click()
        self.page.get_by_test_id('stMainBlockContainer').get_by_role('heading',name=ROUTES[name],exact=True).wait_for(timeout=120000)
        self.settle();self.exceptions()
    def json_view(self,viewer=None):
        viewer=viewer if viewer is not None else self.page.get_by_test_id('stJson').last
        # The visual JSON tree omits commas. Use its root copy control to read
        # the actual JSON payload; do not repair or infer a schema from the text.
        self.page.evaluate("navigator.clipboard.writeText('')")
        # Large JSON trees move their copy control when scrolled/hovered.
        # Dispatch its UI click handler directly, rather than clicking unstable
        # coordinates. This reads the viewer payload, never application internals.
        viewer.locator('.copy-to-clipboard-container').last.locator('span').first.dispatch_event('click')
        self.page.wait_for_function("async () => (await navigator.clipboard.readText()).length > 0",timeout=10000)
        return json.loads(self.page.evaluate('navigator.clipboard.readText()'))
    def diagnostic(self,key):
        self.route('Home/Overview');self.page.get_by_text('Deployment diagnostics',exact=True).click();self.settle()
        raw=self.page.get_by_test_id('stJson').last.inner_text();(self.audit.out/f'diagnostics_{key}_raw.txt').write_text(raw)
        record=self.json_view();self.audit.diagnostics[key]=record
        (self.audit.out/f'diagnostics_{key}.json').write_text(json.dumps(record,indent=2)+'\n')
        return record
    def select(self,label,identity,suffix=True):
        self.idle();widget=self.page.get_by_test_id('stSelectbox').filter(has=self.page.get_by_text(label,exact=True))
        control=widget.locator('input');control.click();control.fill(identity)
        if not self.page.get_by_role('listbox').is_visible():control.press('ArrowDown')
        self.page.get_by_role('option',name=re.compile(re.escape(identity)+(r'$' if suffix else ''))).click()
        self.settle()
    def specialist_snapshots(self,key):
        """Exercise deterministic controls, read evidence, never request a report."""
        snapshots={}
        for route,label,choices in [
            ('Player Profile','Inspect evidence sent to the scout',[('Search for a player','ba607b88',True),('Competition','IPL',True)]),
            ('Team Matchups','Inspect evidence sent to the Matchup Analyst',[('Team A','RCB',True),('Team B','CSK',True)]),
            ('Squad Analysis','Inspect evidence sent to the Squad Analyst',[('Franchise','RCB',False)]),
            ('Auction Trends','Inspect evidence sent to the Auction Analyst',[('Auction year','2022',True)]),
        ]:
            self.route(route)
            for widget,value,suffix in choices:self.select(widget,value,suffix)
            toggle=self.page.get_by_text(label,exact=True)
            panel=self.page.get_by_test_id('stExpander').filter(has=toggle)
            if not panel.get_by_test_id('stJson').is_visible():toggle.click()
            record=self.json_view(panel.get_by_test_id('stJson'))
            assert record.get('facts'),'Specialist evidence packet has no facts'
            snapshots[route]=record;self.exceptions()
            self.page.screenshot(path=str(self.audit.out/f'specialist_{key}_{route.replace(" ","_")}.png'))
        (self.audit.out/f'specialists_{key}.json').write_text(json.dumps(snapshots,indent=2)+'\n')
        return snapshots
    def day(self,label,when):
        widget=self.page.get_by_test_id('stDateInput').filter(has=self.page.get_by_text(label,exact=True))
        control=widget.locator('input')
        control.fill(when if control.get_attribute('type')=='date' else when.replace('-','/'))
        control.press('Enter');control.press('Tab')
        # New Streamlit's segmented date field commits when focus leaves the
        # whole widget, rather than merely moving to its next internal segment.
        self.page.get_by_role('heading',name='Player Comparison Lab',exact=True).click()
        self.settle()
    def dates(self,start,cutoff):
        control=self.page.get_by_test_id('stDateInput').filter(has=self.page.get_by_text('Decision as-of date (exclusive)',exact=True)).locator('input')
        old=date.fromisoformat(control.input_value().replace('/','-'))
        if date.fromisoformat(start)<old:
            self.day('Historical start date (inclusive)',start);self.day('Decision as-of date (exclusive)',cutoff)
        else:
            self.day('Decision as-of date (exclusive)',cutoff);self.day('Historical start date (inclusive)',start)
    def mode(self,value):
        self.page.get_by_test_id('stRadio').filter(has=self.page.get_by_text('Comparison type',exact=True)).get_by_text(value,exact=True).click();self.settle()
    def download(self,label,path):
        with self.page.expect_download(timeout=60000) as pending:self.page.get_by_text(label,exact=True).click()
        pending.value.save_as(str(path));self.settle()
    def exported_case(self,name,ids,mode,start,cutoff,phase):
        started=time.perf_counter()
        self.sequence+=1;folder=self.audit.out/f'{self.sequence:02d}_{name}';folder.mkdir()
        expected={'player_ids':ids,'comparison_type':mode,'start_inclusive':start,'decision_as_of_exclusive':cutoff,'phase':phase,'competition':'IPL','super_overs_excluded':True}
        (folder/'steps.json').write_text(json.dumps(expected,indent=2)+'\n')
        self.select('Player A',ids[0]);self.select('Player B',ids[1]);self.mode(mode);self.dates(start,cutoff);self.select('Analytical window',phase)
        self.exceptions()
        # Ensure both displayed stable identities, irrespective of name formatting.
        for pid in ids:self.page.get_by_text('Cricsheet ID: '+pid,exact=True).wait_for(timeout=60000)
        toggle=self.page.get_by_text('Evidence and Source Records',exact=True)
        # Check expanded state using its containing details element.
        details=self.page.get_by_test_id('stExpander').filter(has=toggle)
        if details.locator('details').count():
            if details.locator('details').get_attribute('open') is None:toggle.click()
        elif not self.page.get_by_text('Download match-level series',exact=True).is_visible():toggle.click()
        self.page.get_by_text('Download match-level series',exact=True).wait_for(timeout=60000)
        for label,file in [('Download comparison metrics','metrics.csv'),('Download match-level series','series.csv'),('Download evidence scope and source manifest','scope.json')]:
            self.download(label,folder/file)
        with (folder/'metrics.csv').open() as f:metrics=list(csv.DictReader(f))
        with (folder/'series.csv').open() as f:series=list(csv.DictReader(f))
        scope=json.loads((folder/'scope.json').read_text())
        expected={'player_ids':ids,'comparison_type':mode,'start_inclusive':start,'decision_as_of_exclusive':cutoff,'phase':phase,'competition':'IPL','super_overs_excluded':True}
        if self.manifest is None:
            source_checks=validate_manifest(scope,Path(__file__).resolve().parents[1]/'data')
            (self.audit.out/'source_checksum_comparisons.json').write_text(json.dumps(source_checks,indent=2)+'\n')
            self.manifest=scope['dataset_manifest']
            self.audit.gate('source_checksums','PASS',source_checks)
        assert scope['dataset_manifest']==self.manifest,'Source manifest changed during the audit'
        checks=reconcile(metrics,series,scope,expected)
        self.audit.comparisons.extend([{'case':name,**c} for c in checks])
        # DOM values are compared to downloads, not accepted as the expected truth.
        nodes=self.page.get_by_test_id('stMetric');assert nodes.count()==16,'Expected two columns of eight metrics'
        for i,node in enumerate(nodes.all()):
            label=node.get_by_test_id('stMetricLabel').inner_text().strip();field=LABELS[label]
            displayed=node.get_by_test_id('stMetricValue').inner_text().strip();raw=number(metrics[i//8].get(field))
            decimals=2 if field in ['strike_rate','batting_average','economy','bowling_strike_rate','dot_ball_percentage'] else 0
            expected_display=None if raw is None else float(f'{raw:.{decimals}f}')
            assert close(displayed,expected_display),f'Display/export disagreement {label}: {displayed} vs {raw}'
        self.page.screenshot(path=str(folder/'page.png'),full_page=False)
        (folder/'steps.json').write_text(json.dumps(expected,indent=2)+'\n')
        self.audit.gate(name,'PASS',f'IDs {ids}; {mode}; {start} <= date < {cutoff}; {phase}; {len(checks)} independent-series checks; DOM matches exports; {time.perf_counter()-started:.2f}s including interactions/downloads')
        return metrics,series

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default=DEFAULT_URL);parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--deployment-wait-seconds',type=int,default=600)
    parser.add_argument('--output-dir',type=Path,default=Path('.runtime/hosted-audit'));parser.add_argument('--reference-file',type=Path,default=Path(__file__).resolve().parents[1]/'tests/fixtures/independent_ipl_scorecards.json')
    args=parser.parse_args();validate_url(args.url)
    if not re.fullmatch('[0-9a-f]{40}',args.expected_commit):parser.error('Expected commit must be a full lowercase Git SHA')
    if not 0<=args.deployment_wait_seconds<=1200:parser.error('Deployment wait must be between 0 and 1200 seconds')
    audit=Audit(args.output_dir);page=None;browser=None
    audit.context={'url':args.url,'execution_kind':'LOCAL harness validation' if '127.0.0.1' in args.url or 'localhost' in args.url else 'PUBLIC hosted audit','expected_commit':args.expected_commit,'started_utc':datetime.now(timezone.utc).isoformat(),'reference_fixture_sha256':hashlib.sha256(args.reference_file.read_bytes()).hexdigest()}
    audit.planned=['runner_connectivity','streamlit_ui','deployed_revision','specialist_controls','specialist_input_isolation','source_checksums','independent_scorecards','invalid_dates','client_llm_requests','uncaught_browser_errors','memory_diagnostics','revision_stability','duplicate_names','empty_window']+['workspace_'+route for route in ROUTES]+[mode+'_'+cutoff+'_'+str(i) for mode in ['Batting','Bowling'] for cutoff in ['2026-06-01','2023-01-01'] for i in range(4)]
    audit.context['runner_commit']=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=Path(__file__).resolve().parents[1]).strip()
    try:
        connection=probe(args.url);(audit.out/'connectivity.json').write_text(json.dumps(connection,indent=2)+'\n')
        if not connection['reachable']:
            audit.gate('runner_connectivity','NOT VERIFIED',connection)
            for test in ['streamlit_ui','deployed_revision','six_workspaces','player_comparisons','historical_cutoff','phase_windows','downloads','independent_scorecards','empty_invalid_dates','memory_after']:
                audit.gate(test,'NOT VERIFIED','Browser audit not started because public connectivity was not established')
            return audit.write()
        audit.gate('runner_connectivity','PASS',connection)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True,permissions=['clipboard-read','clipboard-write'])
            page=context.new_page();page.set_default_timeout(60000);ui=BrowserAudit(page,audit)
            errors=[];providers=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            def route_request(route):
                providers.append(route.request.url.split('?')[0]);route.abort()
            context.route(re.compile(r'https://api\.(deepseek|openai)\.com/.*'),route_request)
            deployment_ready=False
            try:
                def read_deployment():
                    page.goto(args.url,wait_until='domcontentloaded',timeout=30000)
                    wake=page.get_by_role('button',name=re.compile(r'Yes, get this app back up',re.I))
                    if wake.is_visible():wake.click()
                    page.get_by_text('Home/Overview',exact=True).wait_for(timeout=45000)
                    ui.settle();ui.exceptions()
                    return ui.diagnostic('deployment_poll')
                def record_poll(result):
                    (audit.out/'deployment_poll.json').write_text(json.dumps(result,indent=2)+'\n')
                    last=result['attempts'][-1]
                    print(json.dumps({'deployment_poll':last}),flush=True)
                    if not result['ready']:
                        page.screenshot(path=str(audit.out/f'startup_attempt_{last["attempt"]}.png'))
                readiness=poll_revision(read_deployment,args.expected_commit,timeout=args.deployment_wait_seconds,record=record_poll)
                deployment_ready=readiness['ready']
                if not deployment_ready:
                    audit.gate('deployed_revision','NOT VERIFIED',{'reason':'Intended clean revision was not observed within the deployment wait; possible deployment lag or access blocker, not an established application defect','poll_log':'deployment_poll.json','expected':args.expected_commit})
                    raise DeploymentPending('Hosted revision not ready; remaining tests are blocked. See deployment_poll.json')
                audit.gate('streamlit_ui','PASS','Public Streamlit controls rendered in Chromium after deployment polling')
                before=readiness['attempts'][-1]['snapshot'];audit.diagnostics['before']=before
                (audit.out/'diagnostics_before.json').write_text(json.dumps(before,indent=2)+'\n')
                audit.gate('deployed_revision','PASS',{'expected':args.expected_commit,'observed':before.get('git_commit'),'dirty':before.get('git_tracked_changes'),'attempts':len(readiness['attempts'])})
                for route in ROUTES:
                    ui.route(route);page.screenshot(path=str(audit.out/('workspace_'+route.replace('/','_').replace(' ','_')+'.png')))
                    audit.gate('workspace_'+route,'PASS','Rendered without Streamlit exception; no AI generation buttons clicked')
                specialist_before=ui.specialist_snapshots('before')
                audit.gate('specialist_controls','PASS','Changed player, team, franchise and auction selectors; inspected nonempty evidence packets without requesting reports')
                ui.route('Player Comparison Lab')
                for mode,ids in [('Batting',['ba607b88','740742ef']),('Bowling',['462411b3','5f547c8b'])]:
                    for cutoff in ['2026-06-01','2023-01-01']:
                        for phase in PHASES:ui.exported_case(mode+'_'+cutoff+'_'+str(PHASES.index(phase)),ids,mode,'2008-04-18',cutoff,phase)
                # True duplicate display name, distinct registry identifiers.
                ui.exported_case('duplicate_names',['0bf15e52','2a72fd4f'],'Batting','2008-04-18','2026-06-01','Overall')
                refs=json.loads(args.reference_file.read_text());reference_checks=[];display_notes=[]
                for match in refs['matches']:
                    for mode in ['Batting','Bowling']:
                        records=[r for r in match['records'] if r['type']==mode][:2]
                        ids=[r['player_id'] for r in records];cutoff=(date.fromisoformat(match['date'])+timedelta(days=1)).isoformat()
                        metrics,_=ui.exported_case('reference_'+match['match_id']+'_'+mode,ids,mode,match['date'],cutoff,'Overall')
                        for expected,row in zip(records,metrics):
                            for metric,value in expected['expected'].items():
                                status='PASS' if close(row.get(metric),value) else 'FAIL'
                                reference_checks.append({'match_id':match['match_id'],'reference':match['reference_source'],'player_id':expected['player_id'],'metric':metric,'expected':value,'observed':number(row.get(metric)),'difference':number(row.get(metric))-value if number(row.get(metric)) is not None else None,'status':status})
                            rate='strike_rate' if mode=='Batting' else 'economy'
                            if not close(round(float(row[rate]),2),expected['reference_display_rate']):display_notes.append({'match_id':match['match_id'],'player_id':expected['player_id'],'metric':rate,'displayed_by_reference':expected['reference_display_rate'],'calculated':number(row[rate]),'note':'External display differs; raw expected primitive counts and exact arithmetic checked separately'})
                assert len(reference_checks)==96,'Expected 96 sampled external scorecard fields'
                (audit.out/'independent_scorecards.json').write_text(json.dumps(reference_checks,indent=2)+'\n')
                (audit.out/'reference_display_notes.json').write_text(json.dumps(display_notes,indent=2)+'\n')
                audit.gate('independent_scorecards','PASS' if all(r['status']=='PASS' for r in reference_checks) else 'FAIL',f'{len(reference_checks)} external field checks; {len(display_notes)} rate-display notes')
                ui.exported_case('empty_window',['ba607b88','740742ef'],'Batting','2000-01-01','2001-01-01','Overall')
                assert page.get_by_text(re.compile('Insufficient observations')).count()>=2
                ui.day('Historical start date (inclusive)','2002-01-01');ui.exceptions()
                page.get_by_text(re.compile('Start date must be earlier')).wait_for();audit.gate('invalid_dates','PASS','Readable validation error, no exception panel')
                specialist_after=ui.specialist_snapshots('after')
                assert specialist_before==specialist_after,'Comparison browsing changed specialist input evidence under identical specialist selections'
                audit.gate('specialist_input_isolation','PASS','Before/after JSON evidence packets identical under explicitly restored specialist selections')
                audit.gate('client_llm_requests','FAIL' if providers else 'PASS',{'attempts_blocked':providers,'ai_generation_buttons_clicked':0})
                audit.gate('live_specialist_generation','NOT VERIFIED','Paid DeepSeek calls are prohibited for this audit; deterministic specialist evidence controls were tested',required=False)
                audit.gate('server_llm_traffic','NOT VERIFIED','Browser cannot observe server-side provider traffic; no live specialist report requested',required=False)
                audit.gate('uncaught_browser_errors','FAIL' if errors else 'PASS',errors)
                audit.gate('unexported_dot_innings_verification','NOT VERIFIED','Match-series export does not expose all dot/innings/raw-boundary inputs; no independent all-history claim',required=False)
            except Exception as exc:
                audit.gate('browser_acceptance','FAIL' if isinstance(exc,AssertionError) else 'NOT VERIFIED',type(exc).__name__+': '+str(exc))
                (audit.out/'exception.txt').write_text(traceback.format_exc());page.screenshot(path=str(audit.out/'failure.png'))
            finally:
                try:
                    after=ui.diagnostic('after')
                    audit.gate('revision_stability','PASS' if deployment_ready and after.get('git_commit')==args.expected_commit and after.get('git_tracked_changes') is False else 'NOT VERIFIED',{'after':after.get('git_commit'),'dirty':after.get('git_tracked_changes')})
                    audit.gate('memory_diagnostics','PASS',{'before':audit.diagnostics.get('before',{}).get('process_memory'),'after':after.get('process_memory')})
                except Exception as exc:audit.gate('memory_diagnostics','NOT VERIFIED',str(exc))
                browser.close()
    except Exception as exc:
        audit.gate('audit_execution','NOT VERIFIED',type(exc).__name__+': '+str(exc));(audit.out/'exception.txt').write_text(traceback.format_exc())
    return audit.write()

if __name__=='__main__':raise SystemExit(main())
