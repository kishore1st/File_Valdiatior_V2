# Okta JWT verification stub. Fill in JWKS fetch + verify in production.
import httpx
from ..config import settings

async def verify_jwt(token: str) -> dict:
    if not settings.OKTA_JWKS_URL:
        # Local dev: trust the token as-is (matches deps.current_user)
        return {"okta_user_id": token}
    async with httpx.AsyncClient() as c:
        jwks = (await c.get(settings.OKTA_JWKS_URL)).json()
    # ... implement JWKS-based verification ...
    return {"okta_user_id": token}