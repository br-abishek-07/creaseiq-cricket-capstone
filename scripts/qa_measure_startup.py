"""Fresh-process local measurements; no secrets or AI requests."""
import sys,time,json,resource,statistics,argparse
from pathlib import Path
from streamlit.testing.v1 import AppTest
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--output',type=Path,default=Path('qa-performance.json'))
args=parser.parse_args()
root=args.root.resolve();sys.path.insert(0,str(root))
assert not (root/'data/parquet').exists(),'Cold measurement requires an empty derived cache'
def rss():
 for line in Path('/proc/self/status').read_text().splitlines():
  if line.startswith('VmRSS:'):return round(int(line.split()[1])/1024,2)
start=time.perf_counter();ui=AppTest.from_file(str(root/'app.py'),default_timeout=120).run();home=time.perf_counter()-start
assert not ui.exception and not ui.error
home_rss=rss()
start=time.perf_counter();ui.sidebar.radio[0].set_value('Player Comparison Lab').run();cold=time.perf_counter()-start
assert not ui.exception and not ui.error
lab_rss=rss();start=time.perf_counter();ui.run();warm=time.perf_counter()-start
assert not ui.exception and not ui.error
from src.metrics.comparison_ui import _engine
from src.metrics.parquet_store import source_paths
sources=source_paths(root/'data');versions=tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in sources.values())
engine=_engine(str(root/'data'),versions)
times=[]
for _ in range(20):
 start=time.perf_counter();engine.get_batting_comparison('ba607b88','740742ef','2008-04-18','2023-01-01');times.append(time.perf_counter()-start)
from src.metrics.parquet_store import ensure_parquet
start=time.perf_counter();path,manifest=ensure_parquet(root/'data');reuse=time.perf_counter()-start
result={'environment':'fresh Python 3.12 venv (no system site packages), clean Git worktree, no derived cache or secrets',
 'home_seconds':round(home,3),'first_lab_seconds':round(cold,3),'warm_lab_rerun_seconds':round(warm,3),
 'home_current_rss_mib':home_rss,'lab_current_rss_mib':lab_rss,'peak_process_rss_mib':round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2),
 'query_repetitions':20,'query_median_seconds':round(statistics.median(times),4),'query_p95_seconds':round(sorted(times)[18],4),
 'query_min_seconds':round(min(times),4),'query_max_seconds':round(max(times),4),'manifest_reuse_seconds':round(reuse,4),
 'dataset_version':manifest['dataset_version'],'parquet_bytes':sum((path/(n+'.parquet')).stat().st_size for n in manifest['tables'])}
args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
