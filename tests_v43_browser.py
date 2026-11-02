"""Regression for false draft warnings and Task map display controls."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'test-results/v43'
OUT.mkdir(parents=True, exist_ok=True)
errors, dialogs, metrics, audits = [], [], {}, []

with tempfile.TemporaryDirectory() as temporary:
    data = Path(temporary) / 'data'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    http = requests.Session(); http.trust_env = False
    with (OUT / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([sys.executable, '-m', 'scripts.qa_server', '--data-dir', str(data), '--port', str(port), '--map-size', '150'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(300):
                if server.poll() is not None: raise AssertionError((OUT/'server.log').read_text(encoding='utf-8')[-3000:])
                try:
                    if http.get(base+'/health', timeout=1).ok: break
                except requests.RequestException: pass
                time.sleep(.1)
            else: raise AssertionError('Fixture startup timed out')
            fixture = json.loads((data/'fixture.json').read_text(encoding='utf-8'))
            pid, tid = fixture['project_id'], fixture['task_ids'][0]
            with sync_playwright() as pw:
                options = {'headless': True, 'args': ['--no-sandbox', '--disable-dev-shm-usage']}
                if os.getenv('MLO_BROWSER'): options['executable_path'] = os.environ['MLO_BROWSER']
                browser = pw.chromium.launch(**options)
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
                page = context.new_page(); page.set_default_timeout(15000)
                page.on('pageerror', lambda e: errors.append(str(e)))
                def handle_dialog(d):
                    dialogs.append(d.type); d.dismiss()
                page.on('dialog', handle_dialog)
                page.goto(base+'/login'); page.locator('[name=username]').fill('demo'); page.locator('[name=password]').fill('MloPreviewOnly!234')
                page.get_by_role('button', name='Sign in', exact=True).click(); page.wait_for_url(base+'/life')
                url = base+f'/life/projects/{pid}'
                page.goto(url+'?view=list')
                page.locator(f'a[href="/life/tasks/{tid}"]').first.click()
                inspector = page.locator('.task-inspector')
                expect(inspector.locator('[name=due_on]')).to_be_visible()
                inspector.locator('[name=due_on]').fill('2026-12-12')
                inspector.get_by_role('button', name='Save changes', exact=True).click()
                expect(inspector).to_have_count(0)
                page.get_by_role('link', name='Due dates', exact=True).click()
                # The old global tracker held the removed inspector form, causing a
                # native beforeunload warning and keeping this navigation on List.
                page.wait_for_timeout(200)
                assert dialogs == [], f'False navigation prompt after saving due date: {dialogs}'
                page.wait_for_url(url+'?view=calendar')
                assert page.request.get(base+f'/api/v4/tasks/{tid}').json()['task']['due_on'] == '2026-12-12'
                page.get_by_role('link', name='Board', exact=True).click(); page.wait_for_url(url+'?view=board')
                print('PASS saved due-date preview navigates to Due dates and Board without false warnings.', flush=True)
                # Dismissed previews must not retain a draft reference either.
                page.goto(url+'?view=list'); page.locator(f'a[href="/life/tasks/{tid}"]').first.click()
                inspector.locator('[name=due_on]').fill('2026-12-13')
                page.keyboard.press('Escape'); expect(inspector).to_have_count(0)
                page.get_by_role('link', name='Due dates', exact=True).click(); page.wait_for_url(url+'?view=calendar')
                assert dialogs == []
                # A real connected task-page draft still protects against loss.
                page.goto(base+f'/life/tasks/{tid}')
                task_form=page.locator(f'form[action="/life/tasks/{tid}/edit"]')
                task_form.locator('[name=due_on]').fill('2026-12-14')
                page.locator('.sidebar-nav a[href="/life/tasks"]').first.click()
                assert dialogs == ['beforeunload']; dialogs.clear()
                task_form.locator('[name=title]').fill('Updated safely')
                task_form.get_by_role('button', name='Save changes', exact=True).click()
                page.wait_for_url(lambda target: f'/life/tasks/{tid}' not in target)
                assert dialogs == []

                api = base+f'/api/v4/projects/{pid}'
                page.goto(url+'?view=map'); page.locator('[data-map-expand]').click()
                filters, direction = page.locator('[data-map-filter]'), page.locator('[data-map-orientation]')
                puts = []
                page.on('request', lambda r: puts.append(r.post_data_json) if r.method=='PUT' and r.url==api+'/map/layout' else None)
                for value, count in [('open',5),('done',1),('todo',3),('doing',1),('blocked',1),('all',6)]:
                    filters.select_option(value); expect(page.locator('[data-map-node]:visible')).to_have_count(count)
                direction.select_option('vertical')
                def locations():
                    return page.locator('[data-map-node]:visible').evaluate_all('els=>Object.fromEntries(els.map(e=>{const m=new DOMMatrix(e.style.transform);return [e.dataset.mapNode,{x:m.m41,y:m.m42,w:e.offsetWidth,h:e.offsetHeight}]}))')
                graph = page.request.get(api+'/map').json()
                for child in [n for n in graph['nodes'] if n['parent_id']]:
                    p = locations(); assert p[str(child['id'])]['y'] >= p[str(child['parent_id'])]['y']+168+50
                assert puts == [], 'Display controls must not rewrite layouts'
                card = page.locator(f'[data-map-node="{tid}"]'); card.focus(); card.press('ArrowDown')
                expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.')
                canonical = page.request.get(api+'/map').json()['positions']
                assert canonical
                direction.select_option('horizontal'); direction.select_option('vertical')
                assert page.request.get(api+'/map').json()['positions'] == canonical
                assert len(puts)==1

                # Native horizontal wheel events, line/page units and Shift-wheel
                # all pan the map, while Ctrl-wheel zooms around the pointer.
                view = page.locator('[data-map-viewport]')
                def camera(): return page.locator('[data-map-world]').evaluate('e=>{const m=new DOMMatrix(getComputedStyle(e).transform);return {x:m.m41,y:m.m42,z:m.a}}')
                def wheel(dx,dy,mode=0,shift=False,ctrl=False):
                    view.evaluate('(e,v)=>e.dispatchEvent(new WheelEvent("wheel",{deltaX:v[0],deltaY:v[1],deltaMode:v[2],shiftKey:v[3],ctrlKey:v[4],bubbles:true,cancelable:true}))',[dx,dy,mode,shift,ctrl])
                for dx,dy,mode,shift,expected in [(120,0,0,False,120),(2,0,1,False,64),(0,90,0,True,90)]:
                    before=camera(); wheel(dx,dy,mode,shift); after=camera()
                    assert abs((before['x']-after['x'])-expected)<.1 and abs(before['y']-after['y'])<.1
                before=camera(); wheel(0,-60,ctrl=True); assert camera()['z']>before['z']
                view.hover(); before=camera(); page.mouse.wheel(140,0); page.wait_for_timeout(100)
                assert camera()['x']<before['x'] and abs(camera()['y']-before['y'])<.1
                wheel(0,1,2); assert camera()['y']<before['y']
                # Undo snapshots survive a direction change without materializing
                # automatic positions as manual saved coordinates.
                page.locator('[data-map-arrange]').click()
                expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.')
                direction.select_option('horizontal'); page.locator('[data-map-undo]').click()
                expect(page.locator('[data-map-status]')).to_have_text('Layout saved to your account.')
                restored = page.request.get(api+'/map').json()['positions']
                assert restored == canonical, (canonical,restored)

                # A completed child remains findable under an open parent.
                child = next(n for n in graph['nodes'] if n['parent_id']==tid)
                response=page.request.post(api+'/move',data=json.dumps({'task_id':child['id'],'status':'done','expected_updated_at':child['updated_at']}),headers={'Content-Type':'application/json'})
                assert response.ok, response.text()
                page.locator('[data-map-close]').click(); page.reload(); page.locator('[data-map-expand]').click()
                filters.select_option('done')
                expect(page.locator('[data-map-node]:visible')).to_have_count(3)
                expect(page.locator('.is-filter-context:visible')).to_have_count(1)
                expect(page.locator('[data-map-shown]')).to_contain_text('2 matching')
                compact=list(locations().values())
                assert max(p['y'] for p in compact)-min(p['y'] for p in compact)<900, 'Hidden root branches reserved empty layout space'
                page.locator('[data-map-search]').fill('nothing matches this query')
                expect(page.locator('[data-map-no-results]')).to_be_visible()
                page.locator('[data-map-search]').fill('')
                direction.select_option('vertical'); page.reload(); page.locator('[data-map-expand]').click()
                expect(filters).to_have_value('done'); expect(direction).to_have_value('vertical')
                expect(page.locator('[data-map-node]:visible')).to_have_count(3)
                page.screenshot(path=str(OUT/'vertical-completed.png'))

                def audit(label):
                    page.add_script_tag(path=os.environ['MLO_AXE_PATH'])
                    result=page.evaluate('async()=> (await axe.run(document,{runOnly:{type:"tag",values:["wcag2a","wcag2aa","wcag21aa"]}})).violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))')
                    audits.append({'screen':label,'violations':result}); assert not result,result
                audit('vertical-completed-desktop')
                page.evaluate('document.documentElement.classList.add("dark")'); audit('vertical-dark')
                for width,height in [(375,667),(390,844),(768,1024),(1440,1000)]:
                    page.set_viewport_size({'width':width,'height':height}); page.wait_for_timeout(120)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    for selector in ['[data-map-close]','[data-map-filter]','[data-map-orientation]','[data-map-zoom="1"]']:
                        box=page.locator(selector).bounding_box(); assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1,(selector,box,width,height)
                    assert view.bounding_box()['height']>=190
                    audit(f'vertical-{width}x{height}')
                    if width==375: page.screenshot(path=str(OUT/'vertical-phone.png'))
                page.evaluate('document.documentElement.classList.remove("dark")')
                # Preferences stay isolated by project. Filtering the folded large
                # tree reveals matching descendants and their ancestor context.
                page.locator('[data-map-close]').click()
                performance_url=base+f'/life/projects/{fixture["performance_project_id"]}?view=map'
                page.goto(performance_url); page.locator('[data-map-expand]').click()
                expect(filters).to_have_value('all'); expect(direction).to_have_value('horizontal')
                start=time.perf_counter(); filters.select_option('open'); direction.select_option('vertical')
                page.wait_for_timeout(100); metrics['150_task_filter_and_orientation_ms']=round((time.perf_counter()-start)*1000,2)
                assert page.locator('[data-map-node]:visible').count()>100
                positions=locations(); items=list(positions.values())
                for i,a in enumerate(items):
                    for b in items[i+1:]:
                        assert not (a['x']<b['x']+b['w'] and b['x']<a['x']+a['w'] and a['y']<b['y']+b['h'] and b['y']<a['y']+a['h'])
                assert page.locator('[data-map-lines]').evaluate('e=>!e.innerHTML.includes("NaN")')
                audit('150-task-vertical-open'); page.screenshot(path=str(OUT/'vertical-150-tasks.png'))
                assert not errors,errors
                assert dialogs==[],dialogs
                (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
                (OUT/'accessibility.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
                (OUT/'javascript-errors.json').write_text(json.dumps(errors),encoding='utf-8')
                print('PASS map status/context filters, orientations, saved-layout/Undo compatibility, wheel axes/units/zoom, preferences, 150 tasks, four sizes and accessibility.',flush=True)
                browser.close()
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait()
