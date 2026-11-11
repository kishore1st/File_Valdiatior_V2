from datetime import datetime
import httpx
from .base import DiscoveredItem

class SharePointConnector:
    """Uses Microsoft Graph delta API.
    Requires a valid bearer token in cfg['token'] (refreshed by a separate job).
    """
    def __init__(self, cfg: dict):
        self.drive_id = cfg["drive_id"]
        self.token = cfg["token"]
        self.graph_base = "https://graph.microsoft.com/v1.0"
        self.cursor = None

    async def list_since(self, location, since, cursor):
        token = cursor
        url = (f"{self.graph_base}/drives/{self.drive_id}/root/delta" +
               (f"?token={token}" if token else ""))
        async with httpx.AsyncClient(timeout=60) as c:
            while url:
                r = await c.get(url, headers={"Authorization": f"Bearer {self.token}"})
                r.raise_for_status()
                data = r.json()
                for item in data.get("value", []):
                    if "file" not in item:
                        continue
                    mtime = datetime.fromisoformat(item["lastModifiedDateTime"].replace("Z", "+00:00"))
                    if since and mtime <= since:
                        continue
                    yield DiscoveredItem(
                        ref=item["id"],
                        version=item.get("eTag"),
                        name=item["name"],
                        size=item.get("size"),
                        modified_at=mtime,
                        raw={"drive_id": self.drive_id, "item": item},
                    )
                url = data.get("@odata.nextLink")
                if url is None:
                    self.cursor = data.get("@odata.deltaLink", "").split("token=")[-1]

    async def fetch(self, item) -> bytes:
        url = f"{self.graph_base}/drives/{self.drive_id}/items/{item.ref}/content"
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(url, headers={"Authorization": f"Bearer {self.token}"}, follow_redirects=True)
            r.raise_for_status()
            return r.content