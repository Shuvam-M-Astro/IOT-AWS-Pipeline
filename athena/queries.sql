-- IoT Sensor Data Analytics Queries
-- This file contains SQL queries for analyzing IoT sensor data using Athena

-- ============================================================================
-- SETUP AND CONFIGURATION
-- ============================================================================

-- Set workgroup for queries
SET workgroup = 'iot-pipeline-workgroup';

-- ============================================================================
-- BASIC DATA EXPLORATION QUERIES
-- ============================================================================

-- 1. Recent sensor readings (last 24 hours)
SELECT 
    machine_id,
    temperature,
    vibration,
    pressure,
    event_timestamp,
    total_anomaly_score
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '24' HOUR
ORDER BY event_timestamp DESC
LIMIT 100;

-- 2. Machine performance summary
SELECT 
    machine_id,
    COUNT(*) as total_readings,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    MAX(temperature) as max_temperature,
    MIN(temperature) as min_temperature,
    STDDEV(temperature) as temp_std_dev
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id
ORDER BY avg_temperature DESC;

-- ============================================================================
-- ANOMALY DETECTION QUERIES
-- ============================================================================

-- 3. Recent anomalies
SELECT 
    machine_id,
    temperature,
    vibration,
    pressure,
    total_anomaly_score,
    event_timestamp,
    CASE 
        WHEN total_anomaly_score >= 3 THEN 'CRITICAL'
        WHEN total_anomaly_score >= 2 THEN 'HIGH'
        WHEN total_anomaly_score >= 1 THEN 'MEDIUM'
        ELSE 'NORMAL'
    END as severity_level
FROM sensor_data 
WHERE total_anomaly_score > 0 
    AND event_timestamp >= NOW() - INTERVAL '24' HOUR
ORDER BY event_timestamp DESC;

-- 4. Anomaly trends by machine
SELECT 
    machine_id,
    DATE(event_timestamp) as date,
    COUNT(*) as total_readings,
    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_count,
    (SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as anomaly_percentage
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '30' DAY
GROUP BY machine_id, DATE(event_timestamp)
ORDER BY machine_id, date;

-- 5. Temperature anomalies by hour
SELECT 
    machine_id,
    EXTRACT(HOUR FROM event_timestamp) as hour_of_day,
    COUNT(*) as total_readings,
    SUM(CASE WHEN temperature > 80 THEN 1 ELSE 0 END) as high_temp_count,
    AVG(temperature) as avg_temperature,
    MAX(temperature) as max_temperature
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id, EXTRACT(HOUR FROM event_timestamp)
ORDER BY machine_id, hour_of_day;

-- ============================================================================
-- TIME SERIES ANALYSIS
-- ============================================================================

-- 6. Hourly averages for the last week
SELECT 
    machine_id,
    DATE(event_timestamp) as date,
    EXTRACT(HOUR FROM event_timestamp) as hour,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    COUNT(*) as reading_count
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id, DATE(event_timestamp), EXTRACT(HOUR FROM event_timestamp)
ORDER BY machine_id, date, hour;

-- 7. Daily trends
SELECT 
    machine_id,
    DATE(event_timestamp) as date,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    STDDEV(temperature) as temp_volatility,
    COUNT(*) as daily_readings
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '30' DAY
GROUP BY machine_id, DATE(event_timestamp)
ORDER BY machine_id, date;

-- ============================================================================
-- MACHINE COMPARISON QUERIES
-- ============================================================================

-- 8. Machine performance comparison
WITH machine_stats AS (
    SELECT 
        machine_id,
        AVG(temperature) as avg_temp,
        AVG(vibration) as avg_vib,
        AVG(pressure) as avg_pressure,
        STDDEV(temperature) as temp_std,
        COUNT(*) as total_readings,
        SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_count
    FROM sensor_data 
    WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
    GROUP BY machine_id
)
SELECT 
    machine_id,
    avg_temp,
    avg_vib,
    avg_pressure,
    temp_std,
    total_readings,
    anomaly_count,
    (anomaly_count * 100.0 / total_readings) as anomaly_rate
FROM machine_stats
ORDER BY anomaly_rate DESC;

-- 9. Machine efficiency ranking
SELECT 
    machine_id,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    COUNT(*) as total_readings,
    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_count,
    CASE 
        WHEN AVG(temperature) < 60 AND AVG(vibration) < 1.5 AND AVG(pressure) < 120 THEN 'EXCELLENT'
        WHEN AVG(temperature) < 70 AND AVG(vibration) < 2.0 AND AVG(pressure) < 140 THEN 'GOOD'
        WHEN AVG(temperature) < 80 AND AVG(vibration) < 2.5 AND AVG(pressure) < 160 THEN 'FAIR'
        ELSE 'POOR'
    END as efficiency_rating
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id
ORDER BY efficiency_rating, avg_temperature;

-- ============================================================================
-- PREDICTIVE MAINTENANCE QUERIES
-- ============================================================================

-- 10. Machines requiring attention
SELECT 
    machine_id,
    COUNT(*) as total_readings,
    SUM(CASE WHEN total_anomaly_score >= 2 THEN 1 ELSE 0 END) as critical_anomalies,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    MAX(temperature) as max_temperature,
    MAX(vibration) as max_vibration,
    MAX(pressure) as max_pressure
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '24' HOUR
GROUP BY machine_id
HAVING SUM(CASE WHEN total_anomaly_score >= 2 THEN 1 ELSE 0 END) > 0
ORDER BY critical_anomalies DESC;

-- 11. Trend analysis for predictive maintenance
SELECT 
    machine_id,
    DATE(event_timestamp) as date,
    AVG(temperature) as avg_temp,
    AVG(vibration) as avg_vib,
    AVG(pressure) as avg_pressure,
    LAG(AVG(temperature), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp)) as prev_avg_temp,
    LAG(AVG(vibration), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp)) as prev_avg_vib,
    LAG(AVG(pressure), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp)) as prev_avg_pressure,
    (AVG(temperature) - LAG(AVG(temperature), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp))) as temp_trend,
    (AVG(vibration) - LAG(AVG(vibration), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp))) as vib_trend,
    (AVG(pressure) - LAG(AVG(pressure), 1) OVER (PARTITION BY machine_id ORDER BY DATE(event_timestamp))) as pressure_trend
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '14' DAY
GROUP BY machine_id, DATE(event_timestamp)
ORDER BY machine_id, date;

-- ============================================================================
-- OPERATIONAL INTELLIGENCE QUERIES
-- ============================================================================

-- 12. Peak usage hours
SELECT 
    EXTRACT(HOUR FROM event_timestamp) as hour_of_day,
    COUNT(*) as total_readings,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_count
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY EXTRACT(HOUR FROM event_timestamp)
ORDER BY total_readings DESC;

-- 13. Weekly performance summary
SELECT 
    machine_id,
    DATE_TRUNC('week', event_timestamp) as week_start,
    COUNT(*) as weekly_readings,
    AVG(temperature) as weekly_avg_temp,
    AVG(vibration) as weekly_avg_vib,
    AVG(pressure) as weekly_avg_pressure,
    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as weekly_anomalies,
    (SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as weekly_anomaly_rate
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '8' WEEK
GROUP BY machine_id, DATE_TRUNC('week', event_timestamp)
ORDER BY machine_id, week_start;

-- ============================================================================
-- DATA QUALITY QUERIES
-- ============================================================================

-- 14. Data completeness check
SELECT 
    machine_id,
    COUNT(*) as total_records,
    COUNT(temperature) as temp_records,
    COUNT(vibration) as vib_records,
    COUNT(pressure) as pressure_records,
    (COUNT(temperature) * 100.0 / COUNT(*)) as temp_completeness,
    (COUNT(vibration) * 100.0 / COUNT(*)) as vib_completeness,
    (COUNT(pressure) * 100.0 / COUNT(*)) as pressure_completeness
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id
ORDER BY machine_id;

-- 15. Outlier detection
SELECT 
    machine_id,
    temperature,
    vibration,
    pressure,
    event_timestamp,
    CASE 
        WHEN temperature > 100 OR temperature < 20 THEN 'TEMPERATURE_OUTLIER'
        WHEN vibration > 5 OR vibration < 0 THEN 'VIBRATION_OUTLIER'
        WHEN pressure > 200 OR pressure < 50 THEN 'PRESSURE_OUTLIER'
        ELSE 'NORMAL'
    END as outlier_type
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '24' HOUR
    AND (temperature > 100 OR temperature < 20 
         OR vibration > 5 OR vibration < 0 
         OR pressure > 200 OR pressure < 50)
ORDER BY event_timestamp DESC;

-- ============================================================================
-- COST OPTIMIZATION QUERIES
-- ============================================================================

-- 16. Energy efficiency analysis
SELECT 
    machine_id,
    AVG(temperature) as avg_temperature,
    AVG(vibration) as avg_vibration,
    AVG(pressure) as avg_pressure,
    COUNT(*) as total_readings,
    SUM(CASE WHEN total_anomaly_score > 0 THEN 1 ELSE 0 END) as anomaly_count,
    CASE 
        WHEN AVG(temperature) < 65 AND AVG(vibration) < 1.5 THEN 'ENERGY_EFFICIENT'
        WHEN AVG(temperature) < 75 AND AVG(vibration) < 2.0 THEN 'MODERATE_EFFICIENCY'
        ELSE 'HIGH_ENERGY_USAGE'
    END as efficiency_category
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
GROUP BY machine_id
ORDER BY efficiency_category, avg_temperature;

-- ============================================================================
-- ALERTING QUERIES
-- ============================================================================

-- 17. Current alert status
SELECT 
    machine_id,
    temperature,
    vibration,
    pressure,
    total_anomaly_score,
    event_timestamp,
    CASE 
        WHEN total_anomaly_score >= 3 THEN 'CRITICAL_ALERT'
        WHEN total_anomaly_score >= 2 THEN 'HIGH_ALERT'
        WHEN total_anomaly_score >= 1 THEN 'MEDIUM_ALERT'
        ELSE 'NORMAL'
    END as alert_level
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '1' HOUR
    AND total_anomaly_score > 0
ORDER BY total_anomaly_score DESC, event_timestamp DESC;

-- 18. Alert frequency by machine
SELECT 
    machine_id,
    COUNT(*) as total_alerts,
    COUNT(CASE WHEN total_anomaly_score >= 3 THEN 1 END) as critical_alerts,
    COUNT(CASE WHEN total_anomaly_score = 2 THEN 1 END) as high_alerts,
    COUNT(CASE WHEN total_anomaly_score = 1 THEN 1 END) as medium_alerts,
    MAX(event_timestamp) as last_alert_time
FROM sensor_data 
WHERE event_timestamp >= NOW() - INTERVAL '7' DAY
    AND total_anomaly_score > 0
GROUP BY machine_id
ORDER BY total_alerts DESC; 