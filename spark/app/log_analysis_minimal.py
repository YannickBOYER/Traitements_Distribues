from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

def main():
    spark = SparkSession.builder.appName("LogAnalysis").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    lines = spark.readStream.format("socket").option("host", "localhost").option("port", 9999).load()

    log_regex = r'^(\S+) \S+ \[([^\]]+)\] "(\S+) (\S+) HTTP/\d\.\d" (\d{3})'

    parsed = lines.select(
        regexp_extract("value", log_regex, 1).alias("ip"),
        regexp_extract("value", log_regex, 2).alias("timestamp"),
        regexp_extract("value", log_regex, 3).alias("method"),
        regexp_extract("value", log_regex, 4).alias("url"),
        regexp_extract("value", log_regex, 5).cast("integer").alias("status")
    )
    
    logs = parsed \
        .withColumn("timestamp", to_timestamp("timestamp", "dd/MMM/yyyy:HH:mm:ss Z")) \
        .filter(col("status") >= 400)

    windowed = logs \
        .withWatermark("timestamp", "30 seconds") \
        .groupBy(
            window("timestamp", "30 seconds", "10 seconds"),
            col("status")
        ) \
        .agg(
            count("*").alias("count_error"),
            approx_count_distinct("ip").alias("count_distinct_ip"),
            collect_list("url").alias("urls")
        )
    
    alerts = windowed \
        .filter(col("count_error") > 10) \
        .withColumn("alert", lit("Alerte: trop d'erreurs"))
    
    alert_query = alerts \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    errors_as_json= logs \
        .select(to_json(struct("*")).alias("value"))

    error_query = errors_as_json \
        .writeStream \
        .outputMode("append") \
        .format("text") \
        .option("path", "output/errors") \
        .option("checkpointLocation", "checkpoint/errors") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    metrics_query = windowed \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="10 seconds") \
        .start()

    error_query.awaitTermination()
    alert_query.awaitTermination()
    metrics_query.awaitTermination()

if __name__ == "__main__":
    main()