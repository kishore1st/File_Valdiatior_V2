from datetime import datetime, timezone
from .base import DiscoveredItem
from ..databricks_client import list_volume_files

class DatabricksVolumeConnector:
    def __init__(self, cfg: dict):
        self.volume_path = cfg["volume_path"]
        self.cursor = None

    async def list_since(self, location, since, cursor):
        files = await list_volume_files(self.volume_path)
        for f in files:
            mtime = datetime.fromtimestamp(f.get("modification_time", 0) / 1000, tz=timezone.utc)
            if since and mtime <= since:
                continue
            yield DiscoveredItem(
                ref=f"{self.volume_path}{f['name']}",
                version=f"{int(f.get('modification_time', 0))}:{f.get('size', 0)}",
                name=f["name"],
                size=f.get("size"),
                modified_at=mtime,
                raw={"volume_path": self.volume_path, "file": f},
            )

    async def fetch(self, item) -> bytes:
        # Download from Volume files API
        import httpx
        from ...config import settings
        url = f"{settings.DATABRICKS_HOST}/api/2.1/unity-catalog/volumes{item.ref}"
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(url, headers={"Authorization": f"Bearer {settings.DATABRICKS_TOKEN}"})
            r.raise_for_status()
            return r.content