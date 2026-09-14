from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.db import DB_PATH


def create_startup_backup(app_version: str, keep: int = 14) -> Path | None:
    """Create at most one consistent SQLite backup per UTC day.

    The backup happens before startup migrations. It is intentionally best-effort:
    a backup failure should not corrupt the source database, but startup continues
    so deployments are not bricked by a read-only backup directory.
    """
    source = Path(DB_PATH)
    if not source.exists() or source.stat().st_size == 0:
        return None

    backup_dir = source.parent / "backups"
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_version = "".join(ch if ch.isalnum() or ch in ".-_" else "-" for ch in (app_version or "unknown"))
    dest = backup_dir / f"{source.stem}-prestart-v{safe_version}-{day}.db"
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        src = sqlite3.connect(source, timeout=10.0)
        dst = sqlite3.connect(dest, timeout=10.0)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        backups = sorted(
            backup_dir.glob(f"{source.stem}-prestart-v*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[max(1, int(keep)):]:
            try:
                old.unlink()
            except OSError:
                pass
        return dest
    except (OSError, sqlite3.Error):
        try:
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink()
        except OSError:
            pass
        return None
