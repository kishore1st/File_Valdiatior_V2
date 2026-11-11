# Pull recently ingested files from system.access.audit and POST to FastAPI
import os, requests
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

FVI_API = os.environ["FVI_API"]       # e.g. https://fvi.internal
FVI_KEY = os.environ["FVI_KEY"]

rows = spark.sql("""
  SELECT * FROM system.access.audit
  WHERE service_name='unityCatalog'
    AND action_name='putFile'
    AND event_time > current_timestamp() - INTERVAL 1 HOUR
""").collect()

for row in rows:
    requests.post(f"{FVI_API}/v1/databricks/audit", json=row.asDict(),
                  headers={"X-Api-Key": FVI_KEY}, timeout=30)