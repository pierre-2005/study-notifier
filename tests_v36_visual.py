"""A real Chromium rendering check of destructive-action panel in 12 theme combinations."""
import os,sys,tempfile,types,shutil
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class Scheduler:
 def shutdown(self,wait=False): pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda tz:Scheduler();sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as d:
 os.environ.update(STUDY_NOTIFIER_DB=str(Path(d)/'test.db'),SESSION_SECRET='some-dev-test-key',COOKIE_SECURE='false',APP_USERNAME='admin',APP_PASSWORD='admin-password-strong')
 from fastapi.testclient import TestClient
 from app.main import app
 from app.db import get_conn
 with TestClient(app,follow_redirects=True) as client:
  client.post('/login',data={'username':'admin','password':'admin-password-strong'})
  client.post('/life/projects',data={'name':'REEF','area':'Work','template':'blank'})
  with get_conn() as c: pid=c.execute("SELECT id FROM life_projects WHERE name='REEF'").fetchone()['id']
  soup=BeautifulSoup(client.get(f'/life/projects/{pid}').text,'html.parser')
  for el in soup.select('link[rel="stylesheet"],script'):el.decompose()
  style=soup.new_tag('style');style.string='\n'.join((Path('app/static')/f).read_text() for f in ('theme.css','life.css','design32.css','design33.css','flow34.css','polish342.css','polish343.css'))
  soup.head.append(style)
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,args=['--no-sandbox'],**({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}))
   page=browser.new_page(viewport={'width':1400,'height':900})
   page.set_content(str(soup),wait_until='load')
   card=page.locator('.mlo-danger-area').first
   card.locator('summary').click()
   def contrast(selector):
    return page.evaluate('''(sel) => {
     const el=document.querySelector(sel);if(!el)return -1;
     const nums=(s)=>((s.match(/[\\d.]+/g)||[]).map(Number));
     const foreground=nums(getComputedStyle(el).color), background=nums(getComputedStyle(el).backgroundColor);
     const bg=background.length>2&&background[3]!==0?background:nums(getComputedStyle(el.closest('.mlo-danger-area')).backgroundColor);
     const lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
     const a=lum(foreground),b=lum(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    }''',selector)
   failures=[]
   out=Path('docs/preview');out.mkdir(parents=True,exist_ok=True)
   for mode in ('light','dark'):
    for palette in ('neutral','ocean','sage','rose','amber','lavender'):
     page.evaluate('''([mode,palette])=>{document.documentElement.classList.toggle('dark',mode==='dark');document.documentElement.dataset.palette=palette}''',[mode,palette]);page.wait_for_timeout(100)
     for sel in ('.mlo-danger-area summary','.mlo-danger-area input','.mlo-danger-area .mlo-danger-btn'):
      v=contrast(sel)
      if v<4.5: failures.append((mode,palette,sel,round(v,2)))
     if palette=='ocean':
      card.screenshot(path=str(out/f'project-delete-{mode}-v36.png'))
   for width in (375,768,1280):
    page.set_viewport_size({'width':width,'height':900})
    card.scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),('overflow',width)
   browser.close()
   assert not failures, failures
print('PASS v3.6: deletion panel contrast across 6 palettes x light/dark; 3 responsive widths')
