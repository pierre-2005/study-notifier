"""Real HTTP browser acceptance against a disposable database and disabled integrations."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import requests
from playwright.sync_api import sync_playwright,expect

root=Path(__file__).resolve().parent
output=Path(os.getenv('MLO_QA_OUTPUT',str(root/'docs/preview/v37')));output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    data=Path(temporary)/'data'
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    session=requests.Session();session.trust_env=False
    with (Path(temporary)/'server.log').open('w') as log:
        server=subprocess.Popen([sys.executable,'-m','scripts.qa_server','--data-dir',str(data),'--port',str(port)],cwd=root,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(200):
                if server.poll() is not None:raise AssertionError('Browser fixture exited before startup.')
                try:
                    if session.get(base+'/health',timeout=1).status_code==200:break
                except requests.RequestException:pass
                time.sleep(.05)
            else:raise AssertionError('Browser fixture startup timed out.')
            fixture=json.loads((data/'fixture.json').read_text());pid=fixture['project_id'];first=fixture['task_ids'][0]
            with sync_playwright() as pw:
                options={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
                if os.getenv('MLO_BROWSER'):options['executable_path']=os.environ['MLO_BROWSER']
                browser=pw.chromium.launch(**options)
                context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                axe_path=os.getenv('MLO_AXE_PATH');audits=[]
                def audit(target,label):
                    if not axe_path:return
                    target.add_script_tag(path=axe_path)
                    result=target.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));}")
                    audits.append({'screen':label,'violations':result})
                errors=[];context.on('page',lambda p:p.on('pageerror',lambda error:errors.append(str(error))))
                page=context.new_page();page.set_default_timeout(10000)
                page.goto(base+'/login');page.locator('[name=username]').fill('demo');page.locator('[name=password]').fill('MloPreviewOnly!234')
                page.get_by_role('button',name='Sign in',exact=True).click();page.wait_for_url(base+'/life')
                page.screenshot(path=str(output/'today-desktop.png'),full_page=True)
                page.goto(base+f'/life/projects/{pid}?view=board');expect(page.locator('.v37-ticket')).to_have_count(4)
                page.screenshot(path=str(output/'board-desktop.png'),full_page=True)
                audit(page,'board-desktop')
                for mode in ('light','dark'):
                    for palette in ('neutral','ocean','sage','rose','amber','lavender'):
                        page.evaluate("([mode,palette])=>{document.documentElement.classList.toggle('dark',mode==='dark');document.documentElement.dataset.palette=palette}",[mode,palette])
                        audit(page,f'board-{mode}-{palette}')
                        if mode=='dark' and palette=='ocean':page.screenshot(path=str(output/'board-dark.png'),full_page=True)
                page.evaluate("document.documentElement.classList.remove('dark');document.documentElement.dataset.palette='ocean'")
                # Drag handles change real status, and keyboard controls remain available.
                page.locator(f'[data-handle="{first}"]').drag_to(page.locator('[data-column=doing] .v37-drop'))
                expect(page.locator(f'[data-column=doing] [data-id="{first}"]')).to_have_count(1)
                page.locator(f'[data-id="{first}"] > .v37-card-head .v37-task-title').click()
                expect(page.locator('.task-inspector')).to_be_visible()
                audit(page,'task-inspector')
                page.locator('.task-inspector [name=title]').fill('Finish the circuit design report, reviewed')
                page.locator('.task-inspector [type=submit]').click();expect(page.locator('[data-inspector-status]')).to_have_text('Saved.')
                assert page.locator('.task-inspector [type=submit]').evaluate('e=>e===document.activeElement')
                page.keyboard.press('Escape');expect(page.locator('.task-inspector')).to_have_count(0)
                expect(page.locator(f'[data-id="{first}"] > .v37-card-head .v37-task-title')).to_contain_text('reviewed')
                page.locator(f'[data-id="{first}"] > .v37-card-head .v37-task-actions > summary').click()
                menu=page.locator(f'[data-id="{first}"] > .v37-card-head .v37-task-actions .v37-action-menu')
                expect(menu).to_be_visible();box=menu.bounding_box();assert 0<=box['x'] and box['x']+box['width']<=1440
                menu.get_by_role('button',name='Add subtask',exact=True).click()
                page.locator('.v37-parent-dialog [name=title]').fill('Check source citations')
                page.locator('.v37-parent-dialog [type=submit]').click();expect(page.locator('.v37-parent-dialog')).to_have_count(0)
                expect(page.get_by_role('link',name='Check source citations',exact=True)).to_be_visible()
                child=page.locator('.v37-child-task').filter(has=page.get_by_role('link',name='Check source citations',exact=True))
                child.locator('.v37-task-actions > summary').click();child.locator('select[data-status-task]').select_option('done')
                expect(page.locator('.v37-message')).to_have_text('Saved.')
                # A second root can be nested with an explicit parent selection.
                second=fixture['task_ids'][1]
                page.locator(f'[data-id="{second}"] > .v37-card-head .v37-task-actions > summary').click()
                page.locator(f'[data-parent="{second}"]').click();page.locator('.v37-parent-dialog select').select_option(str(first))
                page.locator('.v37-parent-dialog [type=submit]').click();expect(page.locator('.v37-ticket')).to_have_count(3)
                # Every main route uses the actual stylesheet and JS bundle.
                routes=['/life','/life/tasks','/life/projects','/life/notes','/life/calendar','/life/focus','/life/goals',
                        '/life/insights','/life/study','/life/study/planner','/life/study/import','/life/work','/finance','/life/calendars','/life/devices','/settings','/admin/users']
                for width in (375,768,1280,1440):
                    page.set_viewport_size({'width':width,'height':1000})
                    for path in routes:
                        response=page.goto(base+path);assert response.status==200,(path,response.status)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,path)
                        if width==1440:audit(page,path)
                # Fresh touch context: closed navigation is absent from the tab order.
                mobile=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,
                    storage_state=context.storage_state(),reduced_motion='reduce')
                phone=mobile.new_page();phone.on('pageerror',lambda error:errors.append(str(error)))
                phone.goto(base+f'/life/projects/{pid}?view=board');expect(phone.locator('.v37-ticket')).to_have_count(3)
                phone.wait_for_function('document.querySelector(".app-sidebar").getBoundingClientRect().right<=1')
                assert phone.locator('.app-sidebar').evaluate('e=>e.inert')
                phone.get_by_role('button',name='Open navigation',exact=True).click();expect(phone.locator('.app-sidebar')).to_have_attribute('aria-modal','true')
                phone.keyboard.press('Escape');assert phone.get_by_role('button',name='Open navigation',exact=True).evaluate('e=>e===document.activeElement')
                phone.get_by_role('button',name='In progress',exact=False).first.click()
                phone.wait_for_function("Math.abs(document.querySelector('[data-column=doing]').getBoundingClientRect().left-document.querySelector('.v37-columns').getBoundingClientRect().left)<5")
                handle=phone.locator(f'[data-handle="{first}"]')
                handle.evaluate("e=>e.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'})")
                start=handle.bounding_box();target=phone.locator('[data-column=blocked]').bounding_box()
                columns=phone.locator('.v37-columns').bounding_box()
                end_x=columns['x']+columns['width']-12;end_y=start['y']+start['height']/2
                cdp=mobile.new_cdp_session(phone)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':start['x']+start['width']/2,'y':end_y}]})
                for step in range(1,7):
                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':start['x']+start['width']/2+(end_x-start['x']-start['width']/2)*step/6,'y':end_y}]})
                phone.wait_for_function("(x)=>document.querySelector('[data-column=blocked]').getBoundingClientRect().left<x-35",arg=end_x,timeout=5000)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                expect(phone.locator(f'[data-column=blocked] [data-id="{first}"]')).to_have_count(1)
                phone.get_by_role('button',name='Blocked',exact=False).first.click()
                phone.wait_for_function("Math.abs(document.querySelector('[data-column=blocked]').getBoundingClientRect().left-document.querySelector('.v37-columns').getBoundingClientRect().left)<5")
                phone.screenshot(path=str(output/'board-mobile.png'))
                audit(phone,'board-mobile')
                # Local course extraction, source review and one canonical task per assessment.
                page.set_viewport_size({'width':1440,'height':1000});page.goto(base+'/life/study/import')
                page.locator('[name=file]').set_input_files({'name':'outline.txt','mimeType':'text/plain','buffer':b'ENEL 471 Communications\nAssignment 1 | November 12, 2026 23:59 | 20%\nFinal exam TBA | 80%'})
                page.locator('[data-upload-submit]').click();page.wait_for_url('**/life/study/import/*')
                page.locator('[name=course_name]').fill('Communications');page.locator('[name=term]').fill('Fall 2026')
                expect(page.locator('[data-row]')).to_have_count(2)
                page.screenshot(path=str(output/'outline-review-desktop.png'),full_page=True)
                audit(page,'outline-review')
                page.get_by_role('button',name='Add selected assessments',exact=True).click();page.wait_for_url('**/life/study/courses/*')
                expect(page.get_by_role('heading',name='Communications',exact=True)).to_be_visible()
                # A real calendar plan can be previewed, applied, undone and pinned.
                page.goto(base+'/life/study');expect(page.locator('a.mlo-area-row').filter(has=page.get_by_text('Communications',exact=True))).to_be_visible()
                page.screenshot(path=str(output/'study-desktop.png'),full_page=True)
                page.goto(base+'/life/study/planner')
                page.get_by_role('button',name='Preview plan',exact=True).click()
                expect(page.locator('[data-plan-output]')).to_be_visible()
                assert page.locator('.planner-proposal').count()>0
                expect(page.get_by_role('button',name='Apply to my calendar',exact=True)).to_be_enabled()
                page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/'planner-preview-desktop.png'),full_page=True)
                for mode in ('light','dark'):
                    for palette in ('neutral','ocean','sage','rose','amber','lavender'):
                        page.evaluate("([mode,palette])=>{document.documentElement.classList.toggle('dark',mode==='dark');document.documentElement.dataset.palette=palette}",[mode,palette])
                        audit(page,f'planner-{mode}-{palette}')
                page.evaluate("document.documentElement.classList.remove('dark');document.documentElement.dataset.palette='ocean'")
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert page.locator('[data-window-field=start]').first.bounding_box()['width']>=130
                assert abs(page.locator('[data-window-field=start]').first.bounding_box()['width']-page.locator('[data-window-field=end]').first.bounding_box()['width'])<1
                page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/'planner-mobile.png'));audit(page,'planner-mobile')
                page.locator('[data-planner-preferences]').scroll_into_view_if_needed();page.screenshot(path=str(output/'planner-availability-mobile.png'))
                page.get_by_role('button',name='Apply to my calendar',exact=True).click()
                expect(page.locator('.planner-session')).not_to_have_count(0)
                page.get_by_role('button',name='Undo last plan',exact=True).click();expect(page.locator('.planner-session')).to_have_count(0)
                page.get_by_role('button',name='Preview plan',exact=True).click();expect(page.locator('[data-plan-output]')).to_be_visible()
                page.get_by_role('button',name='Apply to my calendar',exact=True).click();expect(page.locator('.planner-session')).not_to_have_count(0)
                page.locator('[data-plan-pin]').first.click();expect(page.locator('[data-plan-pin][aria-pressed=true]')).to_have_count(1)
                page.get_by_role('button',name='Clear future plan',exact=True).click();expect(page.locator('.planner-session')).to_have_count(1)
                page.set_viewport_size({'width':1440,'height':1000})
                # Profile wizard preserves explicit mute rules through reload.
                page.goto(base+'/life/onboarding');expect(page.locator('#v37-next')).to_be_enabled()
                for _ in range(4):page.locator('#v37-next').click()
                expect(page.locator('#v37-preview')).to_be_visible();page.locator('[name=palette]').select_option('sage')
                page.locator('[name=theme]').select_option('dark');page.screenshot(path=str(output/'appearance-preview.png'),full_page=True)
                page.locator('#v37-next').click();page.wait_for_url('**/settings?notice=*')
                # Public signup validates and retains the entered non-secret fields.
                visitor=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
                visitor.goto(base+'/signup');audit(visitor,'signup-mobile');visitor.locator('[name=display_name]').fill('Test Member');visitor.locator('[name=username]').fill('browser_member')
                visitor.locator('[name=email]').fill('browser@example.com');visitor.locator('[name=password]').fill('BrowserPassword!123');visitor.locator('[name=password_confirm]').fill('BrowserPassword!123')
                for _ in range(4):visitor.locator('#v37-next').click()
                visitor.locator('#v37-next').click();expect(visitor.get_by_role('heading',name='Account created',exact=True)).to_be_visible()
                assert not errors,errors
                if audits:
                    (output/'accessibility.json').write_text(json.dumps(audits,indent=2)+'\n')
                    failures=[a for a in audits if a['violations']]
                    assert not failures,[(a['screen'],[(v['id'],len(v['nodes'])) for v in a['violations']]) for a in failures]
                browser.close()
                print('PASS v3.7 browser: real drag, nested edits, inspector, 17 routes x 4 widths, planner preview/apply/undo/pin/clear, mobile navigation, local course import, appearance and signup; no JS errors')
        finally:
            server.terminate();server.wait(timeout=10)
