"""Isolated statement parser, called with bounded input and a parent timeout."""
import json,sys
from dataclasses import asdict
from app.finance.parser import parse_statement
if __name__=='__main__':
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(40,40))
    except (ImportError,ValueError,OSError):pass
    options=json.loads(sys.stdin.read(200000))
    print(json.dumps([asdict(tx) for tx in parse_statement(sys.argv[1],**options)]))
