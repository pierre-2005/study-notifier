"""One-time automatic pre-v3 backup using SQLite's consistent backup API."""
from pathlib import Path
import sqlite3
import os
from app.db import DB_PATH


def pre_v37_backup():
    """Fail closed if the pre-migration online backup cannot be created."""
    source=Path(DB_PATH)
    if not source.is_file() or not source.stat().st_size:
        return None
    target=source.with_name(source.stem+'.pre-mlo-v3.7.sqlite.backup')
    if target.exists():
        with sqlite3.connect(f'file:{target}?mode=ro',uri=True) as saved:
            if saved.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise RuntimeError('The v3.7 migration backup failed its integrity check.')
        return target
    partial=target.with_name(target.name+'.partial')
    with sqlite3.connect(f'file:{source}?mode=ro',uri=True,timeout=30) as original:
        with sqlite3.connect(partial) as saved:
            original.backup(saved)
            if saved.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise RuntimeError('The v3.7 migration backup failed its integrity check.')
    os.chmod(partial,0o600)
    os.replace(partial,target)
    return target

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


def pre_consolidation_backup():
    """One-time consistent snapshot before the non-destructive v3.1 import."""
    source=Path(DB_PATH)
    if not source.is_file() or source.stat().st_size == 0: return None
    target=source.with_name(source.stem+'.pre-mlo-v3.1.sqlite.backup')
    if target.exists(): return target
    dest=target.with_suffix(target.suffix+'.partial')
    try:
        with sqlite3.connect(str(source),timeout=30) as original:
            with sqlite3.connect(str(dest),timeout=30) as saved: original.backup(saved)
        os.replace(dest,target)
        return target
    finally:
        if dest.exists(): dest.unlink()


def pre_v34_backup():
    """Consistent one-time snapshot before v3.4 starts modifying indexes/data."""
    source=Path(DB_PATH)
    if not source.is_file() or not source.stat().st_size: return None
    target=source.with_name(source.stem+'.pre-mlo-v3.4.sqlite.backup')
    if target.exists(): return target
    partial=target.with_name(target.name+'.partial')
    try:
        with sqlite3.connect(str(source),timeout=30) as existing:
            with sqlite3.connect(str(partial),timeout=30) as saved:
                existing.backup(saved)
        os.replace(partial,target)
        return target
    finally:
        if partial.exists(): partial.unlink()


def pre_v36_backup():
    """One-time SQLite snapshot before additive account-security schema migration."""
    source=Path(DB_PATH)
    if not source.is_file() or source.stat().st_size==0: return None
    target=source.with_name(source.stem+'.pre-mlo-v3.6.sqlite.backup')
    if target.exists(): return target
    partial=target.with_name(target.name+'.partial')
    try:
        with sqlite3.connect(str(source),timeout=30) as original:
            with sqlite3.connect(str(partial),timeout=30) as saved:
                original.backup(saved)
        os.replace(partial,target)
        return target
    finally:
        if partial.exists(): partial.unlink()
