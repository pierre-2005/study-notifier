"""Check the actual publicly deployed MLO PWA from a machine outside the server.
Usage: python tools/check_live_pwa.py https://organizer.overvault.ca
"""
import json, sys, urllib.request, urllib.error
from urllib.parse import urljoin
from html.parser import HTMLParser
class Links(HTMLParser):
    hrefs=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=='link' and 'manifest' in d.get('rel','').split(): self.hrefs.append(d.get('href',''))

def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'MLO-PWA-Health-Check/1.0'}),timeout=15) as r:
            return r.status,r.headers,r.read(1024*512),r.url
    except (urllib.error.URLError,TimeoutError) as exc:
        print('FAILED:',url,str(exc));return 0,{},b'',url

root=sys.argv[1].rstrip('/')+'/' if len(sys.argv)>1 else 'https://organizer.overvault.ca/'
print('Checking publicly accessible website:',root)
status,headers,body,final=fetch(root);print('Home:',status,'redirected:',final!=root,'type:',headers.get('Content-Type'))
parser=Links();parser.feed(body.decode('utf-8','replace'))
print('Manifest links in public homepage:',parser.hrefs)
manifest=urljoin(root,parser.hrefs[0]) if parser.hrefs else urljoin(root,'manifest.webmanifest')
status,headers,body,final=fetch(manifest)
print('Manifest:',status,'URL:',final,'type:',headers.get('Content-Type'))
if status==200:
    try:
        obj=json.loads(body)
        print('Manifest name:',obj.get('name'),'description:',bool(obj.get('description')),'icons:',[(i.get('sizes'),i.get('src')) for i in obj.get('icons',[])])
        for icon in obj.get('icons',[]):
            st,_,b,_=fetch(urljoin(root,icon.get('src','')))
            print('  Icon:',icon.get('sizes'),st,'PNG:',b.startswith(b'\x89PNG'))
    except ValueError as exc:print('INVALID MANIFEST JSON:',exc)
status,headers,body,final=fetch(urljoin(root,'service-worker.js'))
print('Service worker:',status,'type:',headers.get('Content-Type'),'JS:',b'self.addEventListener' in body)
if not parser.hrefs or status!=200:
    print('Action: Check Portainer image tag, Cloudflare Access/WAF, Cloudflare caching and live response headers. PWABuilder must access these anonymously.')
