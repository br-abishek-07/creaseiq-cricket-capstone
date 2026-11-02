"""Read-only deployment identity; never reads secrets or remote Git URLs."""
import hashlib
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import subprocess


def deployment_info(root):
    root=Path(root).resolve()
    try:
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],stderr=subprocess.DEVNULL,timeout=2,text=True).strip()
        if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):commit=None
    except (OSError,subprocess.SubprocessError):commit=None
    try:
        dirty=bool(subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],stderr=subprocess.DEVNULL,timeout=2,text=True).strip())
    except (OSError,subprocess.SubprocessError):dirty=None
    hashes={}
    for name in ['app.py','requirements.txt','src/metrics/query_engine.py','src/metrics/parquet_store.py']:
        path=root/name
        try:
            if path.is_file():hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:hashes[name]=None
    packages={}
    for name in ['streamlit','pandas','duckdb','pyarrow','openai']:
        try:packages[name]=version(name)
        except PackageNotFoundError:packages[name]=None
    memory={}
    status=Path('/proc/self/status')
    try:
        if status.is_file():
            for line in status.read_text().splitlines():
                if line.startswith(('VmRSS:','VmHWM:')):memory[line.split(':')[0]+'_mib']=round(int(line.split()[1])/1024,2)
    except OSError:pass
    limit=Path('/sys/fs/cgroup/memory.max')
    try:memory['observed_cgroup_limit_bytes']=limit.read_text().strip() if limit.is_file() else None
    except OSError:memory['observed_cgroup_limit_bytes']=None
    return {'git_commit':commit,'git_tracked_changes':dirty,'entrypoint':str(root/'app.py'),'source_sha256':hashes,
            'packages':packages,'process_memory':memory,
            'limitations':'Observed checkout/process data only. Cloud repository/branch settings, service memory allowance, endpoint health and hosted acceptance require separate verification. No credentials are inspected.'}
