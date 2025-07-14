#!/usr/bin/env python3
"""
SageMaker Inference Script
Handles model inference for IoT sensor data
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
model = None
scaler = None

def model_fn(model_dir: str):
    """
    Load the model from the model directory
    
    Args:
        model_dir: Directory containing the model files
        
    Returns:
        Loaded model
    """
    global model, scaler
    
    try:
        # Load the model
        model_path = os.path.join(model_dir, 'model.joblib')
        model = joblib.load(model_path)
        logger.info(f"Model loaded successfully from {model_path}")
        
        # Load scaler if it exists
        scaler_path = os.path.join(model_dir, 'scaler.joblib')
        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)
            logger.info("Scaler loaded successfully")
        
        return model
        
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise

def input_fn(request_body: str, content_type: str = 'application/json') -> np.ndarray:
    """
    Parse input data
    
    Args:
        request_body: Request body as string
        content_type: Content type of the request
        
    Returns:
        Parsed input data as numpy array
    """
    try:
        if content_type == 'application/json':
            input_data = json.loads(request_body)
            
            # Extract features
            features = []
            feature_names = ['temperature', 'vibration', 'pressure']
            
            for feature in feature_names:
                if feature in input_data:
                    features.append(float(input_data[feature]))
                else:
                    logger.warning(f"Missing feature: {feature}, using default value 0")
                    features.append(0.0)
            
            # Add derived features
            temp, vib, pressure = features[:3]
            features.append(temp / (vib + 0.001))  # temp_vib_ratio
            features.append(pressure / (temp + 0.001))  # pressure_temp_ratio
            
            return np.array(features).reshape(1, -1)
            
        else:
            raise ValueError(f"Unsupported content type: {content_type}")
            
    except Exception as e:
        logger.error(f"Error parsing input: {str(e)}")
        raise

def predict_fn(input_data: np.ndarray, model) -> np.ndarray:
    """
    Make predictions using the loaded model
    
    Args:
        input_data: Input features as numpy array
        model: Loaded model
        
    Returns:
        Predictions as numpy array
    """
    try:
        # Scale features if scaler is available
        if scaler is not None:
            input_data = scaler.transform(input_data)
        
        # Make prediction
        prediction = model.predict(input_data)
        
        # Get prediction probabilities if available
        try:
            prediction_proba = model.predict_proba(input_data)
            logger.info(f"Prediction: {prediction[0]}, Probability: {prediction_proba[0]}")
        except AttributeError:
            logger.info(f"Prediction: {prediction[0]}")
        
        return prediction
        
    except Exception as e:
        logger.error(f"Error making prediction: {str(e)}")
        raise

def output_fn(prediction: np.ndarray, accept: str = 'application/json') -> str:
    """
    Format the prediction output
    
    Args:
        prediction: Model predictions
        accept: Accept header for response format
        
    Returns:
        Formatted prediction output
    """
    try:
        if accept == 'application/json':
            output = {
                'prediction': int(prediction[0]),
                'prediction_label': 'anomaly' if prediction[0] == 1 else 'normal',
                'confidence': 0.8  # Placeholder confidence score
            }
            return json.dumps(output)
        else:
            return str(prediction[0])
            
    except Exception as e:
        logger.error(f"Error formatting output: {str(e)}")
        raise

def validate_input(input_data: Dict[str, Any]) -> bool:
    """
    Validate input data
    
    Args:
        input_data: Input data dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['temperature', 'vibration', 'pressure']
    
    for field in required_fields:
        if field not in input_data:
            logger.error(f"Missing required field: {field}")
            return False
    
    # Validate data types and ranges
    try:
        temp = float(input_data['temperature'])
        vib = float(input_data['vibration'])
        pressure = float(input_data['pressure'])
        
        # Check reasonable ranges
        if not (0 <= temp <= 200):
            logger.warning(f"Temperature out of expected range: {temp}")
        
        if not (0 <= vib <= 10):
            logger.warning(f"Vibration out of expected range: {vib}")
            
        if not (0 <= pressure <= 200):
            logger.warning(f"Pressure out of expected range: {pressure}")
            
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid data type: {e}")
        return False
    
    return True

def preprocess_features(input_data: Dict[str, Any]) -> np.ndarray:
    """
    Preprocess input features
    
    Args:
        input_data: Raw input data
        
    Returns:
        Preprocessed features as numpy array
    """
    features = [
        float(input_data['temperature']),
        float(input_data['vibration']),
        float(input_data['pressure'])
    ]
    
    # Add derived features
    temp, vib, pressure = features
    features.append(temp / (vib + 0.001))  # temp_vib_ratio
    features.append(pressure / (temp + 0.001))  # pressure_temp_ratio
    
    return np.array(features).reshape(1, -1)

def postprocess_prediction(prediction: int, confidence: float = None) -> Dict[str, Any]:
    """
    Postprocess prediction output
    
    Args:
        prediction: Raw prediction
        confidence: Confidence score
        
    Returns:
        Processed prediction output
    """
    output = {
        'prediction': int(prediction),
        'prediction_label': 'anomaly' if prediction == 1 else 'normal',
        'severity': 'high' if prediction == 1 else 'normal',
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
    if confidence is not None:
        output['confidence'] = confidence
    
    return output

# Main inference function for direct calls
def predict(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main prediction function
    
    Args:
        input_data: Input sensor data
        
    Returns:
        Prediction results
    """
    try:
        # Validate input
        if not validate_input(input_data):
            raise ValueError("Invalid input data")
        
        # Preprocess features
        features = preprocess_features(input_data)
        
        # Make prediction
        prediction = model.predict(features)[0]
        
        # Get confidence if available
        try:
            prediction_proba = model.predict_proba(features)[0]
            confidence = max(prediction_proba)
        except AttributeError:
            confidence = None
        
        # Postprocess output
        result = postprocess_prediction(prediction, confidence)
        
        logger.info(f"Prediction completed: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise

# For backward compatibility
def model_fn(model_dir):
    """Load model for SageMaker"""
    return model_fn(model_dir)

def predict_fn(input_data, model):
    """Make predictions for SageMaker"""
    return predict_fn(input_data, model)

def input_fn(request_body, content_type='application/json'):
    """Parse input for SageMaker"""
    return input_fn(request_body, content_type)

def output_fn(prediction, accept='application/json'):
    """Format output for SageMaker"""
    return output_fn(prediction, accept)
