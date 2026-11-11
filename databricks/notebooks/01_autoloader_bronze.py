# Databricks notebook: Auto Loader to Bronze (one stream per region/schema)
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

REGIONS = ["IN", "US", "EU", "GB", "AE"]

for r in REGIONS:
    src = f"/Volumes/main/bronze/incoming/{r}/customer/"
    chk = f"/Volumes/main/checkpoints/{r}/customer"
    sch = f"/Volumes/main/checkpoints/{r}/schema/customer"

    (spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("header", "true")
        .option("cloudFiles.schemaLocation", sch)
        .load(src)
        .writeStream
        .option("checkpointLocation", chk)
        .trigger(availableNow=True)
        .toTable(f"main.bronze.customer_{r.lower()}"))