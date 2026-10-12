"""Static visual snapshots with locally inlined CSS when browser loopback is restricted."""
import os,sys,tempfile,types
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
class NoopScheduler:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:NoopScheduler();sys.modules['app.scheduler']=stub
work=tempfile.TemporaryDirectory();os.environ.update({'SESSION_SECRET':'visual-preview-session-secret','APP_USERNAME':'admin','APP_PASSWORD':'admin-test-password','STUDY_NOTIFIER_DB':str(Path(work.name)/'visual.db'),'COOKIE_SECURE':'false'})
from app.main import app
from fastapi.testclient import TestClient
from app.db import get_conn
with TestClient(app,follow_redirects=True) as client:
    client.post('/login',data={'username':'admin','password':'admin-test-password','next':'/life'})
    client.post('/life/projects',data={'name':'Substation Panel Upgrade','template':'electrical','area':'Work'})
    client.post('/life/tasks',data={'title':'Submit the schematic package','due_on':'2026-10-16','priority':'high'})
    css=(Path('app/static/theme.css').read_text()+"\n"+Path('app/static/life.css').read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--allow-file-access-from-files'])
        for size,label in [({'width':1440,'height':900},'desktop'),({'width':390,'height':844},'mobile'),({'width':820,'height':1000},'tablet')]:
            page=browser.new_page(viewport=size,device_scale_factor=1)
            for path,page_name in [('/life','home'),('/life/projects','projects'),('/life/projects/1','project_detail'),('/life/tasks','tasks')]:
                html=client.get(path).text
                doc=BeautifulSoup(html,'html.parser')
                for tag in doc.find_all('link',rel='stylesheet'): tag.decompose()
                for tag in doc.find_all('script'):tag.decompose()
                st=doc.new_tag('style');st.string=css;doc.head.append(st)
                page.set_content(str(doc),wait_until='load')
                filename=f'/mnt/data/mlo_{label}_{page_name}_preview.png'
                page.screenshot(path=filename,full_page=True)
                print(label,page_name,'hscroll?',page.evaluate('document.body.scrollWidth > window.innerWidth'))
            page.close()
        browser.close()
work.cleanup()
