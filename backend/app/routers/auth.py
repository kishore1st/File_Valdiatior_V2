from fastapi import APIRouter, Depends
from ..deps import current_user

router = APIRouter(prefix="/v1/auth", tags=["auth"])

@router.get("/me")
async def me(user=Depends(current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "roles": user["roles"],
        "region_code": user["region_code"],
    }