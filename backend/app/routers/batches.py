from fastapi import APIRouter, Depends, HTTPException
import asyncpg, uuid
from ..deps import current_user, db

router = APIRouter(prefix="/v1/batches", tags=["batches"])

@router.get("/{batch_id}")
async def get_batch(batch_id: uuid.UUID, user=Depends(current_user), conn: asyncpg.Connection = Depends(db)):
    row = await conn.fetchrow("SELECT * FROM fvi.v_batch_summary WHERE batch_id=$1", batch_id)
    if not row:
        raise HTTPException(404, "batch not found")
    return dict(row)