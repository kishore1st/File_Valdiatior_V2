import json, uuid, logging
from dataclasses import dataclass
from typing import AsyncIterator, Protocol

log = logging.getLogger("watcher")

@dataclass
class DiscoveredItem:
    ref: str
    version: str | None
    name: str
    size: int | None
    modified_at: object
    raw: dict
    ext: str = "csv"

class Connector(Protocol):
    async def list_since(self, location: dict, since, cursor) -> AsyncIterator[DiscoveredItem]: ...
    async def fetch(self, item: DiscoveredItem) -> bytes: ...


async def watcher_tick(conn, location: dict, connector: Connector, page_size: int = 200) -> dict:
    """Run one incremental discovery pass for a watched location.

    Invariants:
    - Locks the watermark row FOR UPDATE (Req 31/32 concurrency safety)
    - Inserts into discovery_log with UNIQUE(location_id, source_ref, version)
    - Inserts ingestion_events for each new discovery
    - Advances watermark only after events are enqueued
    """
    wm = await conn.fetchrow(
        "SELECT * FROM fvi.watermarks WHERE location_id=$1 FOR UPDATE",
        location["location_id"],
    )
    if wm is None:
        # create an empty watermark on first tick
        wm = await conn.fetchrow(
            "INSERT INTO fvi.watermarks (location_id) VALUES ($1) RETURNING *",
            location["location_id"],
        )
    if wm["status"] == "PAUSED":
        return {"status": "PAUSED"}

    run = await conn.fetchrow(
        "INSERT INTO fvi.watcher_runs (location_id) VALUES ($1) RETURNING run_id",
        location["location_id"],
    )
    try:
        discovered = fetched = skipped = 0
        last_ts, last_ref, new_cursor = None, None, wm["source_cursor"]
        async for item in connector.list_since(location, wm["last_discovery_at"], wm["source_cursor"]):
            discovered += 1
            try:
                disc = await conn.fetchrow(
                    """INSERT INTO fvi.discovery_log
                       (location_id, source_ref, source_version, file_name,
                        file_size_bytes, source_modified_at)
                       VALUES ($1,$2,$3,$4,$5,$6)
                       ON CONFLICT (location_id, source_ref, COALESCE(source_version, '-'))
                       DO NOTHING
                       RETURNING discovery_id""",
                    location["location_id"], item.ref, item.version,
                    item.name, item.size, item.modified_at,
                )
            except Exception:
                disc = None
            if disc is None:
                skipped += 1
                continue
            ev = await conn.fetchrow(
                """INSERT INTO fvi.ingestion_events
                   (source_id, location_id, discovery_id, correlation_id, raw_payload,
                    file_name, file_size_bytes, declared_ext, source_ref, status)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'RECEIVED')
                   RETURNING event_id""",
                location["source_id"], location["location_id"],
                disc["discovery_id"], uuid.uuid4(),
                json.dumps(item.raw), item.name, item.size or 0, item.ext, item.ref,
            )
            await conn.execute(
                "UPDATE fvi.discovery_log SET ingestion_event_id=$1, status='FETCHED' WHERE discovery_id=$2",
                ev["event_id"], disc["discovery_id"],
            )
            last_ts, last_ref = item.modified_at, item.ref
            fetched += 1

        if hasattr(connector, "cursor"):
            new_cursor = connector.cursor  # channel-specific delta token

        await conn.execute(
            """UPDATE fvi.watermarks
               SET last_discovery_at = COALESCE($2, last_discovery_at),
                   last_discovered_item = COALESCE($3, last_discovered_item),
                   source_cursor = COALESCE($4, source_cursor),
                   status='IDLE',
                   last_run_at=now(),
                   consecutive_failures=0,
                   updated_at=now()
               WHERE location_id=$1""",
            location["location_id"], last_ts, last_ref, new_cursor,
        )
        await conn.execute(
            """UPDATE fvi.watcher_runs
               SET finished_at=now(), status='SUCCESS', files_discovered=$2,
                   files_fetched=$3, files_skipped=$4,
                   duration_ms=EXTRACT(EPOCH FROM (now()-started_at))*1000
               WHERE run_id=$1""",
            run["run_id"], discovered, fetched, skipped,
        )
        await conn.execute(
            "INSERT INTO fvi.file_events (event_type, actor_type, payload) VALUES ('WATCHER_TICK','SYSTEM',$1)",
            {"location_id": str(location["location_id"]), "discovered": discovered, "fetched": fetched},
        )
        return {"status": "SUCCESS", "discovered": discovered, "fetched": fetched, "skipped": skipped}
    except Exception as e:
        log.exception("watcher tick failed: %s", e)
        await conn.execute(
            """UPDATE fvi.watermarks
               SET status='ERROR', last_error=$2,
                   consecutive_failures=consecutive_failures+1,
                   last_run_at=now(), updated_at=now()
               WHERE location_id=$1""",
            location["location_id"], str(e),
        )
        await conn.execute(
            """UPDATE fvi.watcher_runs SET finished_at=now(), status='FAILED', error_message=$2,
               duration_ms=EXTRACT(EPOCH FROM (now()-started_at))*1000 WHERE run_id=$1""",
            run["run_id"], str(e),
        )
        raise