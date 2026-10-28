"""Populated v4 browser acceptance and accessibility, using a disposable HTTP server."""
import json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright,expect,Error as BrowserError
ROOT=Path(__file__).resolve().parent
OUT=Path(os.getenv('MLO_V4_QA_OUTPUT',str(ROOT/'test-results/v4')));OUT.mkdir(parents=True,exist_ok=True)
axe=Path(os.environ['MLO_AXE_PATH']);assert axe.is_file(),'Accessibility engine is required.'

def navigate(target,url):
 # Windows may suspend an idle headless browser's network service. Retry only
 # that transport error; HTTP failures and application errors still fail once.
 for attempt in range(3):
  try:return target.goto(url)
  except BrowserError as exc:
   if 'ERR_NETWORK_IO_SUSPENDED' not in str(exc) or attempt==2:raise
   time.sleep(.3)

with tempfile.TemporaryDirectory() as temporary:
 data=Path(temporary)/'data'
 with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
 base=f'http://127.0.0.1:{port}';session=requests.Session();session.trust_env=False
 with (OUT/'server.log').open('w') as log:
  server=subprocess.Popen([sys.executable,'-m','scripts.qa_server','--data-dir',str(data),'--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  try:
   for _ in range(300):
    if server.poll() is not None:raise AssertionError('Fixture startup failed: '+(OUT/'server.log').read_text()[-3000:])
    try:
     if session.get(base+'/health',timeout=1).status_code==200:break
    except requests.RequestException:pass
    time.sleep(.1)
   else:raise AssertionError('Fixture startup timed out.')
   f=json.loads((data/'fixture.json').read_text());routes=['/life','/life/tasks','/life/projects',f'/life/projects/{f["project_id"]}?view=board',f'/life/tasks/{f["task_ids"][0]}','/life/notes',f'/life/notes/{f["note_id"]}','/life/calendar','/life/calendar?month=2026-11&view=agenda','/life/focus','/life/goals','/life/insights','/life/study','/life/study/planner','/life/study/import','/life/work','/finance','/finance/transactions','/finance/transactions/1','/finance/budget','/finance/monthly','/finance/rules','/finance/import','/expenses','/expenses/new',f'/expenses/{f["expense_id"]}','/courses','/courses/new',f'/courses/{f["course_id"]}','/items','/items/new',f'/items/{f["item_id"]}','/classes','/classes/new',f'/classes/{f["class_id"]}/edit','/jobs','/jobs/new',f'/jobs/{f["job_id"]}','/events',f'/events/{f["event_id"]}','/life/spaces','/sections/new',f'/sections/{f["space_id"]}',f'/sections/{f["space_id"]}?view=settings',*[f'/sections/{f["grocery_id"]}?view={v}' for v in ['list','recipes','prices','settings']],'/life/calendars','/life/calendars/new','/life/devices',f'/life/devices/{f["device_id"]}/pair-iphone','/settings','/account/security','/account/password','/admin/users','/life/import','/life/search','/missing-page']
   audits=[];screens=[];errors=[]
   with sync_playwright() as pw:
    options={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
    if os.getenv('MLO_BROWSER'):options['executable_path']=os.environ['MLO_BROWSER']
    browser=pw.chromium.launch(**options);context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    context.on('page',lambda target:target.on('pageerror',lambda error:errors.append(str(error))))
    page=context.new_page();page.on('dialog',lambda d:d.accept());page.set_default_timeout(15000)
    def audit(target,label):
     target.add_script_tag(path=str(axe))
     violations=target.evaluate("async()=> (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))")
     audits.append({'screen':label,'violations':violations})
    navigate(page,base+'/login');page.locator('[name=username]').fill('demo');page.locator('[name=password]').fill('MloPreviewOnly!234');page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url(base+'/life')
    for width in (375,768,1280,1440):
     page.set_viewport_size({'width':width,'height':1000})
     for index,path in enumerate(routes):
      response=navigate(page,base+path);assert response.status==(404 if path=='/missing-page' else 200),(path,response.status)
      page.wait_for_timeout(30)
      assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,path)
      screens.append({'path':path,'width':width,'status':response.status})
      if width in (375,1440):page.screenshot(path=str(OUT/f'screen-{index:02d}-{width}.png'),full_page=True)
      if width==1440:audit(page,path)
    # Actual SQL paging retains filters and contains only the current 50 rows.
    navigate(page,base+'/finance/transactions');expect(page.locator('.transaction-row')).to_have_count(50);page.get_by_role('link',name='Next',exact=True).click();expect(page.locator('.transaction-row')).to_have_count(22)
    page.locator('[name=q]').fill('Weekly groceries');page.get_by_role('button',name='Filter',exact=True).click();expect(page.locator('.transaction-row')).to_have_count(18)
    # Budget uses one draft through steps, category creation, movement and retries.
    navigate(page,base+'/finance/budget');salary=page.locator('[data-budget-row]').filter(has=page.locator('[data-category-name]',has_text='Employment income')).first
    salary.locator('[data-budget-amount]').fill('2600')
    page.locator('[data-budget-next]').click();page.locator('[data-budget-back]').click();expect(salary.locator('[data-budget-amount]')).to_have_value('2600')
    page.locator('[data-budget-next]').click();page.locator('[data-budget-add=essentials]').click();page.locator('[data-budget-search]').fill('Workshop supplies');page.locator('[data-budget-create]').click()
    custom=page.locator('[data-budget-row]').filter(has=page.locator('[data-category-name]',has_text='Workshop supplies'))
    custom.locator('[data-budget-amount]').fill('42.555');custom.locator('[data-budget-frequency]').select_option('Weekly');custom.locator('[data-budget-move]').click();expect(page.locator('[data-budget-panel=flexible]')).to_be_visible()
    page.locator('[data-budget-step=review]').click();expect(page.locator('[data-budget-review]')).to_contain_text('Workshop supplies');audit(page,'budget-review')
    page.route('**/finance/budget/save',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Temporary test failure. Retry your save.'})))
    page.locator('[data-budget-save]').click();expect(page.locator('[data-budget-feedback]')).to_contain_text('Temporary test failure');expect(custom.locator('[data-budget-amount]')).to_have_value('42.555');page.screenshot(path=str(OUT/'budget-save-failure.png'),full_page=True)
    page.unroute('**/finance/budget/save');page.locator('[data-budget-save]').click();expect(page.locator('[data-budget-feedback]')).to_have_text('Budget saved.')
    page.reload();page.locator('[data-budget-quick]').click();expect(page.locator('[data-category-name]').filter(has_text='Workshop supplies')).to_be_visible()
    # Both existing and new categories can be removed and restored without losing frequencies.
    custom=page.locator('[data-budget-row]').filter(has=page.locator('[data-category-name]',has_text='Workshop supplies'));expect(custom.locator('[data-budget-frequency]')).to_have_value('Weekly')
    custom.locator('[data-budget-remove]').click();expect(custom).to_be_hidden();page.locator('[data-budget-add=flexible]').click();page.locator('[data-budget-search]').fill('Workshop');page.get_by_role('button',name='Workshop supplies',exact=True).click();expect(custom).to_be_visible()
    page.locator('[data-budget-save]').click();expect(page.locator('[data-budget-feedback]')).to_have_text('Budget saved.')
    stale=context.new_page();stale.on('dialog',lambda d:d.accept());navigate(stale,base+'/finance/budget');stale.locator('[data-budget-quick]').click();stale.locator('[data-budget-amount]').first.fill('999')
    salary.locator('[data-budget-amount]').fill('2800');page.locator('[data-budget-save]').click();expect(page.locator('[data-budget-feedback]')).to_have_text('Budget saved.')
    stale.locator('[data-budget-save]').click();expect(stale.locator('[data-budget-feedback]')).to_contain_text('newer budget');expect(stale.locator('[data-budget-amount]').first).to_have_value('999');stale.close()
    for mode in ('light','dark'):
     for palette in ('neutral','ocean','sage','rose','amber','lavender'):
      page.evaluate("([m,p])=>{document.documentElement.classList.toggle('dark',m==='dark');document.documentElement.dataset.palette=p}",[mode,palette]);audit(page,'budget-'+mode+'-'+palette)
    page.screenshot(path=str(OUT/'budget-dark.png'),full_page=True)
    # Narrow staged forms, dialog focus, keyboard and native selects remain reachable.
    page.set_viewport_size({'width':375,'height':844});page.reload();page.locator('[data-budget-next]').click();page.locator('[data-budget-add=essentials]').click();expect(page.locator('[data-budget-dialog]')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('[data-budget-dialog]')).not_to_be_visible();assert page.locator('[data-budget-add=essentials]').evaluate('e=>e===document.activeElement')
    audit(page,'budget-phone-essentials');page.screenshot(path=str(OUT/'budget-mobile.png'),full_page=True)
    # Markdown never trusts raw HTML or dangerous links. Typing during saves stays unsaved.
    page.set_viewport_size({'width':1440,'height':1000});navigate(page,base+f'/life/notes/{f["note_id"]}')
    body=page.locator('[data-note-editor] [name=body]');body.fill('## Design review\n**Check calculations**\n<script>window.noteXss=1</script>\n[bad](javascript:alert(1))\n[good](https://example.com)\n```\n<img src=x onerror=alert(1)>\n```')
    page.locator('[data-note-view=preview]').click();expect(page.locator('[data-note-preview] strong')).to_have_text('Check calculations');assert page.evaluate('window.noteXss===undefined');assert page.locator('[data-note-preview] a').count()==1;assert page.locator('[data-note-preview] script, [data-note-preview] img').count()==0
    page.locator('[data-note-view=split]').click();audit(page,'note-split')
    page.evaluate("window.__realFetch=window.fetch;window.fetch=(...a)=>window.__realFetch(...a).then(r=>new Promise(resolve=>setTimeout(()=>resolve(r),500)))")
    page.locator('[data-note-editor] [type=submit]').click();body.fill('A later draft typed while the previous save was pending.');expect(page.locator('[data-note-status]')).to_contain_text('Newer changes are unsaved');expect(body).to_have_value('A later draft typed while the previous save was pending.')
    page.evaluate('window.fetch=window.__realFetch');page.locator('[data-note-editor] [type=submit]').click();expect(page.locator('[data-note-status]')).to_have_text('Saved')
    other=context.new_page();other.on('dialog',lambda d:d.accept());navigate(other,base+f'/life/notes/{f["note_id"]}');other.locator('[name=body]').fill('Other tab saved');other.locator('[data-note-editor] [type=submit]').click();expect(other.locator('[data-note-status]')).to_have_text('Saved');other.close()
    body.fill('Keep this conflicting draft');page.locator('[data-note-editor] [type=submit]').click();expect(page.locator('[data-note-status]')).to_contain_text('another tab');expect(body).to_have_value('Keep this conflicting draft')
    for mode in ('light','dark'):
     for palette in ('neutral','ocean','sage','rose','amber','lavender'):
      page.evaluate("([m,p])=>{document.documentElement.classList.toggle('dark',m==='dark');document.documentElement.dataset.palette=p}",[mode,palette]);audit(page,'note-'+mode+'-'+palette)
    # JavaScript-disabled Budget displays real saved summaries and retains invalid submissions.
    nojs=browser.new_context(java_script_enabled=False,storage_state=context.storage_state(),viewport={'width':390,'height':844});plain=nojs.new_page();navigate(plain,base+'/finance/budget')
    assert plain.locator('[data-budget-panel]:visible').count()==5;assert '$0.00'!=plain.locator('[data-budget-total=income]').inner_text();plain.locator('[data-budget-amount]').first.fill('NaN');plain.locator('[data-budget-save]').click();expect(plain.locator('[data-budget-feedback]')).to_contain_text('valid amount');expect(plain.locator('[data-budget-amount]').first).to_have_value('NaN');nojs.close()
    expired=browser.new_context(storage_state=context.storage_state());expired_page=expired.new_page();expired_page.on('dialog',lambda d:d.accept());navigate(expired_page,base+'/finance/budget');expired_page.locator('[data-budget-quick]').click();expired_page.locator('[data-budget-amount]').first.fill('321');expired.clear_cookies();expired_page.locator('[data-budget-save]').click();expect(expired_page.locator('[data-budget-feedback]')).to_contain_text('session expired');expect(expired_page.locator('[data-budget-amount]').first).to_have_value('321');expired.close()
    viewer=browser.new_context(viewport={'width':390,'height':844});readonly=viewer.new_page();readonly.on('pageerror',lambda error:errors.append(str(error)))
    navigate(readonly,base+'/login');readonly.locator('[name=username]').fill('read_only');readonly.locator('[name=password]').fill('FixtureMemberOnly!234');readonly.get_by_role('button',name='Sign in',exact=True).click();readonly.wait_for_url(base+'/life')
    navigate(readonly,base+f'/life/projects/{f["project_id"]}?view=board');expect(readonly.locator('.v37-ticket')).to_have_count(4);assert readonly.locator('[data-status-task]').count()==0;audit(readonly,'shared-project-viewer')
    navigate(readonly,base+f'/life/notes/{f["shared_note_id"]}');expect(readonly.locator('[data-note-reader] strong')).to_have_text('safe formatting');assert readonly.locator('[data-note-editor],form[action$="/delete"]').count()==0;audit(readonly,'shared-note-viewer');viewer.close()
    # Public/authentication surfaces receive the same rendered-state audit.
    guest=browser.new_context(viewport={'width':390,'height':844});guest.on('page',lambda target:target.on('pageerror',lambda error:errors.append(str(error))));public=guest.new_page()
    for path in ('/','/privacy','/termsofservice','/login','/signup','/forgot-password','/reset-code','/verify-email/resend','/missing-public'):
     response=navigate(public,base+path);assert response.status in (200,404);assert public.evaluate('document.documentElement.scrollWidth<=innerWidth+1');audit(public,'public-'+path)
    guest.close()
    pwa=browser.new_context();installed=pwa.new_page();local='http://localhost:'+str(port)
    navigate(installed,local+'/health');installed.evaluate("async()=>{await caches.open('mlo-static-v3.7.1');await caches.open('unrelated-owner-cache')}")
    navigate(installed,local+'/');installed.evaluate('async()=>await navigator.serviceWorker.ready')
    installed.reload();installed.wait_for_function('navigator.serviceWorker.controller!==null')
    installed.evaluate("async()=>{await fetch('/login');await fetch('/life');await fetch('/api/v4/projects/1/board');}")
    keys=installed.evaluate('async()=>await caches.keys()');assert 'unrelated-owner-cache' in keys and 'mlo-static-v3.7.1' not in keys,keys
    cached=installed.evaluate("async()=>{const c=await caches.open('mlo-static-v4.0.0');return (await c.keys()).map(r=>new URL(r.url).pathname)}")
    assert cached and all(path.startswith('/static/') for path in cached),cached
    assert installed.request.get(local+'/static/theme.js?v=3.7.1').status==200
    pwa.close();context.close();browser.close()
   (OUT/'screens.json').write_text(json.dumps(screens,indent=2));(OUT/'accessibility.json').write_text(json.dumps(audits,indent=2));(OUT/'javascript-errors.json').write_text(json.dumps(errors))
   failures=[a for a in audits if a['violations']];assert not failures,json.dumps(failures)[:16000];assert not errors,errors
   print(f'PASS v4 browser: {len(screens)} populated route/width states, {len(audits)} accessibility scans, staged/quick/no-JS Budget, custom categories/frequencies/move/removal, failed saves/conflicts, safe note previews/concurrent typing, pagination and public/auth screens.')
  finally:
   server.terminate()
   try:server.wait(timeout=10)
   except subprocess.TimeoutExpired:server.kill();server.wait()
