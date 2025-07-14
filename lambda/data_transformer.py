import boto3
import json
import logging
import os
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import statistics

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
kinesis = boto3.client('kinesis')
firehose = boto3.client('firehose')

# Environment variables
KINESIS_STREAM_NAME = os.environ.get('KINESIS_STREAM_NAME')
FIREHOSE_STREAM_NAME = os.environ.get('FIREHOSE_STREAM_NAME')

class DataTransformationError(Exception):
    """Custom exception for data transformation errors"""
    pass

def calculate_statistical_features(sensor_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate statistical features from sensor data
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        Dict containing statistical features
    """
    if not sensor_data:
        return {}
    
    temperatures = [float(reading['temperature']) for reading in sensor_data]
    vibrations = [float(reading['vibration']) for reading in sensor_data]
    pressures = [float(reading['pressure']) for reading in sensor_data]
    
    features = {
        'temp_mean': statistics.mean(temperatures),
        'temp_std': statistics.stdev(temperatures) if len(temperatures) > 1 else 0,
        'temp_min': min(temperatures),
        'temp_max': max(temperatures),
        'vib_mean': statistics.mean(vibrations),
        'vib_std': statistics.stdev(vibrations) if len(vibrations) > 1 else 0,
        'vib_min': min(vibrations),
        'vib_max': max(vibrations),
        'pressure_mean': statistics.mean(pressures),
        'pressure_std': statistics.stdev(pressures) if len(pressures) > 1 else 0,
        'pressure_min': min(pressures),
        'pressure_max': max(pressures)
    }
    
    return features

def detect_trends(sensor_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Detect trends in sensor data
    
    Args:
        sensor_data: List of sensor readings
        
    Returns:
        Dict containing trend information
    """
    if len(sensor_data) < 3:
        return {'trend': 'insufficient_data'}
    
    temperatures = [float(reading['temperature']) for reading in sensor_data]
    vibrations = [float(reading['vibration']) for reading in sensor_data]
    pressures = [float(reading['pressure']) for reading in sensor_data]
    
    trends = {}
    
    # Temperature trend
    if temperatures[-1] > temperatures[0] + 5:
        trends['temp_trend'] = 'increasing'
    elif temperatures[-1] < temperatures[0] - 5:
        trends['temp_trend'] = 'decreasing'
    else:
        trends['temp_trend'] = 'stable'
    
    # Vibration trend
    if vibrations[-1] > vibrations[0] + 0.5:
        trends['vib_trend'] = 'increasing'
    elif vibrations[-1] < vibrations[0] - 0.5:
        trends['vib_trend'] = 'decreasing'
    else:
        trends['vib_trend'] = 'stable'
    
    # Pressure trend
    if pressures[-1] > pressures[0] + 10:
        trends['pressure_trend'] = 'increasing'
    elif pressures[-1] < pressures[0] - 10:
        trends['pressure_trend'] = 'decreasing'
    else:
        trends['pressure_trend'] = 'stable'
    
    return trends

def enrich_sensor_data(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich sensor data with additional metadata and derived features
    
    Args:
        record: Original sensor record
        
    Returns:
        Enriched sensor record
    """
    enriched = record.copy()
    
    # Add timestamp if not present
    if 'timestamp' not in enriched:
        enriched['timestamp'] = int(time.time())
    
    # Add derived features
    enriched['temp_vib_ratio'] = float(enriched['temperature']) / (float(enriched['vibration']) + 0.001)
    enriched['pressure_temp_ratio'] = float(enriched['pressure']) / (float(enriched['temperature']) + 0.001)
    
    # Add metadata
    enriched['processed_at'] = datetime.utcnow().isoformat()
    enriched['data_version'] = '1.0'
    
    return enriched

def validate_transformed_data(data: Dict[str, Any]) -> bool:
    """
    Validate transformed data
    
    Args:
        data: Transformed data record
        
    Returns:
        bool: True if valid
        
    Raises:
        DataTransformationError: If data is invalid
    """
    required_fields = ['machine_id', 'temperature', 'vibration', 'pressure', 'timestamp']
    
    for field in required_fields:
        if field not in data:
            raise DataTransformationError(f"Missing required field: {field}")
    
    # Validate data types
    try:
        float(data['temperature'])
        float(data['vibration'])
        float(data['pressure'])
        int(data['timestamp'])
    except (ValueError, TypeError) as e:
        raise DataTransformationError(f"Invalid data type: {e}")
    
    return True

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for data transformation
    
    Args:
        event: Kinesis event containing sensor data
        context: Lambda context
        
    Returns:
        Dict containing transformation results
    """
    start_time = time.time()
    
    try:
        # Extract records from Kinesis event
        if 'Records' not in event or not event['Records']:
            raise DataTransformationError("No records found in event")
        
        processed_records = []
        
        for record in event['Records']:
            try:
                # Parse the record
                if 'kinesis' in record:
                    payload = json.loads(record['kinesis']['data'].decode('utf-8'))
                else:
                    payload = json.loads(record['body'])
                
                logger.info(f"Processing record: {payload}")
                
                # Enrich the data
                enriched_data = enrich_sensor_data(payload)
                
                # Validate transformed data
                validate_transformed_data(enriched_data)
                
                processed_records.append(enriched_data)
                
            except Exception as e:
                logger.error(f"Failed to process record: {str(e)}")
                continue
        
        if not processed_records:
            raise DataTransformationError("No records were successfully processed")
        
        # Calculate statistical features if we have multiple records
        if len(processed_records) > 1:
            stats_features = calculate_statistical_features(processed_records)
            trends = detect_trends(processed_records)
            
            # Add statistical features to the latest record
            latest_record = processed_records[-1]
            latest_record.update(stats_features)
            latest_record.update(trends)
        
        # Send to Kinesis for real-time processing
        for record in processed_records:
            try:
                kinesis.put_record(
                    StreamName=KINESIS_STREAM_NAME,
                    Data=json.dumps(record),
                    PartitionKey=record['machine_id']
                )
            except Exception as e:
                logger.error(f"Failed to send to Kinesis: {str(e)}")
        
        # Send to Firehose for batch processing
        for record in processed_records:
            try:
                firehose.put_record(
                    DeliveryStreamName=FIREHOSE_STREAM_NAME,
                    Record={'Data': json.dumps(record)}
                )
            except Exception as e:
                logger.error(f"Failed to send to Firehose: {str(e)}")
        
        duration = (time.time() - start_time) * 1000
        
        logger.info(f"Successfully processed {len(processed_records)} records in {duration:.2f}ms")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed_records': len(processed_records),
                'processing_time_ms': duration,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except DataTransformationError as e:
        logger.error(f"Data transformation error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Data transformation failed',
                'message': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        } 