import asyncio, logging
from ...db import pool
from .base import watcher_tick
from .sftp import SftpConnector
from .dbx_volume import DatabricksVolumeConnector
from .sharepoint import SharePointConnector

log = logging.getLogger("scheduler")

_CONNECTOR_MAP = {
    "SFTP_FOLDER": SftpConnector,
    "DBX_VOLUME": DatabricksVolumeConnector,
    "SP_FOLDER": SharePointConnector,
}

async def _tick_one(loc):
    connector_cls = _CONNECTOR_MAP.get(loc["location_type"])
    if connector_cls is None:
        return
    connector = connector_cls(loc["config"])
    p = await pool()
    async with p.acquire() as conn:
        try:
            await watcher_tick(conn, dict(loc), connector)
        except Exception as e:
            log.exception("tick failed for %s: %s", loc["location_id"], e)

async def run_scheduler():
    p = await pool()
    while True:
        try:
            async with p.acquire() as conn:
                locs = await conn.fetch(
                    "SELECT wl.*, wm.status AS wm_status FROM fvi.watched_locations wl "
                    "LEFT JOIN fvi.watermarks wm USING (location_id) "
                    "WHERE wl.is_active AND COALESCE(wm.status,'IDLE') <> 'PAUSED'"
                )
            await asyncio.gather(*[_tick_one(dict(loc)) for loc in locs], return_exceptions=True)
        except Exception as e:
            log.exception("scheduler error: %s", e)
        await asyncio.sleep(30)