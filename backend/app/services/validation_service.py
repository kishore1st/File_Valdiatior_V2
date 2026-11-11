import csv, io, json
from datetime import datetime
import asyncpg

def _infer_type(value: str) -> str:
    v = (value or "").strip()
    if v == "":
        return "string"
    try:
        int(v); return "integer"
    except ValueError:
        pass
    try:
        float(v); return "decimal"
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            datetime.strptime(v, fmt); return "date"
        except ValueError:
            pass
    if v.lower() in ("true", "false"):
        return "boolean"
    return "string"

def validate_first_n_records(
    body: bytes,
    region_code: str,
    schema_type_key: str,
    conn: asyncpg.Connection,
    n: int = 5,
) -> dict:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return {"is_valid": False, "error_summary": "not utf-8"}

    reader = csv.DictReader(io.StringIO(text))
    rows = [r for _, r in zip(range(n), reader)]
    if not rows:
        return {"is_valid": False, "error_summary": "empty file"}

    import asyncio
    # Fetch schema field definitions from reference_data
    async def _fetch_fields():
        return await conn.fetch(
            "SELECT key, position, value FROM fvi.reference_data "
            "WHERE category='schema_field' AND parent_key=$1 AND is_active "
            "ORDER BY position", schema_type_key,
        )
    # caller is sync; use run-in-loop bridge via a small helper in worker contexts
    # For simplicity, run inline only when an event loop exists.
    try:
        loop = asyncio.get_running_loop()
        fields = asyncio.run_coroutine_threadsafe(_fetch_fields(), loop).result()
    except RuntimeError:
        return {"is_valid": False, "error_summary": "no event loop available"}

    expected = [{"name": f["key"], "position": f["position"], "data_type": json.loads(json.dumps(f["value"]))["data_type"]} for f in fields]
    mismatches = []
    for row_idx, row in enumerate(rows, start=1):
        for exp in expected:
            val = row.get(exp["name"], "")
            actual = _infer_type(val)
            if actual != exp["data_type"] and not (exp["data_type"] == "decimal" and actual == "integer"):
                mismatches.append({
                    "record": row_idx, "field": exp["name"],
                    "expected": exp["data_type"], "actual": actual, "value": val,
                })
    return {
        "is_valid": len(mismatches) == 0,
        "records_checked": len(rows),
        "mismatches": mismatches,
        "error_summary": None if not mismatches else f"{len(mismatches)} field mismatch(es)",
    }