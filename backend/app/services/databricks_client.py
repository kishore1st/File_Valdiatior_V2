import httpx
from ..config import settings

async def put_volume_file(volume_path: str, filename: str, content: bytes) -> dict:
    url = f"{settings.DATABRICKS_HOST}/api/2.1/unity-catalog/volumes{volume_path}files/{filename}"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.put(url, content=content,
                        headers={"Authorization": f"Bearer {settings.DATABRICKS_TOKEN}"})
        r.raise_for_status()
        return r.json()

async def list_volume_files(volume_path: str) -> list[dict]:
    url = f"{settings.DATABRICKS_HOST}/api/2.1/unity-catalog/volumes{volume_path}files"
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(url, headers={"Authorization": f"Bearer {settings.DATABRICKS_TOKEN}"})
        r.raise_for_status()
        return r.json().get("files", [])