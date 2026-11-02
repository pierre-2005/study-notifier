"""Acceptance for the expandable Task map workspace, using only a disposable fixture."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'test-results/v42'
OUT.mkdir(parents=True, exist_ok=True)
AXE = Path(os.environ['MLO_AXE_PATH'])
audits, errors, metrics, screens = [], [], {}, []


def audit(page, label):
    page.add_script_tag(path=str(AXE))
    result = page.evaluate("""async () => (await axe.run(document, {
      runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag21aa']}
    })).violations.map(v => ({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))""")
    audits.append({'screen':label, 'violations':result})
    (OUT/'accessibility.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')


def no_overlap(page):
    boxes = page.locator('[data-map-node]:visible').evaluate_all("""els=>els.map(e=>{
      const m=new DOMMatrix(e.style.transform);
      return {id:e.dataset.mapNode,x:m.m41,y:m.m42,w:e.offsetWidth,h:e.offsetHeight};
    })""")
    for i, a in enumerate(boxes):
        for b in boxes[i+1:]:
            assert not (a['x'] < b['x']+b['w'] and b['x'] < a['x']+a['w'] and a['y'] < b['y']+b['h'] and b['y'] < a['y']+a['h']), (a,b)


with tempfile.TemporaryDirectory() as temporary:
    data_dir = Path(temporary) / 'data'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    session = requests.Session()
    session.trust_env = False
    with (OUT/'server.log').open('w') as log:
        server = subprocess.Popen([sys.executable,'-m','scripts.qa_server','--data-dir',str(data_dir),'--port',str(port),'--map-size','150'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise AssertionError((OUT/'server.log').read_text(encoding='utf-8')[-5000:])
                try:
                    if session.get(base+'/health',timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(.1)
            else:
                raise AssertionError('Fixture startup timed out')
            fixture = json.loads((data_dir/'fixture.json').read_text())
            pid, roots = fixture['project_id'], fixture['task_ids']
            map_url = base+f'/life/projects/{pid}?view=map'
            with sync_playwright() as pw:
                options = {'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage']}
                if os.getenv('MLO_BROWSER'):
                    options['executable_path'] = os.environ['MLO_BROWSER']
                browser = pw.chromium.launch(**options)
                context = browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                context.on('page',lambda p:p.on('pageerror',lambda e:errors.append(str(e))))
                page = context.new_page()
                page.set_default_timeout(15000)

                def login(target, username='demo', password='MloPreviewOnly!234'):
                    target.goto(base+'/login')
                    target.locator('[name=username]').fill(username)
                    target.locator('[name=password]').fill(password)
                    target.get_by_role('button',name='Sign in',exact=True).click()
                    target.wait_for_url(base+'/life')

                def saved(target=page):
                    expect(target.locator('[data-map-status]')).to_have_text('Layout saved to your account.')

                login(page)
                api = base+f'/api/v4/projects/{pid}'
                graph = page.request.get(api+'/map').json()
                response = page.request.post(api+'/map/relationships',data=json.dumps({
                    'task_id':roots[2],'parent_id':None,'prerequisites':[roots[1]],
                    'expected_updated_at':next(n for n in graph['nodes'] if n['id']==roots[2])['updated_at']
                }),headers={'Content-Type':'application/json'})
                assert response.ok, response.text()
                map_gets = []
                page.on('request',lambda r:map_gets.append(r.url) if r.method=='GET' and r.url==api+'/map' else None)
                page.goto(map_url)
                expect(page.locator('[data-map-window]')).not_to_be_visible()
                expect(page.locator('[data-map-node]')).to_have_count(0)
                expect(page.locator('[data-map-preview-count]')).to_contain_text('6 tasks')
                assert page.locator('[data-map-expand]').bounding_box()['height'] < 350
                page.screenshot(path=str(OUT/'preview-desktop.png'),full_page=True)
                audit(page,'compact-preview')
                page.locator('[data-map-expand]').focus()
                page.locator('[data-map-expand]').press('Enter')
                expect(page.locator('[data-map-window]')).to_be_visible()
                expect(page.locator('[data-map-node]')).to_have_count(6)
                assert not map_gets, map_gets
                window = page.locator('[data-map-window]').bounding_box()
                assert window['width'] >= 1440*.95 and window['height'] >= 1000*.95, window
                assert page.evaluate("getComputedStyle(document.documentElement).overflow") == 'hidden'
                no_overlap(page)
                style = page.locator('[data-map-node]').first.evaluate("""e=>({
                  width:e.offsetWidth,height:e.offsetHeight,
                  font:parseFloat(getComputedStyle(e.querySelector('.task-map-node-title')).fontSize)
                })""")
                assert style['width'] >= 300 and style['height'] >= 160 and style['font'] >= 16, style
                paths = page.locator('[data-map-edge]').evaluate_all("""els=>els.map(e=>({
                  d:e.getAttribute('d'),stroke:parseFloat(getComputedStyle(e).strokeWidth)
                }))""")
                assert all(p['d'] and 'NaN' not in p['d'] and p['stroke'] >= 2.5 for p in paths), paths
                parent_paths = page.locator(f'[data-map-edge=parent][data-map-from="{roots[0]}"]').evaluate_all("els=>els.map(e=>e.getAttribute('d').split('L')[0])")
                assert len(set(parent_paths)) == 2, parent_paths
                page.screenshot(path=str(OUT/'workspace-desktop.png'))

                # Selection, related wires and nested native dialogs remain inside the workspace flow.
                page.locator('[data-map-search]').fill('Review lecture notes')
                expect(page.locator('[data-map-selected-title]')).to_have_text('Review lecture notes')
                expect(page.locator('[data-map-edge=prerequisite]')).to_be_visible()
                page.locator('[data-map-open]').click()
                expect(page.locator('.task-inspector')).to_be_visible()
                page.keyboard.press('Escape')
                expect(page.locator('.task-inspector')).to_have_count(0)
                expect(page.locator('[data-map-window]')).to_be_visible()
                page.locator('[data-map-open]').click()
                page.locator('.task-inspector [name=title]').fill('Review notes in the map window')
                page.locator('.task-inspector [type=submit]').click()
                expect(page.locator('.task-inspector')).to_have_count(0)
                expect(page.locator('[data-map-selected-title]')).to_have_text('Review notes in the map window')
                expect(page.locator('[data-map-window]')).to_be_visible()
                page.locator('[data-map-search]').fill('')
                page.locator('[data-map-clear]').click()
                expect(page.locator('[data-map-edge=prerequisite]')).not_to_be_visible()
                page.locator('[data-map-connections]').select_option('all')
                expect(page.locator('[data-map-edge=prerequisite]')).to_be_visible()
                page.locator('[data-map-connections]').select_option('prerequisite')
                assert page.locator('[data-map-edge=parent]:visible').count() == 0
                page.locator('[data-map-connections]').select_option('structure')

                # Per-task expand/fold does not delete or write tasks or layout.
                page.locator('[data-map-search]').fill('Finish the circuit')
                expect(page.locator('[data-map-selected-title]')).to_contain_text('Finish the circuit')
                toggle = page.locator(f'[data-map-toggle="{roots[0]}"]')
                toggle.click()
                expect(page.locator('[data-map-node]:visible')).to_have_count(4)
                assert len(page.request.get(api+'/map').json()['nodes']) == 6
                page.locator(f'[data-map-toggle="{roots[0]}"]').click()
                expect(page.locator('[data-map-node]:visible')).to_have_count(6)
                no_overlap(page)

                # Search can find a hidden subtask and unfolds its ancestors automatically.
                page.locator(f'[data-map-toggle="{roots[0]}"]').click()
                page.locator('[data-map-search]').fill('Check calculations')
                expect(page.locator('[data-map-selected-title]')).to_have_text('Check calculations')
                expect(page.locator('[data-map-node]:visible')).to_have_count(6)
                page.locator('[data-map-focus]').click()
                expect(page.locator('[data-map-focus-strip]')).to_be_visible()
                expect(page.locator('[data-map-node]:visible')).to_have_count(2)
                page.locator('[data-map-show-all]').click()
                expect(page.locator('[data-map-node]:visible')).to_have_count(6)
                expect(page.locator('[data-map-search]')).to_have_value('')

                # Moving a card persists, Auto arrange can be undone, and close/reopen preserves the camera.
                page.locator('[data-map-search]').fill('Review notes in')
                expect(page.locator('[data-map-selected-title]')).to_have_text('Review notes in the map window')
                card = page.locator(f'[data-map-node="{roots[1]}"]')
                card.focus()
                card.press('ArrowRight')
                saved()
                before_arrange = page.request.get(api+'/map').json()['positions'][str(roots[1])]
                page.locator('[data-map-arrange]').click()
                saved()
                no_overlap(page)
                expect(page.locator('[data-map-undo]')).to_be_visible()
                page.locator('[data-map-undo]').click()
                saved()
                assert page.request.get(api+'/map').json()['positions'][str(roots[1])] == before_arrange
                before_close = page.locator('[data-map-world]').get_attribute('style')
                page.keyboard.press('Escape')
                expect(page.locator('[data-map-window]')).not_to_be_visible()
                expect(page.locator('[data-map-expand]')).to_be_focused()
                page.locator('[data-map-expand]').click()
                assert page.locator('[data-map-world]').get_attribute('style') == before_close
                page.reload()
                page.locator('[data-map-expand]').click()
                persisted = page.request.get(api+'/map').json()['positions'][str(roots[1])]
                assert persisted == before_arrange

                # Add subtask, validate a forbidden cycle, and search prerequisites without losing choices.
                page.locator('[data-map-search]').fill('Finish the circuit')
                expect(page.locator('[data-map-selected-title]')).to_contain_text('Finish the circuit')
                page.locator('[data-map-child]').click()
                page.locator('.task-map-dialog [name=title]').fill('A clear next step')
                page.locator('.task-map-dialog [type=submit]').click()
                expect(page.locator('.task-map-dialog')).to_have_count(0)
                expect(page.locator('[data-map-selected-title]')).to_have_text('A clear next step')
                graph = page.request.get(api+'/map').json()
                new = next(n for n in graph['nodes'] if n['title']=='A clear next step')
                assert new['parent_id'] == roots[0]
                page.locator('[data-map-search]').fill('Finish the circuit')
                expect(page.locator('[data-map-selected-title]')).to_contain_text('Finish the circuit')
                page.locator('[data-map-relate]').click()
                page.locator('.task-map-dialog [name=parent_id]').select_option(str(new['id']))
                page.locator('.task-map-dialog [type=submit]').click()
                expect(page.locator('.task-map-dialog [role=alert]')).not_to_be_empty()
                expect(page.locator('.task-map-dialog [name=parent_id]')).to_have_value(str(new['id']))
                page.locator('.task-map-dialog [data-cancel]').click()
                page.locator('[data-map-search]').fill('A clear next step')
                expect(page.locator('[data-map-selected-title]')).to_have_text('A clear next step')
                page.locator('[data-map-relate]').click()
                page.locator('[data-prerequisite-search]').fill('Review notes in')
                page.locator(f'.task-map-dialog [name=prerequisite][value="{roots[1]}"]').check()
                page.locator('[data-prerequisite-search]').fill('unrelated search')
                expect(page.locator(f'.task-map-dialog [name=prerequisite][value="{roots[1]}"]')).to_be_visible()
                page.locator('.task-map-dialog [type=submit]').click()
                expect(page.locator('.task-map-dialog')).to_have_count(0)
                assert any(e['from']==roots[1] and e['to']==new['id'] for e in page.request.get(api+'/map').json()['edges'])

                # A failed layout save retains the card position and offers a working retry.
                page.route('**/map/layout',lambda route:route.fulfill(status=503,content_type='application/json',body='{"detail":"Temporary layout failure"}'))
                card = page.locator(f'[data-map-node="{new["id"]}"]')
                card.focus()
                card.press('ArrowDown')
                expect(page.locator('[data-map-status]')).to_have_text('Temporary layout failure')
                expect(page.locator('[data-map-retry]')).to_be_visible()
                page.unroute('**/map/layout')
                page.locator('[data-map-retry]').click()
                saved()

                # Personal viewer layouts remain editable while shared task mutations stay unavailable.
                viewer = browser.new_context(viewport={'width':390,'height':844})
                readonly = viewer.new_page()
                readonly.on('pageerror',lambda e:errors.append(str(e)))
                login(readonly,'read_only','FixtureMemberOnly!234')
                readonly.goto(map_url)
                readonly.locator('[data-map-expand]').click()
                expect(readonly.locator('[data-map-node]')).to_have_count(7)
                assert readonly.locator('[data-map-add],[data-map-child],[data-map-relate],[data-map-complete]').count() == 0
                readonly.locator('[data-map-search]').fill('A clear next step')
                expect(readonly.locator('[data-map-selected-title]')).to_have_text('A clear next step')
                readonly.locator('[data-map-open]').click()
                expect(readonly.locator('.task-inspector [name=title]')).to_be_disabled()
                assert readonly.locator('.task-inspector [type=submit]').count() == 0
                readonly.keyboard.press('Escape')
                audit(readonly,'viewer-phone')
                viewer.close()

                # Changed views across all themes, then six window sizes including a short phone.
                page.set_viewport_size({'width':1440,'height':1000})
                page.locator('[data-map-search]').fill('')
                page.locator('[data-map-clear]').click()
                for palette in ('neutral','ocean','sage','rose','amber','lavender'):
                    for mode in ('light','dark'):
                        page.evaluate("([palette,mode])=>{document.documentElement.dataset.palette=palette;document.documentElement.classList.toggle('dark',mode==='dark')}",[palette,mode])
                        audit(page,'workspace-'+palette+'-'+mode)
                        page.locator('[data-map-close]').click()
                        audit(page,'preview-'+palette+'-'+mode)
                        page.locator('[data-map-expand]').click()
                for width,height in ((375,667),(390,844),(768,1024),(1024,768),(1440,1000),(1920,1080)):
                    page.set_viewport_size({'width':width,'height':height})
                    page.locator('[data-map-search]').fill('A clear next step')
                    expect(page.locator('[data-map-selected-title]')).to_have_text('A clear next step')
                    page.wait_for_timeout(140)
                    geometry = page.evaluate("""()=>{
                      const d=document.querySelector('[data-map-window]'),b=d.getBoundingClientRect(),v=document.querySelector('[data-map-viewport]').getBoundingClientRect();
                      return {x:b.x,right:b.right,y:b.y,bottom:b.bottom,sw:d.scrollWidth,cw:d.clientWidth,vw:v.width,vh:v.height,w:innerWidth,h:innerHeight,page:document.documentElement.scrollWidth};
                    }""")
                    assert geometry['x'] >= -1 and geometry['right'] <= width+1 and geometry['bottom'] <= height+1,geometry
                    assert geometry['sw'] <= geometry['cw']+1 and geometry['page'] <= width+1,geometry
                    assert geometry['vw'] >= 240 and geometry['vh'] >= 140,geometry
                    if width <= 390:
                        panel=page.locator('.map-sidebar').bounding_box()
                        for selector in ('[data-map-child]','[data-map-relate]','[data-map-focus]'):
                            button=page.locator(selector).bounding_box()
                            assert button['y']+button['height']<=panel['y']+panel['height']+1,(selector,panel,button)
                    screens.append(geometry)
                    audit(page,f'selected-{width}')
                    if width==390:
                        page.screenshot(path=str(OUT/'workspace-phone.png'))
                    if width==1440:
                        page.screenshot(path=str(OUT/'selected-desktop.png'))
                page.locator('[data-map-close]').click()
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path=str(OUT/'preview-phone.png'),full_page=True)

                # Large projects start with explorable branches; search reaches a deep hidden task.
                page.set_viewport_size({'width':1440,'height':1000})
                page.goto(base+f'/life/projects/{fixture["performance_project_id"]}?view=map')
                expect(page.locator('[data-map-node]')).to_have_count(0)
                start = time.perf_counter()
                page.locator('[data-map-expand]').click()
                expect(page.locator('[data-map-node]')).to_have_count(150)
                expect(page.locator('[data-map-node]:visible')).to_have_count(4)
                metrics['expand_150_ms'] = round((time.perf_counter()-start)*1000,2)
                no_overlap(page)
                page.screenshot(path=str(OUT/'large-project.png'))
                page.locator('[data-map-search]').fill('Performance task 150')
                expect(page.locator('[data-map-selected-title]')).to_have_text('Performance task 150')
                deep_id = fixture['performance_task_ids'][-1]
                expect(page.locator(f'[data-map-node="{deep_id}"]')).to_be_visible()
                page.locator('[data-map-expand-all]').click()
                expect(page.locator('[data-map-node]:visible')).to_have_count(150)
                page.locator('[data-map-search]').fill('Performance task 1')
                expect(page.locator('[data-map-selected-title]')).to_have_text('Performance task 1')
                perf = page.locator(f'[data-map-node="{fixture["performance_task_ids"][0]}"]')
                perf.evaluate('e=>window.__originalNode=e')
                box = perf.bounding_box()
                writes = []
                page.on('request',lambda r:writes.append(r.url) if r.method=='PUT' and r.url.endswith('/map/layout') else None)
                page.mouse.move(box['x']+130,box['y']+box['height']-10)
                page.mouse.down()
                page.mouse.move(box['x']+180,box['y']+box['height']+25,steps=20)
                assert not writes,writes
                assert perf.evaluate('e=>e===window.__originalNode')
                page.mouse.up()
                saved()
                metrics['drag_dom_preserved'] = True
                metrics['writes_during_drag'] = 0

                # Real two-finger input zooms the phone canvas, without writing task/layout data.
                touch = browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
                phone = touch.new_page()
                phone.on('pageerror',lambda e:errors.append(str(e)))
                login(phone)
                phone.goto(map_url)
                phone.locator('[data-map-expand]').click()
                phone.wait_for_timeout(150)
                before = int(phone.locator('[data-map-scale]').inner_text().strip('%'))
                box = phone.locator('[data-map-viewport]').bounding_box()
                y = box['y']+box['height']*.6
                cdp = touch.new_cdp_session(phone)
                def points(distance):
                    return [{'id':1,'x':195-distance/2,'y':y},{'id':2,'x':195+distance/2,'y':y}]
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points(70)})
                for distance in (80,95,110,125,140):
                    cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':points(distance)})
                    phone.wait_for_timeout(25)
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                after = int(phone.locator('[data-map-scale]').inner_text().strip('%'))
                assert after > before,(before,after)
                metrics['native_pinch_zoom'] = {'before':before,'after':after}
                audit(phone,'native-touch-phone')
                phone.keyboard.press('Escape')
                expect(phone.locator('[data-map-window]')).not_to_be_visible()
                touch.close()
                assert not errors,errors
                assert not [a for a in audits if a['violations']],json.dumps([a for a in audits if a['violations']])[:16000]
                (OUT/'accessibility.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
                (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
                (OUT/'screens.json').write_text(json.dumps(screens,indent=2),encoding='utf-8')
                (OUT/'javascript-errors.json').write_text(json.dumps(errors),encoding='utf-8')
                browser.close()
                print(f'PASS v4.2 workspace: compact/window, keyboard/focus/return, save/retry/undo, branch exploration, connections, viewer permissions, six sizes, native pinch, 150-node drag and {len(audits)} accessibility scans.')
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
