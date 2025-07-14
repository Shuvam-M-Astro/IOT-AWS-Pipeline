#!/usr/bin/env python3
"""
AWS Glue ETL Job for IoT Sensor Data Processing
This job processes raw sensor data and creates structured tables for analytics
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def process_sensor_data():
    """
    Main ETL function to process sensor data
    """
    try:
        logger.info("Starting IoT sensor data ETL job...")
        
        # Read data from S3
        input_path = "s3://iot-sensor-data-bucket/sensor_data/"
        
        # Create DynamicFrame from S3 data
        sensor_dyf = glueContext.create_dynamic_frame.from_options(
            connection_type="s3",
            connection_options={
                "paths": [input_path],
                "recurse": True
            },
            format="json"
        )
        
        logger.info(f"Read {sensor_dyf.count()} records from S3")
        
        # Convert to Spark DataFrame for easier processing
        sensor_df = sensor_dyf.toDF()
        
        # Add processing timestamp
        sensor_df = sensor_df.withColumn("processing_timestamp", current_timestamp())
        
        # Parse timestamp if it exists
        if "timestamp" in sensor_df.columns:
            sensor_df = sensor_df.withColumn(
                "event_timestamp", 
                from_unixtime(col("timestamp"))
            )
        else:
            sensor_df = sensor_df.withColumn("event_timestamp", current_timestamp())
        
        # Add derived features
        sensor_df = sensor_df.withColumn(
            "temp_vib_ratio", 
            col("temperature") / (col("vibration") + 0.001)
        ).withColumn(
            "pressure_temp_ratio", 
            col("pressure") / (col("temperature") + 0.001)
        )
        
        # Add anomaly detection logic
        sensor_df = sensor_df.withColumn(
            "is_anomaly_temp", 
            when(col("temperature") > 80, 1).otherwise(0)
        ).withColumn(
            "is_anomaly_vib", 
            when(col("vibration") > 2.0, 1).otherwise(0)
        ).withColumn(
            "is_anomaly_pressure", 
            when(col("pressure") > 150, 1).otherwise(0)
        ).withColumn(
            "total_anomaly_score", 
            col("is_anomaly_temp") + col("is_anomaly_vib") + col("is_anomaly_pressure")
        )
        
        # Add date partitioning columns
        sensor_df = sensor_df.withColumn(
            "year", year(col("event_timestamp"))
        ).withColumn(
            "month", month(col("event_timestamp"))
        ).withColumn(
            "day", dayofmonth(col("event_timestamp"))
        ).withColumn(
            "hour", hour(col("event_timestamp"))
        )
        
        # Create machine-specific aggregations
        machine_stats = sensor_df.groupBy("machine_id", "year", "month", "day", "hour").agg(
            avg("temperature").alias("avg_temperature"),
            avg("vibration").alias("avg_vibration"),
            avg("pressure").alias("avg_pressure"),
            stddev("temperature").alias("std_temperature"),
            stddev("vibration").alias("std_vibration"),
            stddev("pressure").alias("std_pressure"),
            max("temperature").alias("max_temperature"),
            min("temperature").alias("min_temperature"),
            max("vibration").alias("max_vibration"),
            min("vibration").alias("min_vibration"),
            max("pressure").alias("max_pressure"),
            min("pressure").alias("min_pressure"),
            count("*").alias("record_count"),
            sum("total_anomaly_score").alias("anomaly_count")
        )
        
        # Create time-series features
        window_spec = Window.partitionBy("machine_id").orderBy("event_timestamp")
        
        sensor_df = sensor_df.withColumn(
            "temp_lag_1", lag("temperature", 1).over(window_spec)
        ).withColumn(
            "vib_lag_1", lag("vibration", 1).over(window_spec)
        ).withColumn(
            "pressure_lag_1", lag("pressure", 1).over(window_spec)
        ).withColumn(
            "temp_diff", col("temperature") - col("temp_lag_1")
        ).withColumn(
            "vib_diff", col("vibration") - col("vib_lag_1")
        ).withColumn(
            "pressure_diff", col("pressure") - col("pressure_lag_1")
        )
        
        # Write processed data back to S3
        output_path = "s3://iot-sensor-data-bucket/processed_data/"
        
        # Convert back to DynamicFrame
        processed_dyf = DynamicFrame.fromDF(sensor_df, glueContext, "processed_sensor_data")
        
        # Write with partitioning
        glueContext.write_dynamic_frame.from_options(
            frame=processed_dyf,
            connection_type="s3",
            connection_options={
                "path": output_path,
                "partitionKeys": ["year", "month", "day", "hour"]
            },
            format="parquet"
        )
        
        # Write machine statistics
        machine_stats_dyf = DynamicFrame.fromDF(machine_stats, glueContext, "machine_statistics")
        
        stats_output_path = "s3://iot-sensor-data-bucket/machine_statistics/"
        
        glueContext.write_dynamic_frame.from_options(
            frame=machine_stats_dyf,
            connection_type="s3",
            connection_options={
                "path": stats_output_path,
                "partitionKeys": ["year", "month", "day", "hour"]
            },
            format="parquet"
        )
        
        logger.info("ETL job completed successfully!")
        
        # Return statistics
        return {
            "total_records_processed": sensor_df.count(),
            "unique_machines": sensor_df.select("machine_id").distinct().count(),
            "anomaly_records": sensor_df.filter(col("total_anomaly_score") > 0).count()
        }
        
    except Exception as e:
        logger.error(f"Error in ETL job: {str(e)}")
        raise

def create_analytics_views():
    """
    Create analytics views for common queries
    """
    try:
        logger.info("Creating analytics views...")
        
        # Read processed data
        processed_path = "s3://iot-sensor-data-bucket/processed_data/"
        
        processed_df = spark.read.parquet(processed_path)
        
        # Create temporary view
        processed_df.createOrReplaceTempView("sensor_data")
        
        # Create anomaly summary view
        anomaly_summary = spark.sql("""
            SELECT 
                machine_id,
                year,
                month,
                day,
                COUNT(*) as total_records,
                SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_records,
                AVG(temperature) as avg_temperature,
                AVG(vibration) as avg_vibration,
                AVG(pressure) as avg_pressure,
                MAX(temperature) as max_temperature,
                MIN(temperature) as min_temperature
            FROM sensor_data
            GROUP BY machine_id, year, month, day
            ORDER BY machine_id, year, month, day
        """)
        
        # Write anomaly summary
        anomaly_summary.write.mode("overwrite").parquet(
            "s3://iot-sensor-data-bucket/analytics/anomaly_summary/"
        )
        
        # Create machine performance view
        machine_performance = spark.sql("""
            SELECT 
                machine_id,
                year,
                month,
                AVG(avg_temperature) as monthly_avg_temp,
                AVG(avg_vibration) as monthly_avg_vib,
                AVG(avg_pressure) as monthly_avg_pressure,
                SUM(anomaly_records) as monthly_anomalies,
                SUM(total_records) as monthly_total_records,
                (SUM(anomaly_records) / SUM(total_records)) * 100 as anomaly_percentage
            FROM (
                SELECT 
                    machine_id,
                    year,
                    month,
                    day,
                    COUNT(*) as total_records,
                    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_records,
                    AVG(temperature) as avg_temperature,
                    AVG(vibration) as avg_vibration,
                    AVG(pressure) as avg_pressure
                FROM sensor_data
                GROUP BY machine_id, year, month, day
            )
            GROUP BY machine_id, year, month
            ORDER BY machine_id, year, month
        """)
        
        # Write machine performance
        machine_performance.write.mode("overwrite").parquet(
            "s3://iot-sensor-data-bucket/analytics/machine_performance/"
        )
        
        logger.info("Analytics views created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating analytics views: {str(e)}")
        raise

def main():
    """
    Main function to run the ETL job
    """
    try:
        # Process sensor data
        stats = process_sensor_data()
        logger.info(f"Processing statistics: {stats}")
        
        # Create analytics views
        create_analytics_views()
        
        # Job completed successfully
        job.commit()
        logger.info("ETL job completed and committed successfully!")
        
    except Exception as e:
        logger.error(f"Job failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 