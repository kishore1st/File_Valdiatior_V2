"""E2E (Req 27): authenticated multi-file batch with one duplicate.
Assumes API at FVI_API and a valid bearer token in FVI_TOKEN env."""
import os, uuid, httpx, pytest

API = os.environ.get("FVI_API", "http://localhost:8000")
TOKEN = os.environ.get("FVI_TOKEN", "okta-uploader")

@pytest.mark.asyncio
async def test_batch_partial_success():
    hdr = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(base_url=API, timeout=30) as c:
        # 3 files: two valid, one duplicate of the first
        a = b"customer_id,first_name,last_name,dob,country\n9,A,B,1990-01-01,IN\n"
        b = b"customer_id,first_name,last_name,dob,country\n10,C,D,1991-02-02,IN\n"
        files = [
            ("files", ("a.csv", a, "text/csv")),
            ("files", ("b.csv", b, "text/csv")),
            ("files", ("a2.csv", a, "text/csv")),
        ]
        r = await c.post("/v1/batches",
                         data={"schema_type_key": "customer", "region_code": "IN"},
                         files=files, headers=hdr)
        r.raise_for_status()
        body = r.json()
        assert body["total_files"] == 3
        assert body["accepted"] + body["rejected"] == 3
        assert body["rejected"] >= 1  # one duplicate

        # batch summary view reports outcomes
        r2 = await c.get(f"/v1/batches/{body['batch_id']}", headers=hdr)
        r2.raise_for_status()
        summary = r2.json()
        assert summary["total_files"] == 3