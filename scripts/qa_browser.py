from playwright.sync_api import sync_playwright
from pathlib import Path
import json,csv,argparse,shutil
parser=argparse.ArgumentParser(description='Browser QA: run against a local dev app, not a production data-entry session.')
parser.add_argument('--url',default='http://127.0.0.1:8540')
parser.add_argument('--output-dir',type=Path,default=Path('.runtime/qa-browser'))
args=parser.parse_args()
out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
 def idle():
  page.wait_for_function("document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state') === 'notRunning'",timeout=90000)
 def search(label,text):
  idle()
  widget=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text(label,exact=True))
  control=widget.locator('input')
  control.click();control.fill(text)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(args.url,wait_until='domcontentloaded')
 page.get_by_text('Player Comparison Lab',exact=True).first.wait_for(timeout=60000)
 page.get_by_text('Player Comparison Lab',exact=True).first.click()
 page.get_by_text('9,336',exact=True).wait_for(timeout=90000)
 # Search real stable identities, using text entry rather than programmatic option replacement.
 first=page.get_by_role('combobox').first;search('Player A','Kohli')
 page.get_by_role('option',name='Virat Kohli · ba607b88',exact=True).click()
 page.get_by_text('Cricsheet ID: ba607b88',exact=True).wait_for(timeout=90000)
 page.get_by_text('9,336',exact=True).wait_for(timeout=60000)
 page.get_by_text('Evidence and Source Records',exact=True).click()
 page.get_by_text('Download evidence scope and source manifest',exact=True).wait_for(timeout=60000)
 for label,filename in [('Download comparison metrics','metrics.csv'),('Download match-level series','series.csv'),('Download evidence scope and source manifest','scope.json')]:
  with page.expect_download(timeout=30000) as capture:page.get_by_text(label,exact=True).click()
  capture.value.save_as(str(out/filename))
  page.wait_for_timeout(300);idle()
 scope=json.loads((out/'scope.json').read_text());rows=list(csv.DictReader((out/'metrics.csv').open()))
 assert len(rows)==2 and len({r['player_id'] for r in rows})==2
 assert scope['scope']['player_ids']==[r['player_id'] for r in rows]
 assert scope['metrics_version']=='comparison-metrics-1.0.1'
 assert list(csv.DictReader((out/'series.csv').open()))[0].get('dismissals') is not None
 # Verify a real duplicate display name resolves through two distinct IDs.
 first=page.get_by_role('combobox').first;search('Player A','Harmeet Singh')
 page.get_by_role('option',name='Harmeet Singh · 0bf15e52',exact=True).wait_for()
 page.get_by_role('option',name='Harmeet Singh · 2a72fd4f',exact=True).wait_for()
 options=page.get_by_role('option');assert options.count()==2
 page.get_by_role('option',name='Harmeet Singh · 0bf15e52',exact=True).click()
 page.get_by_text('Cricsheet ID: 0bf15e52',exact=True).wait_for(timeout=90000)
 second=page.get_by_role('combobox').nth(1);search('Player B','Harmeet Singh')
 page.get_by_role('option',name='Harmeet Singh · 2a72fd4f',exact=True).click()
 page.get_by_text('Cricsheet ID: 2a72fd4f',exact=True).wait_for(timeout=90000)
 page.get_by_text('Cricsheet ID: 0bf15e52',exact=True).wait_for(timeout=60000)
 page.get_by_text('Cricsheet ID: 2a72fd4f',exact=True).wait_for(timeout=60000)
 first=page.get_by_role('combobox').first;search('Player A','Kohli')
 page.get_by_role('option',name='Virat Kohli · ba607b88',exact=True).click()
 page.get_by_text('Cricsheet ID: ba607b88',exact=True).wait_for(timeout=90000)
 second=page.get_by_role('combobox').nth(1);search('Player B','Rohit Sharma')
 page.get_by_role('option',name='Rohit Sharma · 740742ef',exact=True).click()
 page.get_by_text('Cricsheet ID: 740742ef',exact=True).wait_for(timeout=90000)
 page.get_by_text('9,336',exact=True).wait_for(timeout=60000)
 page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(600)
 page.screenshot(path=str(out/'desktop.png'))
 # All six pages are reachable in a real browser, including after using the Lab.
 for label,heading in [('Home/Overview','IPL Intelligence 360°'),('Player Profile','Player Profile'),('Team Matchups','Team Matchups'),('Squad Analysis','Squad Analysis'),('Auction Trends','Auction Trends'),('Player Comparison Lab','Player Comparison Lab')]:
  page.get_by_text(label,exact=True).first.click();page.get_by_role('heading',name=heading,exact=True).wait_for(timeout=60000)
  page.wait_for_timeout(300);idle()
  assert not page.locator('[data-testid="stException"]').count(),label
 idle();page.set_viewport_size({'width':390,'height':844})
 page.get_by_text('9,336',exact=True).wait_for(timeout=60000);idle()
 # Exercise controls at mobile width, not just a resized screenshot.
 phase=page.get_by_test_id('stSelectbox').filter(has=page.get_by_text('Analytical window',exact=True))
 search('Analytical window','Death');page.get_by_role('option',name='Death overs (16–20)',exact=True).click()
 page.get_by_text('Also show overall statistics for these dates',exact=True).wait_for(timeout=60000)
 page.get_by_text('Bowling',exact=True).click()
 page.get_by_text('Economy',exact=True).first.wait_for(timeout=60000)
 search('Player A','Kohli');page.get_by_role('option',name='Virat Kohli · ba607b88',exact=True).click()
 page.get_by_text('Cricsheet ID: ba607b88',exact=True).wait_for(timeout=60000);idle()
 page.wait_for_timeout(600);page.screenshot(path=str(out/'mobile.png'))
 # At narrow width the controls/results fit the main panel; evidence tables scroll internally.
 overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 2')
 assert not overflow,'Page-level horizontal overflow on mobile'
 assert not page.locator('[data-testid="stException"]').count()
 result={'viewport_widths':[1440,390],'page_errors':errors,'exception_panels':0,'routes_visited':6,'search':'Kohli -> ba607b88','duplicate_names_verified':['0bf15e52','2a72fd4f'],
         'downloads':['metrics.csv','series.csv','scope.json'],'metrics_player_ids':[r['player_id'] for r in rows],
         'scope_matches_downloaded_metrics':True,'mobile_page_overflow':overflow,'mobile_controls':['phase','bowling mode','player search']}
 (out/'results.json').write_text(json.dumps(result,indent=2));print(result)
 browser.close()
