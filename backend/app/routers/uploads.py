from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
import asyncpg, uuid
from ..deps import current_user, db
from ..services.hash_service import sha256_bytes
from ..services.validation_service import validate_first_n_records

router = APIRouter(prefix="/v1/batches", tags=["batches"])

@router.post("", status_code=202)
async def upload_batch(
    schema_type_key: str = Form(...),
    region_code: str = Form(...),
    files: list[UploadFile] = File(...),
    user=Depends(current_user),
    conn: asyncpg.Connection = Depends(db),
):
    if not files:
        raise HTTPException(422, "no files provided")

    correlation_id = uuid.uuid4()
    async with conn.transaction():
        batch = await conn.fetchrow(
            """INSERT INTO fvi.upload_batches
               (correlation_id, user_id, schema_type_key, region_code, total_files)
               VALUES ($1,$2,$3,$4,$5) RETURNING batch_id""",
            correlation_id, user["user_id"], schema_type_key, region_code, len(files),
        )
    accepted = rejected = 0
    for f in files:
        body = await f.read()
        sha = sha256_bytes(body)
        ext = (f.filename or "").rsplit(".", 1)[-1].lower()
        src = await conn.fetchrow(
            "SELECT source_id FROM fvi.ingestion_sources WHERE source_type='WEB_UI' LIMIT 1"
        )
        source_id = src["source_id"] if src else None
        row = await conn.fetchrow(
            "SELECT * FROM fvi.register_file($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)",
            batch["batch_id"], sha, f.filename, len(body), ext,
            region_code, schema_type_key, user["user_id"],
            "api", None, source_id, None,
        )
        if row["is_duplicate"]:
            await conn.execute(
                "UPDATE fvi.files SET status='DUPLICATE_DETECTED', reject_reason=$1 WHERE file_id=$2",
                "sha256 already registered", row["file_id"],
            )
            await conn.execute(
                "INSERT INTO fvi.file_events (correlation_id, file_id, batch_id, event_type, actor_type, actor_user_id) "
                "VALUES ($1,$2,$3,'DUPLICATE','USER',$4)",
                correlation_id, row["file_id"], batch["batch_id"], user["user_id"],
            )
            rejected += 1
            continue

        await conn.execute(
            "UPDATE fvi.files SET status='QUEUED' WHERE file_id=$1", row["file_id"]
        )
        # enqueue an ingestion event so the worker picks it up
        await conn.execute(
            """INSERT INTO fvi.ingestion_events
               (source_id, correlation_id, raw_payload, file_name, file_size_bytes,
                declared_ext, source_ref, status, file_id)
               VALUES ($1,$2,$3,$4,$5,$6,$7,'RECEIVED',$8)""",
            source_id, correlation_id,
            {"origin": "WEB_UI", "uploader": user["email"]},
            f.filename, len(body), ext, f"browser://{f.filename}", row["file_id"],
        )

        # validate first 5 records against schema
        outcome = validate_first_n_records(body, region_code, schema_type_key, conn, n=5)
        await conn.execute(
            "INSERT INTO fvi.file_events (correlation_id, file_id, batch_id, event_type, actor_type, payload) "
            "VALUES ($1,$2,$3,'VALIDATION','SYSTEM',$4)",
            correlation_id, row["file_id"], batch["batch_id"], outcome,
        )
        if outcome["is_valid"]:
            await conn.execute(
                "UPDATE fvi.files SET status='APPROVED', latest_validation_status='VALID' WHERE file_id=$1",
                row["file_id"],
            )
            accepted += 1
        else:
            await conn.execute(
                "UPDATE fvi.files SET status='VALIDATION_FAILED', latest_validation_status='INVALID', "
                "reject_reason=$1 WHERE file_id=$2",
                outcome.get("error_summary", "schema mismatch"), row["file_id"],
            )
            rejected += 1

    final_status = "COMPLETED" if rejected == 0 else ("PARTIAL_SUCCESS" if accepted > 0 else "FAILED")
    await conn.execute(
        "UPDATE fvi.upload_batches SET status=$1, completed_at=now() WHERE batch_id=$2",
        final_status, batch["batch_id"],
    )
    return {
        "batch_id": str(batch["batch_id"]),
        "correlation_id": str(correlation_id),
        "total_files": len(files),
        "accepted": accepted,
        "rejected": rejected,
        "status": final_status,
    }