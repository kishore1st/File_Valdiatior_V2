"""E2E (Req 31B): Databricks Volume watermark prevents re-ingest."""
import pytest
from datetime import datetime, timedelta
from backend.app.services.watchers.base import DiscoveredItem

class FakeVolumeConnector:
    def __init__(self, items): self.items, self.cursor = items, None
    async def list_since(self, location, since, cursor):
        for it in self.items:
            if since and it.modified_at <= since: continue
            yield it
    async def fetch(self, item): return b"y"

@pytest.mark.asyncio
async def test_volume_incremental(db_conn, make_watched_location):
    loc = await make_watched_location("DBX_VOLUME")
    t = datetime.utcnow()
    await db_conn.execute("UPDATE fvi.watermarks SET last_discovery_at=$1 WHERE location_id=$2",
                          t - timedelta(hours=1), loc)
    items = [
        DiscoveredItem(ref="/v/old.csv", version="1", name="old.csv", size=1,
                       modified_at=t - timedelta(hours=2), raw={}),
        DiscoveredItem(ref="/v/new.csv", version="2", name="new.csv", size=1,
                       modified_at=t, raw={}),
    ]
    from backend.app.services.watchers.base import watcher_tick
    result = await watcher_tick(db_conn, dict(location_id=loc), FakeVolumeConnector(items))
    assert result["discovered"] == 1
    assert result["fetched"] == 1