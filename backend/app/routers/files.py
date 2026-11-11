from fastapi import APIRouter, Depends, HTTPException, Query
import asyncpg, uuid
from ..deps import current_user, db

router = APIRouter(prefix="/v1/files", tags=["files"])

@router.get("/{file_id}")
async def get_file(file_id: uuid.UUID, user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    row = await conn.fetchrow("SELECT * FROM fvi.files WHERE file_id=$1", file_id)
    if not row:
        raise HTTPException(404, "file not found")
    events = await conn.fetch(
        "SELECT event_id, event_type, occurred_at, payload FROM fvi.file_events "
        "WHERE file_id=$1 ORDER BY occurred_at", file_id
    )
    return {"file": dict(row), "events": [dict(e) for e in events]}

@router.get("")
async def list_files(
    status: str | None = Query(default=None),
    user=Depends(current_user),
    conn: asyncpg.Connection = Depends(db),
):
    if status:
        rows = await conn.fetch("SELECT * FROM fvi.files WHERE status=$1 ORDER BY created_at DESC LIMIT 200", status)
    else:
        rows = await conn.fetch("SELECT * FROM fvi.files ORDER BY created_at DESC LIMIT 200")
    return [dict(r) for r in rows]