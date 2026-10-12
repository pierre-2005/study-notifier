"""One-time automatic pre-v3 backup using SQLite's consistent backup API."""
from pathlib import Path
import sqlite3
import os
from app.db import DB_PATH

def pre_v3_backup():
    source=Path(DB_PATH)
    if not source.is_file() or source.stat().st_size==0:
        return None
    target=source.with_name(source.stem+'.pre-mlo-v3.sqlite.backup')
    if target.exists():
        return target
    source.parent.mkdir(parents=True,exist_ok=True)
    dest=target.with_suffix(target.suffix+'.partial')
    try:
        with sqlite3.connect(str(source),timeout=30) as original:
            with sqlite3.connect(str(dest),timeout=30) as saved:
                original.backup(saved)
        os.replace(dest,target)
        return target
    finally:
        if dest.exists(): dest.unlink()
