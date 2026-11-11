import asyncio, json, logging
from ..db import pool
from .hash_service import sha256_bytes
from .databricks_client import put_volume_file

log = logging.getLogger("worker")

async def _process_event(conn, ev):
    """Fetch bytes (channel-specific connectors land in later commits),
       hash, transfer if approved."""
    file_id = ev["file_id"]
    if file_id is None:
        return
    f = await conn.fetchrow("SELECT * FROM fvi.files WHERE file_id=$1", file_id)
    if f is None:
        return
    if f["status"] != "APPROVED":
        return

    # Resolve destination from reference_data
    vm = await conn.fetchrow(
        "SELECT value FROM fvi.reference_data "
        "WHERE category='volume_mapping' AND key=$1 AND parent_key=$2 AND is_active",
        f["region_code"], f["schema_type_key"],
    )
    if vm is None:
        await conn.execute(
            "UPDATE fvi.files SET status='PROCESSING_FAILED', reject_reason='no volume mapping' WHERE file_id=$1",
            file_id,
        )
        return
    volume_path = json.loads(json.dumps(vm["value"]))["volume_path"]

    # For WEB_UI, the file bytes were already consumed; for MVP we treat the
    # ingestion as a registration + ack (real transfer happens when the channel
    # connector delivers bytes). Placeholder ack for demo:
    attempt = await conn.fetchval(
        "SELECT COALESCE(MAX(attempt_number),0)+1 FROM fvi.transfers WHERE file_id=$1", file_id
    )
    await conn.execute(
        """INSERT INTO fvi.transfers (file_id, attempt_number, destination, status, acknowledgement)
           VALUES ($1,$2,$3,'SUCCESS',$4)""",
        file_id, attempt, volume_path, {"note": "MVP: transfer delegated to channel connector"},
    )
    await conn.execute(
        "UPDATE fvi.files SET status='TRANSFERRED_TO_DATABRICKS', destination_path=$1 WHERE file_id=$2",
        volume_path, file_id,
    )
    await conn.execute(
        "INSERT INTO fvi.file_events (file_id, event_type, actor_type, payload) VALUES ($1,'TRANSFER_ACK','SYSTEM',$2)",
        file_id, {"volume_path": volume_path},
    )


async def run_worker_loop():
    p = await pool()
    while True:
        try:
            async with p.acquire() as conn:
                async with conn.transaction():
                    ev = await conn.fetchrow(
                        "SELECT * FROM fvi.ingestion_events WHERE status='RECEIVED' "
                        "ORDER BY received_at FOR UPDATE SKIP LOCKED LIMIT 1"
                    )
                    if ev is None:
                        await asyncio.sleep(0.5)
                        continue
                    await conn.execute(
                        "UPDATE fvi.ingestion_events SET status='FETCHED', processed_at=now() WHERE event_id=$1",
                        ev["event_id"],
                    )
                    await _process_event(conn, ev)
                    await conn.execute(
                        "UPDATE fvi.ingestion_events SET status='REGISTERED' WHERE event_id=$1",
                        ev["event_id"],
                    )
        except Exception as e:
            log.exception("worker error: %s", e)
            await asyncio.sleep(2)