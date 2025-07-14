#!/usr/bin/env python3
"""
SageMaker Model Training Script
Trains an anomaly detection model for IoT sensor data
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple

# ML libraries
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline

# AWS libraries
import boto3
import sagemaker
from sagemaker.sklearn import SKLearn
from sagemaker.tuner import HyperparameterTuner, IntegerParameter, ContinuousParameter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTrainer:
    """Class to handle model training and deployment"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sagemaker_session = sagemaker.Session()
        self.bucket = self.sagemaker_session.default_bucket()
        self.role = sagemaker.get_execution_role()
        
    def generate_synthetic_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """
        Generate synthetic sensor data for training
        
        Args:
            n_samples: Number of samples to generate
            
        Returns:
            DataFrame with synthetic sensor data
        """
        logger.info(f"Generating {n_samples} synthetic samples...")
        
        np.random.seed(42)
        
        # Generate normal data
        normal_temp = np.random.normal(60, 10, n_samples // 2)
        normal_vib = np.random.normal(1.0, 0.3, n_samples // 2)
        normal_pressure = np.random.normal(100, 15, n_samples // 2)
        
        # Generate anomalous data
        anomaly_temp = np.random.normal(80, 15, n_samples // 2)
        anomaly_vib = np.random.normal(2.5, 0.8, n_samples // 2)
        anomaly_pressure = np.random.normal(150, 25, n_samples // 2)
        
        # Combine data
        data = pd.DataFrame({
            'temperature': np.concatenate([normal_temp, anomaly_temp]),
            'vibration': np.concatenate([normal_vib, anomaly_vib]),
            'pressure': np.concatenate([normal_pressure, anomaly_pressure]),
            'anomaly_score': np.concatenate([
                np.zeros(n_samples // 2),  # Normal
                np.ones(n_samples // 2)    # Anomaly
            ])
        })
        
        # Add derived features
        data['temp_vib_ratio'] = data['temperature'] / (data['vibration'] + 0.001)
        data['pressure_temp_ratio'] = data['pressure'] / (data['temperature'] + 0.001)
        
        # Shuffle data
        data = data.sample(frac=1, random_state=42).reset_index(drop=True)
        
        logger.info(f"Generated data shape: {data.shape}")
        logger.info(f"Anomaly distribution: {data['anomaly_score'].value_counts().to_dict()}")
        
        return data
    
    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare features and labels for training
        
        Args:
            data: Input DataFrame
            
        Returns:
            Tuple of features and labels
        """
        feature_columns = ['temperature', 'vibration', 'pressure', 'temp_vib_ratio', 'pressure_temp_ratio']
        
        X = data[feature_columns].values
        y = data['anomaly_score'].values
        
        return X, y
    
    def train_local_model(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """
        Train model locally for testing
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Dictionary with model and metrics
        """
        logger.info("Training local model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Create pipeline
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', RandomForestClassifier(random_state=42))
        ])
        
        # Define hyperparameters for tuning
        param_grid = {
            'classifier__n_estimators': [50, 100, 200],
            'classifier__max_depth': [10, 20, None],
            'classifier__min_samples_split': [2, 5, 10]
        }
        
        # Grid search
        grid_search = GridSearchCV(
            pipeline, param_grid, cv=5, scoring='roc_auc', n_jobs=-1
        )
        grid_search.fit(X_train, y_train)
        
        # Get best model
        best_model = grid_search.best_estimator_
        
        # Evaluate
        y_pred = best_model.predict(X_test)
        y_pred_proba = best_model.predict_proba(X_test)[:, 1]
        
        metrics = {
            'accuracy': best_model.score(X_test, y_test),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'best_params': grid_search.best_params_,
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        logger.info(f"Local model accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"Local model ROC AUC: {metrics['roc_auc']:.4f}")
        
        return {
            'model': best_model,
            'metrics': metrics,
            'X_test': X_test,
            'y_test': y_test
        }
    
    def train_sagemaker_model(self, data: pd.DataFrame) -> str:
        """
        Train model using SageMaker
        
        Args:
            data: Training data
            
        Returns:
            Model artifact location
        """
        logger.info("Training SageMaker model...")
        
        # Prepare data
        X, y = self.prepare_features(data)
        
        # Save training data
        training_data = pd.DataFrame(X, columns=['temperature', 'vibration', 'pressure', 'temp_vib_ratio', 'pressure_temp_ratio'])
        training_data['anomaly_score'] = y
        
        # Upload to S3
        training_data_path = f"s3://{self.bucket}/iot-training-data/"
        training_data.to_csv('training_data.csv', index=False)
        
        # Upload to S3
        self.sagemaker_session.upload_data(
            path='training_data.csv',
            bucket=self.bucket,
            key_prefix='iot-training-data'
        )
        
        # Create SKLearn estimator
        sklearn_estimator = SKLearn(
            entry_point='train_script.py',
            role=self.role,
            instance_count=1,
            instance_type='ml.m5.large',
            framework_version='0.23-1',
            py_version='py3',
            hyperparameters={
                'n_estimators': 100,
                'max_depth': 20,
                'random_state': 42
            }
        )
        
        # Train model
        sklearn_estimator.fit({
            'train': f"s3://{self.bucket}/iot-training-data/training_data.csv"
        })
        
        logger.info(f"Model training completed. Model location: {sklearn_estimator.model_data}")
        
        return sklearn_estimator.model_data
    
    def deploy_model(self, model_data: str, endpoint_name: str) -> str:
        """
        Deploy model to SageMaker endpoint
        
        Args:
            model_data: S3 location of model artifacts
            endpoint_name: Name for the endpoint
            
        Returns:
            Endpoint name
        """
        logger.info(f"Deploying model to endpoint: {endpoint_name}")
        
        # Create SKLearn model
        sklearn_model = SKLearn(
            model_data=model_data,
            role=self.role,
            entry_point='inference.py',
            framework_version='0.23-1',
            py_version='py3'
        )
        
        # Deploy model
        predictor = sklearn_model.deploy(
            initial_instance_count=1,
            instance_type='ml.t2.medium',
            endpoint_name=endpoint_name
        )
        
        logger.info(f"Model deployed successfully to endpoint: {endpoint_name}")
        
        return endpoint_name
    
    def evaluate_model(self, model: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
        """
        Evaluate model performance
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info("Evaluating model...")
        
        # Make predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        metrics = {
            'accuracy': model.score(X_test, y_test),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
        }
        
        logger.info(f"Model Accuracy: {metrics['accuracy']:.4f}")
        logger.info(f"Model ROC AUC: {metrics['roc_auc']:.4f}")
        
        return metrics
    
    def save_model(self, model: Any, model_path: str) -> None:
        """
        Save model to local file system
        
        Args:
            model: Trained model
            model_path: Path to save model
        """
        import joblib
        
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(model, model_path)
        logger.info(f"Model saved to: {model_path}")
    
    def run_training_pipeline(self) -> Dict[str, Any]:
        """
        Run complete training pipeline
        
        Returns:
            Dictionary with training results
        """
        logger.info("Starting training pipeline...")
        
        # Generate data
        data = self.generate_synthetic_data(n_samples=10000)
        
        # Prepare features
        X, y = self.prepare_features(data)
        
        # Train local model
        local_results = self.train_local_model(X, y)
        
        # Save local model
        model_path = os.path.join(self.config.get('model_dir', 'models'), 'anomaly_detection_model.joblib')
        self.save_model(local_results['model'], model_path)
        
        # Train SageMaker model if specified
        sagemaker_model_data = None
        if self.config.get('train_sagemaker', False):
            sagemaker_model_data = self.train_sagemaker_model(data)
        
        # Deploy model if specified
        endpoint_name = None
        if self.config.get('deploy_model', False) and sagemaker_model_data:
            endpoint_name = self.deploy_model(
                sagemaker_model_data,
                self.config.get('endpoint_name', 'sensor-anomaly-endpoint')
            )
        
        return {
            'local_model_path': model_path,
            'local_metrics': local_results['metrics'],
            'sagemaker_model_data': sagemaker_model_data,
            'endpoint_name': endpoint_name,
            'training_data_shape': data.shape
        }

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Train anomaly detection model')
    parser.add_argument('--config', type=str, default='config.json', help='Configuration file')
    parser.add_argument('--model-dir', type=str, default='models', help='Directory to save models')
    parser.add_argument('--train-sagemaker', action='store_true', help='Train SageMaker model')
    parser.add_argument('--deploy-model', action='store_true', help='Deploy model to endpoint')
    parser.add_argument('--endpoint-name', type=str, default='sensor-anomaly-endpoint', help='SageMaker endpoint name')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Update config with command line arguments
    config.update(vars(args))
    
    # Create model directory
    os.makedirs(args.model_dir, exist_ok=True)
    
    # Initialize trainer
    trainer = ModelTrainer(config)
    
    # Run training pipeline
    results = trainer.run_training_pipeline()
    
    # Save results
    results_path = os.path.join(args.model_dir, 'training_results.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info(f"Training completed. Results saved to: {results_path}")
    logger.info(f"Model saved to: {results['local_model_path']}")
    
    if results['endpoint_name']:
        logger.info(f"Model deployed to endpoint: {results['endpoint_name']}")

if __name__ == "__main__":
    main()
