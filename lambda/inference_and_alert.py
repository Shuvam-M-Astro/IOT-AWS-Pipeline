import boto3
import json
import logging
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
runtime = boto3.client('sagemaker-runtime')
sns = boto3.client('sns')
cloudwatch = boto3.client('cloudwatch')

# Environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Constants
ANOMALY_THRESHOLD = 0.8
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

class AnomalyDetectionError(Exception):
    """Custom exception for anomaly detection errors"""
    pass

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

def validate_sensor_data(data: Dict[str, Any]) -> bool:
    """
    Validate sensor data format and values
    
    Args:
        data: Dictionary containing sensor readings
        
    Returns:
        bool: True if data is valid, False otherwise
        
    Raises:
        DataValidationError: If data is invalid
    """
    required_fields = ['temperature', 'vibration', 'pressure']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            raise DataValidationError(f"Missing required field: {field}")
    
    # Validate data types and ranges
    try:
        temperature = float(data['temperature'])
        vibration = float(data['vibration'])
        pressure = float(data['pressure'])
        
        # Check reasonable ranges for industrial sensors
        if not (0 <= temperature <= 200):
            logger.warning(f"Temperature out of expected range: {temperature}")
        
        if not (0 <= vibration <= 10):
            logger.warning(f"Vibration out of expected range: {vibration}")
            
        if not (0 <= pressure <= 200):
            logger.warning(f"Pressure out of expected range: {pressure}")
            
    except (ValueError, TypeError) as e:
        raise DataValidationError(f"Invalid data type: {e}")
    
    return True

def prepare_features(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare features for ML model inference
    
    Args:
        data: Raw sensor data
        
    Returns:
        Dict containing prepared features
    """
    features = {
        'temperature': float(data['temperature']),
        'vibration': float(data['vibration']),
        'pressure': float(data['pressure'])
    }
    
    # Add derived features
    features['temp_vib_ratio'] = features['temperature'] / (features['vibration'] + 0.001)
    features['pressure_temp_ratio'] = features['pressure'] / (features['temperature'] + 0.001)
    
    return features

def invoke_sagemaker_endpoint(features: Dict[str, Any]) -> int:
    """
    Invoke SageMaker endpoint for anomaly detection
    
    Args:
        features: Prepared feature dictionary
        
    Returns:
        int: Prediction (0 for normal, 1 for anomaly)
        
    Raises:
        AnomalyDetectionError: If inference fails
    """
    try:
        payload = json.dumps(features)
        
        response = runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/json',
            Body=payload
        )
        
        prediction = int(response['Body'].read().decode())
        logger.info(f"SageMaker prediction: {prediction}")
        
        return prediction
        
    except Exception as e:
        logger.error(f"SageMaker inference failed: {str(e)}")
        raise AnomalyDetectionError(f"Inference failed: {str(e)}")

def send_alert(machine_id: str, sensor_data: Dict[str, Any], prediction: int) -> None:
    """
    Send alert via SNS if anomaly is detected
    
    Args:
        machine_id: ID of the machine
        sensor_data: Original sensor data
        prediction: ML model prediction
    """
    if prediction == 1:
        try:
            message = {
                'alert_type': 'anomaly_detected',
                'machine_id': machine_id,
                'timestamp': datetime.utcnow().isoformat(),
                'sensor_data': sensor_data,
                'prediction': prediction,
                'severity': 'high'
            }
            
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps(message, indent=2),
                Subject=f"IoT Anomaly Alert - Machine {machine_id}"
            )
            
            logger.info(f"Alert sent for machine {machine_id}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")

def put_metrics(machine_id: str, sensor_data: Dict[str, Any], prediction: int, duration: float) -> None:
    """
    Put custom metrics to CloudWatch
    
    Args:
        machine_id: ID of the machine
        sensor_data: Sensor data
        prediction: ML prediction
        duration: Processing duration
    """
    try:
        metrics = [
            {
                'MetricName': 'Temperature',
                'Value': float(sensor_data['temperature']),
                'Unit': 'None',
                'Dimensions': [{'Name': 'MachineId', 'Value': machine_id}]
            },
            {
                'MetricName': 'Vibration',
                'Value': float(sensor_data['vibration']),
                'Unit': 'None',
                'Dimensions': [{'Name': 'MachineId', 'Value': machine_id}]
            },
            {
                'MetricName': 'Pressure',
                'Value': float(sensor_data['pressure']),
                'Unit': 'None',
                'Dimensions': [{'Name': 'MachineId', 'Value': machine_id}]
            },
            {
                'MetricName': 'AnomalyPrediction',
                'Value': prediction,
                'Unit': 'None',
                'Dimensions': [{'Name': 'MachineId', 'Value': machine_id}]
            },
            {
                'MetricName': 'ProcessingDuration',
                'Value': duration,
                'Unit': 'Milliseconds',
                'Dimensions': [{'Name': 'MachineId', 'Value': machine_id}]
            }
        ]
        
        cloudwatch.put_metric_data(
            Namespace='IoT/PredictiveMaintenance',
            MetricData=metrics
        )
        
    except Exception as e:
        logger.error(f"Failed to put metrics: {str(e)}")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function
    
    Args:
        event: Kinesis event containing sensor data
        context: Lambda context
        
    Returns:
        Dict containing processing results
    """
    start_time = time.time()
    
    try:
        # Extract record from Kinesis event
        if 'Records' not in event or not event['Records']:
            raise DataValidationError("No records found in event")
        
        record = event['Records'][0]
        
        # Parse the record body
        if 'kinesis' in record:
            # Kinesis record
            payload = json.loads(record['kinesis']['data'].decode('utf-8'))
        else:
            # Direct JSON record
            payload = json.loads(record['body'])
        
        logger.info(f"Processing record: {payload}")
        
        # Extract machine ID and sensor data
        machine_id = payload.get('machine_id', 'unknown')
        sensor_data = {
            'temperature': payload.get('temperature'),
            'vibration': payload.get('vibration'),
            'pressure': payload.get('pressure')
        }
        
        # Validate sensor data
        validate_sensor_data(sensor_data)
        
        # Prepare features for ML model
        features = prepare_features(sensor_data)
        
        # Invoke SageMaker endpoint with retry logic
        prediction = None
        for attempt in range(MAX_RETRIES):
            try:
                prediction = invoke_sagemaker_endpoint(features)
                break
            except AnomalyDetectionError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(RETRY_DELAY * (attempt + 1))
        
        # Send alert if anomaly detected
        send_alert(machine_id, sensor_data, prediction)
        
        # Calculate processing duration
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Put metrics to CloudWatch
        put_metrics(machine_id, sensor_data, prediction, duration)
        
        logger.info(f"Successfully processed record for machine {machine_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'machine_id': machine_id,
                'prediction': prediction,
                'processing_time_ms': duration,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except DataValidationError as e:
        logger.error(f"Data validation error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Data validation failed',
                'message': str(e)
            })
        }
        
    except AnomalyDetectionError as e:
        logger.error(f"Anomaly detection error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Anomaly detection failed',
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
