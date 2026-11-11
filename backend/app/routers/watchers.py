from fastapi import APIRouter, Depends, HTTPException
import asyncpg, uuid
from ..deps import current_user, db

router = APIRouter(prefix="/v1/watchers", tags=["watchers"])

@router.get("")
async def list_watchers(user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    rows = await conn.fetch(
        "SELECT wl.*, wm.status AS wm_status, wm.last_discovery_at "
        "FROM fvi.watched_locations wl LEFT JOIN fvi.watermarks wm USING (location_id) "
        "ORDER BY wl.created_at DESC"
    )
    return [dict(r) for r in rows]

@router.get("/{location_id}/runs")
async def watcher_runs(location_id: uuid.UUID, user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    rows = await conn.fetch(
        "SELECT * FROM fvi.watcher_runs WHERE location_id=$1 ORDER BY started_at DESC LIMIT 100",
        location_id,
    )
    return [dict(r) for r in rows]

@router.post("/{location_id}/reset")
async def watcher_reset(location_id: uuid.UUID, user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    if "admin" not in user["roles"]:
        raise HTTPException(403, "admin role required")
    await conn.execute(
        "UPDATE fvi.watermarks SET last_discovery_at='1970-01-01', source_cursor=NULL, status='IDLE' WHERE location_id=$1",
        location_id,
    )
    await conn.execute(
        "INSERT INTO fvi.file_events (event_type, actor_type, actor_user_id) "
        "VALUES ('WATERMARK_RESET','USER',$1)", user["user_id"],
    )
    return {"ok": True}

@router.post("/{location_id}/pause")
async def watcher_pause(location_id: uuid.UUID, user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    if "admin" not in user["roles"]:
        raise HTTPException(403, "admin role required")
    await conn.execute("UPDATE fvi.watermarks SET status='PAUSED' WHERE location_id=$1", location_id)
    return {"ok": True}