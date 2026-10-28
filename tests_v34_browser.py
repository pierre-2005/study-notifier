"""Browser check for new task filters, multi-select, insights and global task dialog."""
import json,os,sys,tempfile,types
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
class Dummy:
    def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler')
stub.start_scheduler=lambda _:Dummy()
sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as d:
    os.environ.update(SESSION_SECRET='browser-v34',APP_USERNAME='admin',APP_PASSWORD='browser-pass-v34',STUDY_NOTIFIER_DB=str(Path(d)/'mlo.db'),COOKIE_SECURE='false')
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app,follow_redirects=True) as client:
        client.post('/login',data={'username':'admin','password':'browser-pass-v34'})
        for title in ['Prepare draft','Finish report','Build prototype']:
            client.post('/life/tasks',data={'title':title})
        def backend(path,options):
            if not isinstance(path,str):return {'ok':False,'status':404,'text':'{}'}
            d=json.loads(options)
            kwargs={'method':d.get('method','GET'),'url':path,'follow_redirects':False}
            if kwargs['method']=='POST':
                if d.get('form') is not None:
                    kwargs['data']={str(k):str(v) for k,v in d['form']}
                    kwargs['headers']={'X-MLO-Action':d.get('mloAction','')}
                else:
                    kwargs['content']=d.get('body','').encode('utf-8')
                    kwargs['headers']={'Content-Type':d.get('contentType','application/json'),'X-MLO-Action':d.get('mloAction','')}
            r=client.request(**kwargs)
            return {'ok':r.is_success,'status':r.status_code,'text':r.text}
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('MLO_BROWSER') or __import__('shutil').which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':900})
            page.expose_function('mloBackend',backend)
            page.evaluate("""window.fetch=async (path,options={})=>{
                let result=await window.mloBackend(path,JSON.stringify({method:options.method||'GET',form:options.body instanceof FormData?[...options.body.entries()]:null,body:typeof options.body==='string'?options.body:'',contentType:options.headers?.['Content-Type']||'application/json',mloAction:options.headers?.['X-MLO-Action']||''}));
                return {ok:result.ok,status:result.status,json:async()=>JSON.parse(result.text),text:async()=>result.text};
            };""")
            def render(path,view=page):
                soup=BeautifulSoup(client.get(path).text,'html.parser')
                for n in soup.select('script[src],link[rel="stylesheet"],link[rel="manifest"]'):n.decompose()
                st=soup.new_tag('style')
                st.string='\n'.join((Path('app/static')/n).read_text() for n in ('app.css',))
                soup.head.append(st)
                for n in ['theme.js','life.js','customize.js','capture.js']:
                    sc=soup.new_tag('script');sc.string=(Path('app/static')/n).read_text();soup.body.append(sc)
                view.set_content(str(soup),wait_until='load')
            errors=[]
            page.on('pageerror',lambda err:errors.append(str(err)))
            render('/life/tasks')
            page.keyboard.press('n')
            assert page.locator('[data-global-capture-dialog]').is_visible()
            page.locator('[data-global-capture-form] input[name="title"]').fill('Captured from keyboard')
            page.locator('[data-global-capture-form] select[name="schedule"]').select_option('tomorrow')
            page.locator('[data-global-capture-form] button[type=submit]').click()
            page.wait_for_timeout(450)
            assert page.locator('[data-global-capture-dialog]').is_hidden()
            assert 'Captured from keyboard' in client.get('/life/tasks?q=Captured+from+keyboard').text
            render('/life/tasks')
            assert page.locator('[data-task-select]').count()==4
            assert page.locator('[data-bulk-submit]').is_disabled()
            page.locator('[data-select-page]').check()
            assert page.locator('[data-selected-count]').inner_text()=='4'
            assert page.locator('[data-bulk-submit]').is_enabled()
            page.locator('[data-task-select]').first.uncheck()
            assert page.locator('[data-selected-count]').inner_text()=='3'
            page.locator('h1').click()
            page.keyboard.press('n')
            assert page.locator('[data-global-capture-dialog]').is_visible()
            page.keyboard.press('Escape')
            assert page.locator('[data-global-capture-dialog]').is_hidden()
            render('/life/insights')
            assert page.locator('.mlo-bar-chart').count()==2
            assert page.locator('.mlo-insight-kpis').count()==1
            assert not errors,errors
            Path('docs/preview').mkdir(exist_ok=True,parents=True)
            for width,height,label in [(1440,900,'desktop'),(820,900,'tablet'),(390,844,'mobile')]:
                check=browser.new_page(viewport={'width':width,'height':height})
                for path,slug in [('/life/tasks','tasks'),('/life/insights','insights')]:
                    render(path,check)
                    check.wait_for_timeout(100)
                    assert check.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),(label,slug,check.evaluate('document.documentElement.scrollWidth'),width)
                    check.screenshot(path=f'docs/preview/{label}-{slug}-v34.png',full_page=(label=='mobile'))
                check.close()
            browser.close()
print('PASS v3.4 browser: keyboard capture; selection; insights; responsive tasks/insights')
