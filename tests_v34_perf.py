"""Local-only repeatable benchmark; not a Raspberry Pi performance guarantee."""
import os,tempfile,types,sys,statistics,time
from pathlib import Path
class Dummy:
 def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda _:Dummy();sys.modules['app.scheduler']=stub
with tempfile.TemporaryDirectory() as tmp:
 os.environ.update(STUDY_NOTIFIER_DB=str(Path(tmp)/'mlo.db'),SESSION_SECRET='test-secret-performance',COOKIE_SECURE='false',APP_USERNAME='admin',APP_PASSWORD='strong-test-password')
 from fastapi.testclient import TestClient
 from app.main import app
 from app.db import get_conn
 with TestClient(app,follow_redirects=True) as c:
  c.post('/login',data={'username':'admin','password':'strong-test-password'})
  with get_conn() as db:
   uid=db.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
   db.executemany('''INSERT INTO life_tasks(owner_id,title,area,status,priority,created_at,updated_at) VALUES(?,?,?,?,?,?,?)''',[(uid,f'Mock workload {i:05}','Work','todo','high' if i%5==0 else 'normal','2026-10-10','2026-10-10') for i in range(5000)])
   db.commit()
  paths=['/life','/life/tasks?view=open','/life/tasks?view=open&page=90','/life/tasks?q=Mock+workload+04000','/life/insights']
  for path in paths:
   times=[];response=None
   for _ in range(10):
    start=time.perf_counter();response=c.get(path);times.append((time.perf_counter()-start)*1000)
   assert response.status_code==200
   print(f'{path:48} median {statistics.median(times):6.1f} ms, output {len(response.content):7} bytes')
 print('Local benchmark only; run on the Pi to measure production speed.')
