"""Compile all application templates/Python and syntax-check current JavaScript."""
import ast,json,shutil,subprocess
from pathlib import Path
from app.ui import templates
from app.meta import APP_VERSION
ROOT=Path(__file__).resolve().parents[1]
def main():
 python=list((ROOT/'app').rglob('*.py'))+list((ROOT/'scripts').glob('*.py'))
 for path in python:ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path))
 names=templates.env.list_templates()
 for name in names:templates.env.get_template(name)
 node=shutil.which('node');assert node,'Node.js is required for JavaScript syntax checks.'
 javascript=list((ROOT/'app/static').glob('*.js'))
 for path in javascript:subprocess.run([node,'--check',str(path)],check=True,capture_output=True)
 worker=(ROOT/'app/static/sw.js').read_text(encoding='utf-8-sig');assert 'mlo-static-v'+APP_VERSION in worker
 assets=json.loads(worker.split('const ASSETS=',1)[1].split(';',1)[0].replace("'",'"'))
 for asset in assets:assert (ROOT/'app'/asset.split('?',1)[0].lstrip('/')).is_file(),asset
 assert "key.startsWith('mlo-static-')" in worker
 print(json.dumps({'python_files':len(python),'templates':len(names),'javascript_files':len(javascript),'cache_version':APP_VERSION,'cache_assets':len(assets)}))
if __name__=='__main__':main()
