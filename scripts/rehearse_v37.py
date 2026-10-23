"""Back up a read-only source, migrate a staging copy, and verify restoration.

Usage: python -m scripts.rehearse_v37 --source BACKUP.db --work-dir EMPTY_DIRECTORY
No scheduler, external requests, production secrets, or writes to the source DB.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3


def quote(name):
    return '"'+name.replace('"','""')+'"'


def online_backup(source,target):
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30)) as original:
        with closing(sqlite3.connect(target)) as saved:
            original.backup(saved)
            if saved.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise RuntimeError('Backup integrity check failed.')
    target.chmod(0o600)


def counts(db):
    tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return {t:db.execute(f'SELECT COUNT(*) FROM {quote(t)}').fetchone()[0] for t in tables}


def rehearse(source,work_dir,legacy_username=''):
    source=Path(source).resolve(strict=True);work_dir=Path(work_dir).resolve()
    if work_dir.exists() and any(work_dir.iterdir()):
        raise ValueError('Use an empty staging directory. Existing files will not be replaced.')
    work_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup,stage,restored=(work_dir/name for name in ('baseline.sqlite','staging.sqlite','restored.sqlite'))
    online_backup(source,backup)
    online_backup(backup,stage)
    os.environ.update(STUDY_NOTIFIER_DB=str(stage),APP_USERNAME=legacy_username,APP_PASSWORD='',
                      MLO_SCHEDULER_ENABLED='false',MLO_CALENDAR_AUTO_SYNC='false')
    # Imports happen only after the staging database path is fixed.
    from app.bootstrap import initialize_database
    initialize_database(legacy_username,'',backup=False)
    with closing(sqlite3.connect(stage)) as migrated:
        first=counts(migrated)
    initialize_database(legacy_username,'',backup=False)
    with closing(sqlite3.connect(stage)) as migrated:
        second=counts(migrated)
        if first!=second:
            raise RuntimeError('Repeated migration changed table row counts.')
        if migrated.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise RuntimeError('Staging integrity check failed.')
        if migrated.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Staging has foreign-key violations. Review the source on a private copy.')
        migrated.execute('ATTACH DATABASE ? AS baseline',(str(backup),))
        original_tables=[r[0] for r in migrated.execute("SELECT name FROM baseline.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        for table in original_tables:
            columns=[r[1] for r in migrated.execute(f'PRAGMA baseline.table_info({quote(table)})')]
            names=','.join(quote(c) for c in columns)
            missing=migrated.execute(f'''SELECT COUNT(*) FROM (
                SELECT {names} FROM baseline.{quote(table)} EXCEPT SELECT {names} FROM main.{quote(table)})''').fetchone()[0]
            if missing:
                raise RuntimeError(f'Original rows changed in {table}; staging review is required.')
        migrated.execute('DETACH DATABASE baseline')
    online_backup(backup,restored)
    with closing(sqlite3.connect(restored)) as check, closing(sqlite3.connect(backup)) as before:
        if list(check.iterdump())!=list(before.iterdump()):
            raise RuntimeError('Restoration did not match the baseline.')
    report={'status':'passed','checked_at':datetime.now(timezone.utc).isoformat(),
            'original_tables_preserved':len(original_tables),'staging_tables':len(second),
            'migration_idempotent':True,'integrity_check':'ok','foreign_key_check':'ok',
            'restoration_matches_baseline':True,'source_opened_read_only':True,
            'external_io':'disabled','production_verification':False}
    (work_dir/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--work-dir',required=True)
    parser.add_argument('--legacy-owner-username',default='')
    args=parser.parse_args()
    rehearse(args.source,args.work_dir,args.legacy_owner_username)
