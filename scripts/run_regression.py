"""Run every standalone regression script in an isolated Python process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['all','browser','service'],default='all')
    parser.add_argument('--output',default='test-results')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    results=[]
    for path in sorted(root.glob('tests*.py')):
        browser='playwright' in path.read_text()
        if args.kind=='browser' and not browser or args.kind=='service' and browser:continue
        start=time.monotonic()
        try:
            with (output/(path.stem+'.log')).open('w') as log:
                proc=subprocess.run([sys.executable,str(path)],cwd=root,stdout=log,stderr=subprocess.STDOUT,
                                    env={**os.environ,'MLO_SCHEDULER_ENABLED':'false','PYTHONTZPATH':''},timeout=360)
            status='passed' if proc.returncode==0 else 'failed'
        except subprocess.TimeoutExpired:status='timed_out'
        results.append({'script':path.name,'status':status,'seconds':round(time.monotonic()-start,2)})
        print(status.upper()+': '+path.name,flush=True)
        if status=='failed':
            print((output/(path.stem+'.log')).read_text()[-8000:],flush=True)
    (output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    return int(any(r['status']!='passed' for r in results))


if __name__=='__main__':sys.exit(main())
