"""v3.4.2 UI regression: collapsed sidebar, theme palette, spacing, responsive geometry.
Use real FastAPI-rendered HTML and Chromium's layout engine without external network calls.
"""
import os, tempfile, sys, types, shutil
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

stub = types.ModuleType('app.scheduler')
class Dummy:
    def shutdown(self, wait=False):pass
stub.start_scheduler = lambda _:Dummy()
sys.modules['app.scheduler'] = stub
with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(SESSION_SECRET='v342-layout-session-secret',APP_USERNAME='admin',APP_PASSWORD='v342-test-password',STUDY_NOTIFIER_DB=str(Path(tmp)/'app.db'),COOKIE_SECURE='false')
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app,follow_redirects=True) as client:
        login=client.post('/login',data={'username':'admin','password':'v342-test-password'})
        assert login.status_code==200
        client.post('/life/projects',data={'name':'OPT1 1','area':'Work','template':'blank'})
        for name in ['Prepare report','Review drawings','Complete proposal']:
            client.post('/life/tasks',data={'title':name})
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'], **({'executable_path':(os.environ.get('MLO_BROWSER') or shutil.which('chromium'))} if (os.environ.get('MLO_BROWSER') or shutil.which('chromium')) else {}))
            errors=[]
            def render(page,path):
                html=client.get(path).text
                assert '<html' in html.lower(), (path,html[:250])
                soup=BeautifulSoup(html,'html.parser')
                for n in soup.select('script[src],link[rel="stylesheet"],link[rel="manifest"]'):
                    n.decompose()
                style=soup.new_tag('style')
                style.string='\n'.join((Path('app/static')/n).read_text() for n in ['theme.css','life.css','design32.css','design33.css','flow34.css','polish342.css','polish343.css'])
                soup.head.append(style)
                for name in ['theme.js','life.js','customize.js','flow34.js']:
                    sc=soup.new_tag('script');sc.string=(Path('app/static')/name).read_text();soup.body.append(sc)
                page.set_content(str(soup),wait_until='load')
                page.wait_for_timeout(100)
            def dims(page):
                return page.evaluate('''() => {
                  const rc=x=>{const r=x.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
                  return {viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,
                    sidebar:rc(document.querySelector('.app-sidebar')),
                    main:rc(document.querySelector('.app-main')),
                    icons:[...document.querySelectorAll('.mlo-nav-group .mlo-navglyph')].filter(x=>x.getBoundingClientRect().width>0).length,
                    navScrollWidth:document.querySelector('.sidebar-nav').scrollWidth,
                    navClientWidth:document.querySelector('.sidebar-nav').clientWidth,
                    customize:rc(document.querySelector('.mlo-sidebar-customize-row')),
                    section:rc(document.querySelector('.mlo-sidebar-section-title'))};
                }''')
            desktop=browser.new_page(viewport={'width':1440,'height':900})
            desktop.on('pageerror',lambda e:errors.append(str(e)))
            render(desktop,'/life')
            expanded=dims(desktop)
            desktop.locator('[data-sidebar-collapse]').click()
            desktop.wait_for_timeout(240)
            collapsed=dims(desktop)
            assert collapsed['sidebar']['w']<expanded['sidebar']['w']-80,(collapsed,expanded)
            # Toggle button must remain wholly within the collapsed sidebar rail.
            toggle_bounds=desktop.locator('[data-sidebar-collapse]').bounding_box()
            assert toggle_bounds, 'Sidebar button is hidden'
            assert toggle_bounds['x']>=collapsed['sidebar']['x']-1,(toggle_bounds,collapsed)
            assert toggle_bounds['x']+toggle_bounds['width']<=collapsed['sidebar']['right']+1,(toggle_bounds,collapsed)
            assert collapsed['icons']>=10,collapsed
            assert collapsed['navScrollWidth']<=collapsed['navClientWidth']+2,collapsed
            assert collapsed['customize']['h']==0,collapsed
            assert collapsed['section']['h']==0,collapsed
            assert collapsed['main']['x']<expanded['main']['x']-80,collapsed
            assert collapsed['scrollWidth']<=collapsed['viewport'],collapsed
            assert desktop.locator('[data-sidebar-collapse]').get_attribute('aria-label')=='Expand sidebar'
            desktop.screenshot(path='docs/preview/sidebar-collapsed-v342.png')
            desktop.evaluate('document.documentElement.classList.add("dark");document.documentElement.dataset.palette="ocean"')
            desktop.screenshot(path='docs/preview/sidebar-collapsed-dark-v342.png')
            desktop.evaluate('document.documentElement.classList.remove("dark");document.documentElement.dataset.palette="neutral"')
            desktop.locator('[data-sidebar-collapse]').click()
            desktop.wait_for_timeout(240)
            restored=dims(desktop)
            assert abs(restored['sidebar']['w']-expanded['sidebar']['w'])<=1,restored
            desktop.screenshot(path='docs/preview/sidebar-expanded-v342.png')
            for width,height,label in [(1440,900,'desktop'),(1024,800,'compact-desktop'),(820,900,'tablet'),(390,844,'mobile')]:
                page=browser.new_page(viewport={'width':width,'height':height})
                page.on('pageerror',lambda e:errors.append(str(e)))
                for path,slug in [('/life/insights','insights'),('/life/tasks','tasks'),('/life/projects','projects'),('/life/study','study'),('/life/work','work'),('/life/money','money'),('/life/calendar','calendar'),('/life/focus','focus')]:
                    render(page,path)
                    page.wait_for_timeout(25)
                    d=page.evaluate('''() => ({window:innerWidth,scroll:document.documentElement.scrollWidth})''')
                    assert d['scroll']<=d['window']+2,(label,slug,d)
                    if slug=='insights':
                        gaps=page.evaluate('''() => {
                            const root=document.querySelector('.mlo-insights-page');
                            const rows=[...root.children].filter(x=>getComputedStyle(x).display!=='none');
                            return rows.slice(1).map((x,i)=>Math.round(x.getBoundingClientRect().top-rows[i].getBoundingClientRect().bottom));
                        }''')
                        assert gaps and min(gaps)>=10,(label,gaps)
                        cards=page.locator('.mlo-insights-page>.mlo-two .mlo-surface')
                        assert cards.count()==4,(label,cards.count())
                        page.screenshot(path=f'docs/preview/{label}-insights-v342.png',full_page=(width<=820))
                        if label=='desktop':
                            page.evaluate('document.documentElement.classList.add("dark");document.documentElement.dataset.palette="ocean"')
                            page.screenshot(path='docs/preview/desktop-insights-dark-v342.png')
                page.close()
            # Whole-shell audit: new and legacy areas at two screen sizes.
            routes=['/life','/life/tasks','/life/projects','/life/calendar','/life/focus',
                    '/life/notes','/life/insights','/life/goals','/life/search',
                    '/life/devices','/life/import','/life/study','/life/work','/life/money',
                    '/life/spaces','/life/calendars','/courses','/items','/classes',
                    '/expenses','/jobs','/settings','/admin/users']
            # Route integrity sweep for all main modules, without repeatedly
            # booting full browser scripts (which can overload the CI runner).
            for path in routes:
                response=client.get(path,follow_redirects=False)
                assert response.status_code in (200,301,302,303,307,308),(path,response.status_code)
            for w in [390,1440]:
                audit=browser.new_page(viewport={'width':w,'height':900})
                for path in ['/life','/life/tasks','/life/insights','/life/projects',
                             '/life/calendar','/life/study','/life/money','/life/spaces']:
                    render(audit,path)
                    info=audit.evaluate('() => ({scroll:document.documentElement.scrollWidth,window:innerWidth})')
                    assert info['scroll']<=info['window']+2,(path,w,info)
                audit.close()
            assert not errors,errors
            browser.close()
print('PASS v3.4.2: collapsed sidebar & icons; no x-scroll; Insights gaps; eight pages across four viewports')
