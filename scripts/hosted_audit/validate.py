"""Validate downloaded evidence independently with standard-library arithmetic."""
from datetime import date
import math
import hashlib
from pathlib import Path


def number(value):
    if value is None or str(value).strip() in ('','N/A','NaN','nan','<NA>'):return None
    result=float(str(value).replace(',',''))
    if not math.isfinite(result):raise ValueError('Non-finite number')
    return result


def close(actual,expected,tolerance=1e-8):
    actual=number(actual)
    return actual is None if expected is None else actual is not None and math.isclose(actual,expected,rel_tol=tolerance,abs_tol=tolerance)


def reconcile(metrics,series,scope,expected_scope):
    """No trusted source totals or expected figures are derived through app code."""
    for key,value in expected_scope.items():
        if scope['scope'].get(key)!=value:raise AssertionError(f'Scope mismatch {key}: {scope["scope"].get(key)!r} vs {value!r}')
    ids=expected_scope['player_ids']
    if len(metrics)!=2 or [r['player_id'] for r in metrics]!=ids or len(set(ids))!=2:
        raise AssertionError('Metrics must contain exactly the two distinct requested IDs')
    start=date.fromisoformat(expected_scope['start_inclusive']);cutoff=date.fromisoformat(expected_scope['decision_as_of_exclusive'])
    for row in series:
        if row['player_id'] not in ids:raise AssertionError('Unexpected player in exported series')
        when=date.fromisoformat(row['match_date'][:10])
        if not start<=when<cutoff:raise AssertionError(f'Cutoff violation: {when}')
        if 'is_super_over' in row and number(row['is_super_over'])!=0:raise AssertionError('Super-over row included')
    mode=expected_scope['comparison_type'];checks=[]
    for row in metrics:
        samples=[r for r in series if r['player_id']==row['player_id']]
        def total(col):return sum(number(r[col]) or 0 for r in samples)
        if mode=='Batting':
            runs,balls,outs=total('runs'),total('balls_faced'),total('dismissals')
            expected={'runs':runs,'balls_faced':balls,'dismissals':outs,'strike_rate':100*runs/balls if balls else None,'batting_average':runs/outs if outs else None}
        else:
            runs,balls,wickets=total('runs_charged'),total('legal_balls'),total('wickets')
            expected={'runs_charged':runs,'legal_balls':balls,'wickets':wickets,'economy':6*runs/balls if balls else None,'bowling_strike_rate':balls/wickets if wickets else None}
        expected['matches']=len({r['match_id'] for r in samples})
        for metric,value in expected.items():
            passed=close(row.get(metric),value)
            checks.append({'player_id':row['player_id'],'metric':metric,'exported':number(row.get(metric)),'independent_series_value':value,'status':'PASS' if passed else 'FAIL'})
    if not all(c['status']=='PASS' for c in checks):raise AssertionError('Series reconciliation failed: '+str([c for c in checks if c['status']=='FAIL']))
    return checks


def validate_manifest(scope, data_dir):
    """Compare exported source hashes with independent runner-checkout file hashes."""
    tables=scope['dataset_manifest']['tables']
    if set(tables)!={'matches','deliveries','wickets','innings'}:
        raise AssertionError('Expected four source tables in manifest')
    records=[]
    for name,table in tables.items():
        source=table['source']
        if Path(source).name!=source:raise AssertionError('Unexpected source path')
        path=Path(data_dir)/source
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        actual=digest.hexdigest()
        if actual!=table['source_sha256']:raise AssertionError(f'Source checksum disagreement: {source}')
        if table['input_rows']!=table['output_rows']:raise AssertionError(f'Manifest row mismatch: {source}')
        records.append({'table':name,'source':source,'sha256':actual,'rows':table['input_rows']})
    return records
