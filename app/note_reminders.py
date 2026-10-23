"""Owner-scoped review dates for personal and explicitly shared notes."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.db import get_conn
from app.lifeos import note_access, user_id
from app.v37 import read_user_setup

router=APIRouter(prefix='/life/notes',tags=['personal note reminders'])


@router.post('/{note_id}/reminder')
def review_date(request:Request,note_id:int,review_at:str=Form(...)):
    uid=user_id(request)
    with get_conn() as db:
        note_access(db,uid,note_id)
        prefs=read_user_setup(db,uid)
        zone=ZoneInfo(prefs['timezone'])
        try:
            local=datetime.fromisoformat(review_at)
            if local.tzinfo is not None or not 2000<=local.year<=2100:raise ValueError()
            local=local.replace(tzinfo=zone)
            stamp=local.astimezone(timezone.utc)
            if stamp.astimezone(zone).replace(tzinfo=None)!=local.replace(tzinfo=None):raise ValueError()
            if local.replace(fold=0).utcoffset()!=local.replace(fold=1).utcoffset():raise ValueError()
        except ValueError as exc:
            raise HTTPException(422,'Choose a valid local date and time, including daylight saving changes.') from exc
        db.execute('''INSERT INTO life_note_reminders(user_id,note_id,remind_at_utc) VALUES(?,?,?)
            ON CONFLICT(user_id,note_id) DO UPDATE SET remind_at_utc=excluded.remind_at_utc''',
            (uid,note_id,stamp.isoformat()))
        db.commit()
    return RedirectResponse(f'/life/notes/{note_id}',303)


@router.post('/{note_id}/reminder/delete')
def cancel_review_date(request:Request,note_id:int):
    uid=user_id(request)
    with get_conn() as db:
        note_access(db,uid,note_id)
        db.execute('DELETE FROM life_note_reminders WHERE user_id=? AND note_id=?',(uid,note_id))
        db.commit()
    return RedirectResponse(f'/life/notes/{note_id}',303)
