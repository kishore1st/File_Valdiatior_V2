from fastapi import APIRouter, Depends, Request
import asyncpg, uuid
from ..deps import db

router = APIRouter(prefix="/v1/databricks", tags=["databricks"])

@router.post("/audit")
async def accept_audit(request: Request, conn: asyncpg.Connection = Depends(db)):
    body = await request.json()
    await conn.execute(
        "INSERT INTO fvi.file_events (event_type, actor_type, payload) "
        "VALUES ('DBX_INGEST','SYSTEM',$1)", body,
    )
    return {"ok": True}

@router.get("/reconciliation")
async def recon(conn: asyncpg.Connection = Depends(db)):
    rows = await conn.fetch("SELECT * FROM fvi.reconciliation WHERE is_consistent=FALSE ORDER BY reconciled_at DESC LIMIT 500")
    return [dict(r) for r in rows]