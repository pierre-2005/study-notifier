from scripts.qa_db import closing_connection
"""Representative Study Notifier v1.4 schema upgrade and cold snapshot test."""
import os,sys,tempfile,types,sqlite3
from pathlib import Path
class StubSched:
 def shutdown(self,wait=False):pass
stub=types.ModuleType('app.scheduler');stub.start_scheduler=lambda tz:StubSched();sys.modules['app.scheduler']=stub
temp=tempfile.TemporaryDirectory(); path=Path(temp.name)/'existing.sqlite'
os.environ.update({'STUDY_NOTIFIER_DB':str(path),'APP_USERNAME':'admin','APP_PASSWORD':'safe-password','SESSION_SECRET':'testing-secret-legacy','COOKIE_SECURE':'false'})
from app.db import SCHEMA
with closing_connection(sqlite3.connect(path)) as conn:
 conn.executescript(SCHEMA)
 conn.execute('INSERT INTO courses(name,term,created_at_utc) VALUES(?,?,?)',('Physics 365','Fall 2024','2024-09-01T00:00:00+00:00'))
 conn.execute("INSERT INTO todos(title,created_at_utc,updated_at_utc) VALUES(?,?,?)",('Preserve existing todo','2024-09-01T00:00:00+00:00','2024-09-01T00:00:00+00:00'))
 conn.execute("INSERT INTO expenses(title,category,amount,due_at_utc,created_at_utc,updated_at_utc) VALUES(?,?,?,?,?,?)",('Rent','Home',1200,'2024-10-01T00:00:00+00:00','2024-09-01T00:00:00+00:00','2024-09-01T00:00:00+00:00'))
 conn.commit()
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
 assert client.get('/health').status_code==200
 backup=path.with_name(path.stem+'.pre-mlo-v3.sqlite.backup')
 assert backup.is_file()
 with closing_connection(sqlite3.connect(backup)) as snap:
  assert snap.execute("SELECT title FROM todos").fetchone()[0]=='Preserve existing todo'
 with closing_connection(sqlite3.connect(path)) as live:
  assert live.execute("SELECT name FROM courses").fetchone()[0]=='Physics 365'
  assert live.execute("SELECT title FROM expenses").fetchone()[0]=='Rent'
  assert live.execute("SELECT title FROM todos").fetchone()[0]=='Preserve existing todo'
  assert live.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='life_projects'").fetchone()
  assert live.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='life_devices'").fetchone()
print('PASS: representative old courses, todos, expenses preserved; pre-migration snapshot created; new schema added')
temp.cleanup()
