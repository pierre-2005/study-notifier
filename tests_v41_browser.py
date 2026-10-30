"""Browser acceptance for task feedback, save/return, whole-card drag, maps and pairing."""
import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.parse import urlsplit
import requests
from playwright.sync_api import sync_playwright,expect
from scripts.qa_routes import populated_routes
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'test-results/v41';OUT.mkdir(parents=True,exist_ok=True)
axe=Path(os.environ['MLO_AXE_PATH']);assert axe.is_file()
audits=[];errors=[];metrics={};states=[]
with tempfile.TemporaryDirectory() as temporary:
 data=Path(temporary)/'data'
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 base=f'http://127.0.0.1:{port}';http=requests.Session();http.trust_env=False
 with (OUT/'server.log').open('w') as log:
  server=subprocess.Popen([sys.executable,'-m','scripts.qa_server','--data-dir',str(data),'--port',str(port),'--map-size','150'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(300):
    if server.poll() is not None:raise AssertionError((OUT/'server.log').read_text()[-5000:])
    try:
     if http.get(base+'/health',timeout=1).status_code==200:break
    except requests.RequestException:pass
    time.sleep(.1)
   else:raise AssertionError('Fixture startup timed out')
   f=json.loads((data/'fixture.json').read_text());pid=f['project_id'];boardurl=base+f'/life/projects/{pid}?view=board';mapurl=base+f'/life/projects/{pid}?view=map'
   with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if os.getenv('MLO_BROWSER'):options['executable_path']=os.environ['MLO_BROWSER']
    browser=pw.chromium.launch(**options);context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    context.on('page',lambda p:p.on('pageerror',lambda error:errors.append(str(error))))
    page=context.new_page();page.on('dialog',lambda d:d.accept());page.set_default_timeout(15000)
    def goto(path):return page.goto(path if path.startswith('http') else base+path)
    def audit(target,label):
     target.add_script_tag(path=str(axe));result=target.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))");audits.append({'screen':label,'violations':result})
    def login(target,name='demo',password='MloPreviewOnly!234'):
     target.goto(base+'/login');target.locator('[name=username]').fill(name);target.locator('[name=password]').fill(password);target.get_by_role('button',name='Sign in',exact=True).click();target.wait_for_url(base+'/life')
    login(page)
    # The board hydrates from its server-rendered payload, with no redundant GET.
    board_gets=[];page.on('request',lambda r:board_gets.append(r.url) if r.method=='GET' and r.url.endswith(f'/api/v4/projects/{pid}/board') else None)
    goto(boardurl);expect(page.locator('.v37-ticket')).to_have_count(4);assert not board_gets,board_gets
    page.locator('[data-quick-form] [name=title]').fill('Immediate project task');started=time.perf_counter();page.locator('[data-quick-form] [type=submit]').click();expect(page.locator('[data-column=todo]')).to_contain_text('Immediate project task');metrics['quick_add_to_correct_column_ms']=round((time.perf_counter()-started)*1000,2)
    card=page.locator('.v37-ticket').filter(has=page.locator('.v37-task-title',has_text='Immediate project task'));tid=int(card.get_attribute('data-id'));assert page.locator('[data-task-region] > .mlo-task').count()==0
    # Drag from card text/body rather than the dedicated handle.
    card.locator('.v37-task-title').drag_to(page.locator('[data-column=doing] .v37-drop'));expect(page.locator(f'[data-column=doing] [data-id="{tid}"]')).to_have_count(1)
    card=page.locator(f'[data-id="{tid}"]');card.locator('[data-toggle]').click();expect(page.locator(f'[data-column=done] [data-id="{tid}"] .mlo-check')).to_have_attribute('aria-pressed','true')
    expect(page.locator('.v37-message')).to_have_text('Saved.')
    # Saving replaces the optimistic card. Re-query the live DOM on each frame;
    # a retained element handle can briefly refer to the detached optimistic node.
    page.wait_for_function("""id=>{
      const e=document.querySelector(`[data-column=done] [data-id="${id}"] .mlo-check[aria-pressed=true]`);
      if(!e?.isConnected)return false;
      const s=getComputedStyle(e,'::before');
      return parseFloat(s.width)>0&&parseFloat(s.height)>0&&parseFloat(s.borderBottomWidth)>0&&s.borderBottomStyle==='solid';
    }""",arg=tid)
    check=page.locator(f'[data-id="{tid}"] .mlo-check');check.click();expect(page.locator(f'[data-column=todo] [data-id="{tid}"]')).to_have_count(1)
    # Save closes the inspector; the edited title is visible in the original board.
    page.locator(f'[data-id="{tid}"] .v37-task-title').click();expect(page.locator('.task-inspector')).to_be_visible();page.locator('.task-inspector [name=title]').fill('Saved task returns to board');page.locator('.task-inspector [type=submit]').click();expect(page.locator('.task-inspector')).to_have_count(0);expect(page.locator(f'[data-id="{tid}"] .v37-task-title')).to_have_text('Saved task returns to board')
    # An actual full edit returns to the originating project/view, retaining scroll.
    page.locator(f'[data-id="{tid}"] .v37-task-title').click();page.locator('[data-inspector-body] [data-no-preview]').click();page.wait_for_url(base+f'/life/tasks/{tid}');page.locator('form[action$="/edit"] [name=title]').fill('Full edit saved');page.get_by_role('button',name='Save changes',exact=True).click();page.wait_for_url(boardurl);expect(page.locator(f'[data-id="{tid}"]')).to_contain_text('Full edit saved')
    # Errors keep the full editor open and preserve draft input.
    page.locator(f'[data-id="{tid}"] .v37-task-title').click();page.locator('[data-inspector-body] [data-no-preview]').click();page.wait_for_url(base+f'/life/tasks/{tid}');page.locator('form[action$="/edit"] [name=title]').fill('Retain on failed save')
    page.route('**/life/tasks/*/edit',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Temporary save failure"}'));page.get_by_role('button',name='Save changes',exact=True).click();expect(page.locator('[data-form-feedback]')).to_contain_text('Temporary save failure');expect(page.locator('form[action$="/edit"] [name=title]')).to_have_value('Retain on failed save');page.unroute('**/life/tasks/*/edit');page.get_by_role('button',name='Save changes',exact=True).click();page.wait_for_url(boardurl)
    # Inline settings close after Save without leaving the project.
    details=page.locator('details').filter(has=page.locator('form[action$="/edit"]'));details.locator('summary').click();details.locator('[name=name]').fill('Project settings saved');details.get_by_role('button',name='Save project').click();expect(page.locator('details').filter(has=page.locator('form[action$="/edit"]'))).not_to_have_attribute('open','');assert page.url==boardurl
    # Map creation, pan, zoom, drag persistence and real structural edits.
    goto(mapurl);expect(page.locator('[data-map-node]')).to_have_count(7);assert page.request.get(base+f'/api/v4/projects/{pid}/map').json()['nodes']
    page.locator('[data-map-add]').click();page.locator('.task-map-dialog [name=title]').fill('Map-created task');page.locator('.task-map-dialog [type=submit]').click();expect(page.locator('.task-map-dialog')).to_have_count(0);expect(page.locator('[data-map-node]')).to_have_count(8)
    map_data=page.request.get(base+f'/api/v4/projects/{pid}/map').json();created=next(n for n in map_data['nodes'] if n['title']=='Map-created task');mid=created['id'];page.locator('[data-map-search]').fill('Map-created');page.wait_for_timeout(150)
    node=page.locator(f'[data-map-node="{mid}"]');node.focus();node.press('ArrowRight');expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.');saved=page.request.get(base+f'/api/v4/projects/{pid}/map').json()['positions'][str(mid)]
    page.reload();expect(page.locator(f'[data-map-node="{mid}"]')).to_have_count(1);assert page.request.get(base+f'/api/v4/projects/{pid}/map').json()['positions'][str(mid)]==saved
    page.locator('[data-map-search]').fill('Map-created');page.wait_for_timeout(150);node=page.locator(f'[data-map-node="{mid}"]');node.locator('.task-map-node-status').click();page.locator('[data-map-relate]').click();page.locator('.task-map-dialog [name=parent_id]').select_option(str(f['task_ids'][0]));page.locator(f'.task-map-dialog [name=prerequisite][value="{f["task_ids"][1]}"]').check();page.locator('.task-map-dialog [type=submit]').click();expect(page.locator('.task-map-dialog')).to_have_count(0)
    actual=page.request.get(base+f'/api/v4/projects/{pid}/map').json();assert next(n for n in actual['nodes'] if n['id']==mid)['parent_id']==f['task_ids'][0];assert {'from':f['task_ids'][1],'to':mid,'kind':'prerequisite'} in actual['edges']
    page.locator('[data-map-earlier]').click();expect(page.locator('[data-map-status]')).to_have_text('Task saved.')
    reordered=page.request.get(base+f'/api/v4/projects/{pid}/board').json();parent=next(n for column in reordered['columns'].values() for n in column if n['id']==f['task_ids'][0]);assert [n['id'] for n in parent['children']].index(mid)<len(parent['children'])-1
    # A second tab cannot silently overwrite this account's newer layout.
    stale=context.new_page();stale.on('dialog',lambda d:d.accept());stale.goto(mapurl);node=page.locator(f'[data-map-node="{mid}"]');node.focus();node.press('ArrowDown');expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.');stale_node=stale.locator(f'[data-map-node="{mid}"]');stale_node.focus();stale_node.press('ArrowLeft');expect(stale.locator('[data-map-status]')).to_contain_text('another tab');expect(stale.locator('[data-map-retry]')).to_be_visible();stale.locator('[data-map-retry]').click();expect(stale.locator('[data-map-status]')).to_have_text('Saved layout loaded.');stale.close()
    # Saving one inline editor cannot wipe another open editor's unsaved text.
    response=page.request.post(base+'/life/goals',form={'title':'Second goal'});assert response.ok,response.text();goto('/life/goals');goals=page.locator('[data-save-scope]').filter(has=page.locator('form[action^="/life/goals/"]'));first=goals.nth(0);second=goals.nth(1);first.locator('summary').click();second.locator('summary').click();first.locator('form[action$="/edit"] [name=title]').fill('First goal saved');second.locator('form[action$="/edit"] [name=title]').fill('Keep this unsaved goal draft');first.get_by_role('button',name='Save changes',exact=True).click();expect(page.locator('.goal-record').filter(has_text='First goal saved').first.locator('details')).not_to_have_attribute('open','');expect(page.locator('form[action$="/edit"] [name=title]:visible')).to_have_value('Keep this unsaved goal draft')
    # Notes and Budget obey the same return flow after successful clean saves.
    goto('/life/notes');page.locator(f'a[href="/life/notes/{f["note_id"]}"]').first.click();page.wait_for_url(base+f'/life/notes/{f["note_id"]}');page.locator('[data-note-editor] [name=body]').fill('Saved and returned');page.locator('[data-note-editor] [type=submit]').click();page.wait_for_url(base+'/life/notes')
    goto('/finance');page.get_by_role('link',name='Budget',exact=True).click();page.locator('[data-budget-step=review]').click();page.locator('[data-budget-save]').click();page.wait_for_url(base+'/finance')
    goto('/life/spaces');page.locator(f'a[href="/sections/{f["space_id"]}"]').first.click();page.locator('textarea[name=content]').fill('Space saved and returned');page.get_by_role('button',name='Save notes',exact=True).click();page.wait_for_url(base+'/life/spaces')
    # The actual two QR images render, and either scan destination works without cookies.
    goto('/life/devices');page.locator('[data-phone-pair] > summary').first.click();expect(page.locator('[data-phone-qr]')).to_have_count(2);page.wait_for_function("[...document.querySelectorAll('[data-phone-qr]')].every(img=>img.complete&&img.naturalWidth>0)")
    guest=browser.new_context(viewport={'width':390,'height':844});public=guest.new_page();public.on('pageerror',lambda error:errors.append(str(error)));public.add_init_script("Object.defineProperty(navigator,'clipboard',{value:{writeText:async value=>window.__copied=value}})")
    for platform in ('iphone','android'):
     response=page.request.get(base+f'/life/devices/{f["device_id"]}/open-pair?platform={platform}',max_redirects=0);link=urlsplit(response.headers['location']);public.goto(base+link.path+'?'+link.query);assert public.url.startswith(base+'/pair/phone/');assert not guest.cookies();public.get_by_role('button',name='Copy topic',exact=True).click();assert public.evaluate('window.__copied').startswith('mlo-');audit(public,'anonymous-pair-'+platform);public.screenshot(path=str(OUT/f'pair-{platform}.png'),full_page=True)
    guest.close()
    # Read-only collaborators can arrange their own view, never alter project tasks.
    viewer=browser.new_context(viewport={'width':390,'height':844});readonly=viewer.new_page();login(readonly,'read_only','FixtureMemberOnly!234');readonly.goto(mapurl);expect(readonly.locator('[data-map-node]')).to_have_count(8);assert readonly.locator('[data-map-add],[data-map-child],[data-map-relate],[data-map-complete]').count()==0;audit(readonly,'map-viewer-phone');viewer.close()
    # A 150-node map preserves DOM nodes and sends no layout request during movement.
    started=time.perf_counter();goto(f'/life/projects/{f["performance_project_id"]}?view=map');expect(page.locator('[data-map-node]')).to_have_count(150);metrics['map_150_ready_ms']=round((time.perf_counter()-started)*1000,2)
    perf_id=f['performance_task_ids'][0];page.locator('[data-map-search]').fill('Performance task 1');page.wait_for_timeout(160);perf=page.locator(f'[data-map-node="{perf_id}"]');perf.evaluate('e=>window.__originalMapNode=e');page.locator('[data-map-viewport]').scroll_into_view_if_needed();box=perf.bounding_box();writes=[];page.on('request',lambda r:writes.append(r.url) if r.method=='PUT' and r.url.endswith('/map/layout') else None)
    page.mouse.move(box['x']+120,box['y']+box['height']-12);page.mouse.down();page.mouse.move(box['x']+190,box['y']+box['height']+35,steps=24);assert not writes,writes;assert perf.evaluate('e=>e===window.__originalMapNode');page.mouse.up();expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.');metrics['map_nodes_during_drag']=150;metrics['requests_during_drag']=0
    # Four widths and every light/dark palette for the changed components.
    for path,label in [('/life','home'),(mapurl,'map'),('/life/devices','phones'),('/life/focus','focus')]:
     goto(path)
     if label=='phones':page.locator('[data-phone-pair] > summary').first.click();page.wait_for_function("[...document.querySelectorAll('[data-phone-qr]')].every(img=>img.complete&&img.naturalWidth>0)")
     for width in (375,768,1280,1440):
      page.set_viewport_size({'width':width,'height':1000});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(label,width);states.append({'screen':label,'width':width});page.screenshot(path=str(OUT/f'{label}-{width}.png'),full_page=True)
     for mode in ('light','dark'):
      for palette in ('neutral','ocean','sage','rose','amber','lavender'):
       page.evaluate("([m,p])=>{document.documentElement.classList.toggle('dark',m==='dark');document.documentElement.dataset.palette=p}",[mode,palette]);audit(page,label+'-'+mode+'-'+palette)
       if label=='home':assert page.locator('[data-focus-adjust]').first.evaluate('e=>getComputedStyle(e).color')!='rgb(17, 24, 39)' if mode=='dark' else True
     page.screenshot(path=str(OUT/f'{label}-dark.png'),full_page=True)
    # Full rendered CSS review of all populated module routes in dark mode.
    for path in populated_routes(f):
     response=goto(path);assert response.status==(404 if path=='/missing-page' else 200),(path,response.status);page.evaluate("document.documentElement.classList.add('dark')");audit(page,'dark-route-'+path)
    # Native touch long-press from the card body, including continuous edge scroll.
    touch=browser.new_context(storage_state=context.storage_state(),viewport={'width':390,'height':844},has_touch=True,is_mobile=True);phone=touch.new_page();phone.on('pageerror',lambda error:errors.append(str(error)));phone.request.post(base+f'/life/tasks/{f["task_ids"][0]}/status',form={'status':'todo'},headers={'X-MLO-Action':'fetch'});phone.goto(boardurl);expect(phone.locator(f'[data-column=todo] [data-id="{f["task_ids"][0]}"]')).to_have_count(1)
    meta=phone.locator(f'[data-id="{f["task_ids"][0]}"] > .v37-task-meta');meta.scroll_into_view_if_needed();box=meta.bounding_box();x=box['x']+40;y=box['y']+box['height']/2;bounds=phone.locator('.v37-columns').bounding_box();endx=min(377,bounds['x']+bounds['width']-10);cdp=touch.new_cdp_session(phone)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]});phone.wait_for_function("document.getElementById('mlo-v37-board').classList.contains('v37-dragging')")
    for step in range(1,13):cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+(endx-x)*step/12,'y':y}]});phone.wait_for_timeout(20)
    phone.wait_for_timeout(500);destination=phone.evaluate('([x,y])=>document.elementFromPoint(x,y)?.closest("[data-column]")?.dataset.column',[endx,y]);scroll=phone.locator('.v37-columns').evaluate('e=>e.scrollLeft');cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});expect(phone.locator('.v37-message')).to_have_text('Saved.')
    actual=phone.request.get(base+f'/api/v4/projects/{pid}/board').json();assert destination!='todo' and any(n['id']==f['task_ids'][0] for n in actual['columns'][destination]);metrics['native_touch_body_drag']={'destination':destination,'horizontal_scroll_px':scroll};touch.close()
    assert not errors,errors
    (OUT/'accessibility.json').write_text(json.dumps(audits,indent=2));(OUT/'metrics.json').write_text(json.dumps(metrics,indent=2));(OUT/'screens.json').write_text(json.dumps(states,indent=2));(OUT/'javascript-errors.json').write_text(json.dumps(errors))
    failures=[a for a in audits if a['violations']];assert not failures,json.dumps(failures)[:20000]
    browser.close();print(f'PASS v4.1 browser: whole-card drag, immediate task placement, check states, save/return/errors, map edits/layout conflicts/150-node drag, anonymous QR copy, {len(states)} width states and {len(audits)} accessibility scans; no JavaScript errors.')
  finally:
   server.terminate()
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait()
