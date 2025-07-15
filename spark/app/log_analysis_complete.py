from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import json
import os

def create_spark_session():
    spark = SparkSession.builder \
        .appName("LogAnalysis") \
        .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark

def connect_to_kafka(spark, kafka_brokers, topic):
    reader = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_brokers) \
        .option("subscribe", topic)

    protocol = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    if protocol != "PLAINTEXT":
        reader = reader.option("kafka.security.protocol", protocol)
        ts = os.getenv("KAFKA_SSL_TRUSTSTORE_LOCATION")
        tsp = os.getenv("KAFKA_SSL_TRUSTSTORE_PASSWORD")
        ks = os.getenv("KAFKA_SSL_KEYSTORE_LOCATION")
        ksp = os.getenv("KAFKA_SSL_KEYSTORE_PASSWORD")
        if ts and tsp:
            reader = reader.option("kafka.ssl.truststore.location", ts)
            reader = reader.option("kafka.ssl.truststore.password", tsp)
        if ks and ksp:
            reader = reader.option("kafka.ssl.keystore.location", ks)
            reader = reader.option("kafka.ssl.keystore.password", ksp)
        mech = os.getenv("KAFKA_SASL_MECHANISM")
        user = os.getenv("KAFKA_USERNAME")
        pwd = os.getenv("KAFKA_PASSWORD")
        if mech and user and pwd:
            reader = reader.option("kafka.sasl.mechanism", mech)
            jaas = f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"{user}\" password=\"{pwd}\";"
            reader = reader.option("kafka.sasl.jaas.config", jaas)

    df = reader.load()
    return df

def parse_logs(df):
    log_regex = r'^(\S+) \S+ \[([^\]]+)\] "(\S+) (\S+) HTTP/\d\.\d" (\d{3})'
    
    parsed = df.select(
        regexp_extract("value", log_regex, 1).alias("ip"),
        regexp_extract("value", log_regex, 2).alias("timestamp"),
        regexp_extract("value", log_regex, 3).alias("method"),
        regexp_extract("value", log_regex, 4).alias("url"),
        regexp_extract("value", log_regex, 5).cast("integer").alias("status")
    )
    
    logs = parsed \
        .withColumn("timestamp", to_timestamp("timestamp", "dd/MMM/yyyy:HH:mm:ss Z"))
        
    return logs

def process_batch(batch_df, batch_id, spark, kafka_brokers, alerts_topic, thresholds):
    if batch_df.isEmpty():
        print(f"Batch {batch_id} is empty, skipping processing.")
        return

    print(f"Processing batch {batch_id} with {batch_df.count()} records.")
    
    total = batch_df.count()
    errors = batch_df.filter(col("status") >= 400).count()
    print(f"Batch {batch_id} - Total requests: {total}, Error requests: {errors}")

    # Alerts configuration
    alerts = []
    alert_timestamp = datetime.now().isoformat()

    # 1) Global error rate
    global_rate = errors / total if total > 0 else 0.0

    if global_rate > thresholds["global"]:
        alerts.append({
            "timestamp": alert_timestamp,
            "type": "GLOBAL_ERROR_RATE",
            "message": f"Global error rate too high: {global_rate:.2%}",
            "batch_id": batch_id,
            "total_requests": total,
            "error_requests": errors,
            "value": global_rate,
            "thresholds": thresholds["global"]
        })

    # 2) URL error rate
    url_stats = batch_df.groupBy("url").agg(
        count("*").alias("total"),
        count(when(col("status") >= 400, 1)).alias("errors")
    ).collect()
    for row in url_stats:
        if row["total"] >= 5:  # Only consider URLs with at least 5 requests
            rate = row["errors"] / row["total"]
            if rate > thresholds["url"]:
                alerts.append({
                    "timestamp": alert_timestamp,
                    "type": "URL_ERROR_RATE",
                    "message": f"Error rate for URL {row['url']} too high: {rate:.2%}",
                    "batch_id": batch_id,
                    "url": row["url"],
                    "total_requests": row["total"],
                    "error_requests": row["errors"],
                    "value": rate,
                    "thresholds": thresholds["url"]
                })

    # 3) User error rate (by IP)
    ip_stats = batch_df.groupBy("ip").agg(
        count("*").alias("total"),
        count(when(col("status") >= 400, 1)).alias("errors")
    ).collect()
    for row in ip_stats:
        if row["total"] >= 3: # At least 3 requests to consider (to avoid false positives)
            rate = row["errors"] / row["total"]
            if rate > thresholds["user"]:
                alerts.append({
                    "timestamp": alert_timestamp,
                    "type": "IP_ERROR_RATE",
                    "message": f"Error rate for IP {row['ip']} too high: {rate:.2%}",
                    "batch_id": batch_id,
                    "ip": row["ip"],
                    "total_requests": row["total"],
                    "error_requests": row["errors"],
                    "value": rate,
                    "thresholds": thresholds["user"]
                })

    # Sending alerts to Kafka
    if alerts:
        print(f"Sending {len(alerts)} generated alerts to Kafka.")
        alerts_df = spark.createDataFrame([(json.dumps(alert),) for alert in alerts], ["value"])
        writer = alerts_df.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", kafka_brokers) \
            .option("topic", alerts_topic)

        protocol = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
        if protocol != "PLAINTEXT":
            writer = writer.option("kafka.security.protocol", protocol)
            ts = os.getenv("KAFKA_SSL_TRUSTSTORE_LOCATION")
            tsp = os.getenv("KAFKA_SSL_TRUSTSTORE_PASSWORD")
            ks = os.getenv("KAFKA_SSL_KEYSTORE_LOCATION")
            ksp = os.getenv("KAFKA_SSL_KEYSTORE_PASSWORD")
            if ts and tsp:
                writer = writer.option("kafka.ssl.truststore.location", ts)
                writer = writer.option("kafka.ssl.truststore.password", tsp)
            if ks and ksp:
                writer = writer.option("kafka.ssl.keystore.location", ks)
                writer = writer.option("kafka.ssl.keystore.password", ksp)
            mech = os.getenv("KAFKA_SASL_MECHANISM")
            user = os.getenv("KAFKA_USERNAME")
            pwd = os.getenv("KAFKA_PASSWORD")
            if mech and user and pwd:
                writer = writer.option("kafka.sasl.mechanism", mech)
                jaas = f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"{user}\" password=\"{pwd}\";"
                writer = writer.option("kafka.sasl.jaas.config", jaas)

        writer.mode("append").save()

def main():
    thresholds = {
        "global": 0.025,  # 2.5% global error rate
        "url": 0.3,     # 30% URL error rate
        "user": 0.4     # 40% user error rate
    }
    # Creating Spark session
    print("Creating Spark session...")
    spark = create_spark_session()
    print("Spark session created.")

    try:
        # Connecting to Kafka
        print("Connecting to kafka...")
        kafka_brokers = os.getenv("KAFKA_BROKER", "kafka:9093")
        read_topic = "http-logs"
        alert_topic = "alerts"
        kafka_df = connect_to_kafka(spark, kafka_brokers, read_topic)
        print(f'Connected to Kafka topic "{read_topic}" on brokers {kafka_brokers}')

        # Parsing the Kafka stream
        print("Parsing logs from Kafka stream...")
        parsed_logs = parse_logs(kafka_df)
        print("Logs parsed successfully.")

        # Streaming configuration
        print("Starting streaming query...")
        query = parsed_logs \
            .writeStream \
            .outputMode("append") \
            .option("checkpointLocation", "/tmp/alerts") \
            .foreachBatch(lambda batch_df, batch_id: process_batch(batch_df, batch_id, spark, kafka_brokers, alert_topic, thresholds )) \
            .start()
        
        print("Streaming query started. Press Ctrl+C to stop.")
        query.awaitTermination()

    except Exception as e:
        print(f"ERROR: {e}")
    except KeyboardInterrupt:
        print("Interrupted by user, exiting...")
    finally:
        print("Stopping Spark session...")
        spark.stop()
        print("Spark session stopped.")

if __name__ == "__main__":
    main()