"""Regression: controls are readable under every MLO palette in both themes."""
from __future__ import annotations
import os
import sys
import tempfile
import types
import shutil
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class NoopScheduler:
    def shutdown(self, wait=False):
        pass

scheduler = types.ModuleType('app.scheduler')
scheduler.start_scheduler = lambda _: NoopScheduler()
sys.modules['app.scheduler'] = scheduler

PALETTES = ('neutral', 'ocean', 'sage', 'rose', 'amber', 'lavender')
CSS = ('theme.css', 'life.css', 'design32.css', 'design33.css', 'flow34.css')
SELECTORS = (
    '.mlo-saved-filters',
    '.mlo-saved-filters summary',
    '.mlo-task-filters input',
    '.mlo-task-filters select',
    '.mlo-bulkbar select',
    '.mlo-save-filter-form input',
    '.mlo-bulk-select',
    '.mlo-task-filters label',
    '.mlo-bulkbar',
    '.mlo-task-filters .mlo-primary',
)

CONTRAST_SCRIPT = r'''(selectors) => {
  const parse = s => {
    const a = s.match(/[\d.]+/g).map(Number);
    return [a[0], a[1], a[2], a.length > 3 ? a[3] : 1];
  };
  const blend = (a, b) => a[3] === 1 ? a.slice(0,3) : a.slice(0,3).map((x,i) => x*a[3] + b[i]*(1-a[3]));
  const bg = el => {
    const stack = [];
    while (el) { stack.push(parse(getComputedStyle(el).backgroundColor)); el=el.parentElement; }
    let current = [255,255,255];
    for (const color of stack.reverse()) current = blend(color,current);
    return current;
  };
  const lum = c => c.map(x=>x/255).map(x=>x<=.04045 ? x/12.92 : ((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
  const contrast = (a,b) => { const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); };
  return selectors.map(sel=>{
    const el=document.querySelector(sel);
    if(!el) return {sel,missing:true};
    const f=parse(getComputedStyle(el).color).slice(0,3), b=bg(el);
    return {sel,foreground:f,background:b,contrast:Number(contrast(f,b).toFixed(2)), cssBackground:getComputedStyle(el).backgroundColor};
  });
}'''

with tempfile.TemporaryDirectory() as d:
    os.environ.update(SESSION_SECRET='v341-contrast-test', APP_USERNAME='admin',APP_PASSWORD='v341-contrast-pass',STUDY_NOTIFIER_DB=str(Path(d)/'test.db'),COOKIE_SECURE='false')
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app, follow_redirects=True) as client:
        response=client.post('/login',data={'username':'admin','password':'v341-contrast-pass'})
        assert response.status_code==200
        client.post('/life/tasks',data={'title':'Check contrast of Tasks components'})
        client.post('/life/tasks/views',data={'name':'My saved view','view':'open','priority':'high'})
        soup = BeautifulSoup(client.get('/life/tasks').text,'html.parser')
        for element in soup.select('link[rel="stylesheet"],script,link[rel="manifest"]'):
            element.decompose()
        style=soup.new_tag('style')
        style.string='\n'.join((Path('app/static')/name).read_text() for name in CSS)
        soup.head.append(style)
        html=str(soup)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True, args=['--no-sandbox'], **({'executable_path':shutil.which('chromium')} if shutil.which('chromium') else {}))
            page=browser.new_page(viewport={'width':1440,'height':900})
            page.set_content(html,wait_until='load')
            failures=[]
            out=Path('docs/preview')
            out.mkdir(parents=True,exist_ok=True)
            for mode in ('light','dark'):
                for palette in PALETTES:
                    page.evaluate('''([mode,palette])=>{document.documentElement.classList.toggle('dark',mode==='dark');document.documentElement.dataset.palette=palette}''',[mode,palette])
                    page.wait_for_timeout(220)  # wait for CSS palette transitions
                    values=page.evaluate(CONTRAST_SCRIPT,SELECTORS)
                    for result in values:
                        if result.get('missing') or result.get('contrast',0)<4.5:
                            failures.append((mode,palette,result))
                    if palette in ('neutral','ocean'):
                        page.screenshot(path=str(out/f'tasks-{mode}-{palette}-v341.png'),full_page=False)
            assert not failures,'Low contrast detected: '+repr(failures)
            # Confirm native controls do not fall back to white in dark mode.
            page.evaluate("document.documentElement.classList.add('dark')")
            actual=page.locator('.mlo-task-filters select').first.evaluate('el=>getComputedStyle(el).backgroundColor')
            assert actual != 'rgb(255, 255, 255)',actual
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
            browser.close()
print('PASS v3.4.1: 6 palettes x 2 modes; labels, dropdowns, controls, saved filters readable')
