from fastapi import Depends, HTTPException, Header
import asyncpg
from .db import pool

async def db() -> asyncpg.Connection:
    p = await pool()
    async with p.acquire() as conn:
        yield conn

async def current_user(
    authorization: str | None = Header(default=None),
    conn: asyncpg.Connection = Depends(db),
):
    # Local demo: accept a bearer token equal to okta_user_id from the users table.
    # In production, verify Okta JWT via JWKS (see services/okta.py).
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    row = await conn.fetchrow(
        "SELECT * FROM fvi.users WHERE okta_user_id=$1 AND access_status='approved' AND is_active",
        token,
    )
    if row is None:
        raise HTTPException(403, "user not approved or not found")
    return dict(row)