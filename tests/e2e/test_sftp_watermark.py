"""E2E (Req 31A): watermark prevents re-discovery."""
import pytest
from datetime import datetime, timedelta
from backend.app.services.watchers.base import DiscoveredItem

class FakeConnector:
    def __init__(self, items): self.items, self.cursor = items, None
    async def list_since(self, location, since, cursor):
        for it in self.items:
            if since and it.modified_at <= since: continue
            yield it
    async def fetch(self, item): return b"x"

@pytest.mark.asyncio
async def test_watermark_skips_old_files(db_conn, make_watched_location):
    loc = await make_watched_location("SFTP_FOLDER")
    now = datetime.utcnow()
    old = DiscoveredItem(ref="/a.csv", version="1", name="a.csv", size=1,
                         modified_at=now - timedelta(days=2), raw={})
    new = DiscoveredItem(ref="/b.csv", version="2", name="b.csv", size=1,
                         modified_at=now, raw={})
    # First tick sees only 'new' (old is before watermark default 1970 -> actually both)
    # Set watermark forward, then run again to confirm only new file is discovered.
    await db_conn.execute("UPDATE fvi.watermarks SET last_discovery_at=$1 WHERE location_id=$2",
                          now - timedelta(days=1), loc)
    from backend.app.services.watchers.base import watcher_tick
    result = await watcher_tick(db_conn, dict(location_id=loc), FakeConnector([old, new]))
    assert result["fetched"] == 1