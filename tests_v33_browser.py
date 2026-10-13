"""Integrated UI tests: real Chromium + real FastAPI TestClient, bridged without network."""
import os, tempfile, types, sys, json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
stub=types.ModuleType('app.scheduler')
class Dummy:
 def shutdown(self,wait=False):pass
stub.start_scheduler=lambda _:Dummy()
sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as tmp:
 os.environ.update({'SESSION_SECRET':'v33-browser-session','APP_USERNAME':'admin','APP_PASSWORD':'browser-test-password','STUDY_NOTIFIER_DB':str(Path(tmp)/'app.db'),'COOKIE_SECURE':'false'})
 from app.main import app
 from fastapi.testclient import TestClient
 with TestClient(app,follow_redirects=True) as client:
  client.post('/login',data={'username':'admin','password':'browser-test-password','next':'/life'})
  client.post('/life/projects',data={'name':'Release Design Test','area':'Work','template':'blank'})
  client.post('/life/tasks',data={'title':'Test the new dashboard','next_page':'/life'})
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium',args=['--no-sandbox'])
   from bs4 import BeautifulSoup
   page=browser.new_page(viewport={'width':1440,'height':900})
   errors=[]
   def backend(path,request_data):
    options=json.loads(request_data)
    method=options.get('method','GET')
    kwargs={'method':method,'url':path,'follow_redirects':True}
    if method=='POST':
     if options.get('form') is not None:
      kwargs['data']={str(k):str(v) for k,v in options['form']}
      kwargs['headers']={'X-MLO-Action':options.get('mloAction','')}
     else:
      kwargs['content']=options.get('body','').encode('utf8')
      kwargs['headers']={'Content-Type':options.get('contentType','application/json'),'X-MLO-Action':options.get('mloAction','')}
    response=client.request(**kwargs)
    return {'ok':response.is_success,'status':response.status_code,'text':response.text}
   page.expose_function('mloBackend',backend)
   page.evaluate("""(() => {
       window.fetch=async (path,options={}) => {
         const result=await window.mloBackend(path,JSON.stringify({method:options.method||'GET',body:typeof options.body==='string'?options.body:'',form:options.body instanceof FormData ? [...options.body.entries()]:null,contentType:options.headers?.['Content-Type']||'application/json',mloAction:options.headers?.['X-MLO-Action']||''}));
         return {ok:result.ok,status:result.status,json:async()=>JSON.parse(result.text),text:async()=>result.text};
       };
     })();""")
   def render_page(path='/life',target=None):
    html=client.get(path).text
    soup=BeautifulSoup(html,'html.parser')
    for node in soup.select('script[src], link[rel="stylesheet"],link[rel="manifest"]'):
     node.decompose()
    style=soup.new_tag('style')
    style.string='\n'.join(Path('app/static/'+name).read_text() for name in ['theme.css','life.css','design32.css','design33.css'])
    soup.head.append(style)
    for name in ['theme.js','life.js','customize.js']:
     script=soup.new_tag('script')
     script.string=Path('app/static/'+name).read_text()
     soup.body.append(script)
    (target or page).set_content(str(soup),wait_until='load')
   render_page()
   page.on('pageerror',lambda error: errors.append(str(error)))
   page.wait_for_function('document.querySelectorAll("[data-widget]").length > 8')
   page.wait_for_timeout(600)
   assert not errors,errors
   assert page.locator('.mlo-blue-art').count()==1
   # Palette styling must respond to v3.1 settings, no forced green.
   page.evaluate("window.__setPalette('rose'); window.__setPaletteStyle('full')")
   assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()")=='#fdfafb'
   assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--mlo-accent').trim()")=='#a85c6b'
   assert page.locator('.mlo-widget-welcome').evaluate("e => getComputedStyle(e).backgroundImage").startswith('linear-gradient')
   page.evaluate("window.__setPalette('ocean')")
   assert page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--mlo-accent').trim()")=='#2878c8'
   page.locator('.mlo-capture input[name=title]').fill('Quick capture works')
   page.locator('.mlo-capture button[type=submit]').click()
   page.wait_for_timeout(350)
   assert page.locator('.mlo-widget-tasks').get_by_text('Quick capture works').count()==1
   page.get_by_role('button',name='Arrange').click()
   assert page.locator('[data-widget-settings]').is_visible()
   assert page.locator('[data-widget-grid]').evaluate("e=>getComputedStyle(e).gridAutoFlow")=='row'
   assert page.locator('.mlo-widget-handle').first.get_attribute('draggable')=='true'
   before=page.locator('[data-widget]').evaluate_all('(els)=>els.map(e=>e.dataset.widget)')
   # Keyboard accessible move and save.
   page.locator('[data-widget="welcome"] .mlo-widget-handle').focus()
   page.keyboard.press('ArrowDown')
   page.wait_for_timeout(850)
   after=page.locator('[data-widget]').evaluate_all('(els)=>els.map(e=>e.dataset.widget)')
   assert before!=after,(before,after)
   assert client.get('/life/layout').json()['widget_order'][:2]==after[:2]
   # Restore defaults and exercise hide + drag on desktop.
   page.locator('[data-widget-reset]').click()
   page.wait_for_timeout(600)
   page.locator('[data-widget="calendar"] .mlo-widget-handle').drag_to(page.locator('[data-widget="tasks"]'))
   page.wait_for_timeout(650)
   changed=page.locator('[data-widget]').evaluate_all('(els)=>els.map(e=>e.dataset.widget)')
   assert changed!=before,(changed,before)
   assert client.get('/life/layout').json()['widget_order'][:len(changed)]==changed
   # widget hide and show
   page.get_by_role('combobox',name='Width for Projects').select_option('8')
   page.wait_for_timeout(600)
   assert client.get('/life/layout').json()['widget_sizes']['projects']==8
   assert page.locator('[data-widget="projects"]').get_attribute('data-widget-width')=='8'
   page.get_by_role('checkbox',name='Show Money').uncheck()
   page.wait_for_timeout(650)
   assert 'money' in client.get('/life/layout').json()['widget_hidden']
   page.get_by_role('button',name='Done').click()
   assert page.locator('[data-widget="money"]').is_hidden()
   render_page();page.wait_for_timeout(600)
   assert page.locator('[data-widget="money"]').is_hidden()
   assert page.locator('[data-widget="projects"]').get_attribute('data-widget-width')=='8'
   assert page.locator('[data-widget]').evaluate_all('(els)=>els.map(e=>e.dataset.widget)')==changed
   # Sidebar labels and order survive reload
   page.locator('[data-nav-edit]').click()
   field=page.get_by_role('textbox',name='Rename Dashboard')
   field.fill('My Home');field.press('Tab')
   page.wait_for_timeout(650)
   assert 'My Home' in page.locator('[data-nav-key="life-home"]').inner_text()
   page.get_by_role('button',name='Move Dashboard down').click()
   page.wait_for_timeout(650)
   assert client.get('/life/layout').json()['nav_labels']['life-home']=='My Home'
   render_page();page.wait_for_timeout(600)
   assert 'My Home' in page.locator('[data-nav-key="life-home"]').inner_text()
   assert not errors,errors
   Path('docs/preview').mkdir(parents=True,exist_ok=True)
   for width,height,label in [(1440,900,'desktop'),(820,900,'tablet'),(390,850,'mobile')]:
    preview=browser.new_page(viewport={'width':width,'height':height})
    render_page(target=preview)
    preview.evaluate("window.__setPalette('ocean');window.__setPaletteStyle('full');document.activeElement.blur()")
    preview.wait_for_timeout(250)
    assert preview.locator('.mlo-capture .mlo-primary').evaluate("e=>getComputedStyle(e).backgroundColor")=='rgb(40, 120, 200)'
    assert preview.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'{label} page scrolls horizontally'
    preview.screenshot(path=f'docs/preview/{label}-v33.png',full_page=(label=='mobile'))
    preview.close()
   page.close()
   browser.close()
print('PASS v3.3: palettes, blue hero, keyboard/drag ordering, persistence, hiding, sidebar rename/order, responsive Chromium')
