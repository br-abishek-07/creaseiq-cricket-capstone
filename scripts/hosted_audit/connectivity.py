"""Public connectivity probe. Network failures are not app failures."""
import socket
from urllib.parse import urlsplit,urlunsplit
import requests

DEFAULT_URL='https://creaseiq-cricket-capstone.streamlit.app/'

def validate_url(url):
    p=urlsplit(url)
    if p.scheme not in ('http','https') or p.username or p.password or p.query or p.fragment:
        raise ValueError('Use an unauthenticated root HTTP(S) URL without query/fragment')
    if p.hostname not in ('creaseiq-cricket-capstone.streamlit.app','localhost','127.0.0.1'):
        raise ValueError('Only the development app or a local test server may be audited')
    if p.path not in ('','/'):raise ValueError('Use the app root URL')
    return url.rstrip('/')+'/'

def safe_url(url):
    p=urlsplit(url);return urlunsplit((p.scheme,p.netloc,p.path,'',''))

def probe(url):
    url=validate_url(url);p=urlsplit(url);result={'url':url,'dns':{},'requests':[],'reachable':False}
    try:result['dns']={'status':'PASS','addresses':sorted({a[4][0] for a in socket.getaddrinfo(p.hostname,p.port or 443,type=socket.SOCK_STREAM)})}
    except OSError as exc:result['dns']={'status':'NOT VERIFIED','error':str(exc)}
    # Test HTTP redirect behavior separately; HTTPS availability governs the public audit.
    candidates=[url]
    if p.scheme=='https':candidates=['http://'+p.netloc+'/',url]
    for target in candidates:
        row={'requested_url':target}
        try:
            r=requests.get(target,timeout=(15,45),allow_redirects=True)
            row.update(status_code=r.status_code,final_url=safe_url(r.url),content_type=r.headers.get('Content-Type'),
                redirects=[{'status':h.status_code,'url':safe_url(h.url),'location':safe_url(h.headers.get('Location',''))} for h in r.history],
                streamlit_shell=('streamlit' in r.text.lower() or 'id="root"' in r.text.lower()))
            if target==url:result['reachable']=r.status_code==200 and row['streamlit_shell']
        except requests.RequestException as exc:row.update(error=type(exc).__name__+': '+str(exc),status='NOT VERIFIED')
        result['requests'].append(row)
    return result
