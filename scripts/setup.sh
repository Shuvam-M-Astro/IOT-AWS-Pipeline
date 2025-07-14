#!/bin/bash

# IoT Pipeline Setup Script
# This script sets up the complete IoT data pipeline infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Configuration
PROJECT_NAME="iot-pipeline"
REGION="eu-central-1"
ENVIRONMENT="dev"

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check if pip is installed
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials are not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_status "All prerequisites are satisfied!"
}

# Install Python dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python packages..."
    pip install --upgrade pip
    pip install boto3 sagemaker pandas numpy scikit-learn paho-mqtt
    
    print_status "Python dependencies installed successfully!"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying Infrastructure"
    
    cd terraform
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    print_status "Planning deployment..."
    terraform plan -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT"
    
    # Deploy infrastructure
    print_status "Deploying infrastructure..."
    terraform apply -var="project_name=$PROJECT_NAME" -var="environment=$ENVIRONMENT" -auto-approve
    
    # Get outputs
    print_status "Getting infrastructure outputs..."
    terraform output -json > ../infrastructure_outputs.json
    
    cd ..
    
    print_status "Infrastructure deployed successfully!"
}

# Deploy Lambda functions
deploy_lambda() {
    print_header "Deploying Lambda Functions"
    
    cd lambda
    
    # Make deploy script executable
    chmod +x deploy.sh
    
    # Deploy Lambda functions
    print_status "Deploying Lambda functions..."
    ./deploy.sh
    
    cd ..
    
    print_status "Lambda functions deployed successfully!"
}

# Train and deploy ML model
deploy_model() {
    print_header "Training and Deploying ML Model"
    
    cd sagemaker
    
    # Create models directory
    mkdir -p models
    
    # Train model locally
    print_status "Training ML model..."
    python3 train_model.py --model-dir models
    
    # Deploy model to SageMaker (optional)
    if [ "$DEPLOY_SAGEMAKER" = "true" ]; then
        print_status "Deploying model to SageMaker..."
        python3 train_model.py --train-sagemaker --deploy-model --endpoint-name sensor-anomaly-endpoint
    fi
    
    cd ..
    
    print_status "ML model training completed!"
}

# Setup IoT certificates
setup_iot_certificates() {
    print_header "Setting up IoT Certificates"
    
    cd sensor_simulator
    
    # Create certificates directory
    mkdir -p certificates
    
    # Generate IoT certificates (this would typically be done through AWS IoT Core console)
    print_warning "IoT certificates need to be created manually through AWS IoT Core console"
    print_status "Please create certificates and download them to sensor_simulator/certificates/"
    
    cd ..
}

# Configure sensor simulator
configure_simulator() {
    print_header "Configuring Sensor Simulator"
    
    cd sensor_simulator
    
    # Create requirements.txt
    cat > requirements.txt << EOF
paho-mqtt>=1.6.1
boto3>=1.26.0
requests>=2.28.0
EOF
    
    # Create configuration file
    cat > config.json << EOF
{
    "aws_region": "$REGION",
    "iot_endpoint": "YOUR_IOT_ENDPOINT",
    "topic": "factory/machine1/data",
    "client_id": "sensor-device-01",
    "certificate_path": "./certificates/device-certificate.pem.crt",
    "private_key_path": "./certificates/private.pem.key",
    "ca_certificate_path": "./certificates/AmazonRootCA1.pem",
    "publish_interval": 5
}
EOF
    
    print_status "Sensor simulator configured!"
    print_warning "Please update config.json with your IoT endpoint and certificate paths"
    
    cd ..
}

# Create monitoring dashboard
create_dashboard() {
    print_header "Creating CloudWatch Dashboard"
    
    # Create dashboard using AWS CLI
    aws cloudwatch put-dashboard \
        --dashboard-name "$PROJECT_NAME-dashboard" \
        --dashboard-body file://monitoring/dashboard.json \
        --region "$REGION"
    
    print_status "CloudWatch dashboard created successfully!"
}

# Setup Glue crawler
setup_glue_crawler() {
    print_header "Setting up Glue Crawler"
    
    # Start the crawler
    aws glue start-crawler --name "$PROJECT_NAME-crawler" --region "$REGION"
    
    print_status "Glue crawler started successfully!"
}

# Create test data
create_test_data() {
    print_header "Creating Test Data"
    
    cd sagemaker
    
    # Generate synthetic training data
    python3 -c "
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Generate synthetic data
np.random.seed(42)
n_samples = 1000

data = pd.DataFrame({
    'machine_id': np.random.choice(['MCH001', 'MCH002', 'MCH003'], n_samples),
    'temperature': np.random.normal(60, 10, n_samples),
    'vibration': np.random.normal(1.0, 0.3, n_samples),
    'pressure': np.random.normal(100, 15, n_samples),
    'timestamp': [datetime.now() - timedelta(seconds=i) for i in range(n_samples)]
})

# Add some anomalies
anomaly_indices = np.random.choice(n_samples, 50, replace=False)
data.loc[anomaly_indices, 'temperature'] += 30
data.loc[anomaly_indices, 'vibration'] += 2

data.to_csv('training_data.csv', index=False)
print('Test data created: training_data.csv')
"
    
    cd ..
    
    print_status "Test data created successfully!"
}

# Run tests
run_tests() {
    print_header "Running Tests"
    
    # Check if tests directory exists
    if [ -d "tests" ]; then
        cd tests
        
        # Run unit tests
        if [ -d "unit" ]; then
            print_status "Running unit tests..."
            python -m pytest unit/ -v
        fi
        
        # Run integration tests
        if [ -d "integration" ]; then
            print_status "Running integration tests..."
            python -m pytest integration/ -v
        fi
        
        cd ..
    else
        print_warning "Tests directory not found. Skipping tests."
    fi
    
    print_status "Tests completed!"
}

# Display setup summary
display_summary() {
    print_header "Setup Summary"
    
    echo "✅ Infrastructure deployed"
    echo "✅ Lambda functions deployed"
    echo "✅ ML model trained"
    echo "✅ CloudWatch dashboard created"
    echo "✅ Glue crawler configured"
    echo "✅ Test data created"
    
    echo ""
    echo "Next steps:"
    echo "1. Update sensor_simulator/config.json with your IoT endpoint"
    echo "2. Download IoT certificates to sensor_simulator/certificates/"
    echo "3. Start the sensor simulator: cd sensor_simulator && python sensor_simulator.py"
    echo "4. Monitor the pipeline in CloudWatch dashboard"
    echo "5. Query data using Athena"
    
    echo ""
    echo "Useful commands:"
    echo "- View logs: aws logs tail /aws/lambda/iot-pipeline-inference-alert"
    echo "- Query data: aws athena start-query-execution --query-string 'SELECT * FROM sensor_data LIMIT 10'"
    echo "- Monitor costs: aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost"
}

# Main setup function
main() {
    print_header "IoT Pipeline Setup"
    
    # Parse command line arguments
    DEPLOY_SAGEMAKER=${1:-false}
    
    # Run setup steps
    check_prerequisites
    install_dependencies
    deploy_infrastructure
    deploy_lambda
    deploy_model
    setup_iot_certificates
    configure_simulator
    create_dashboard
    setup_glue_crawler
    create_test_data
    run_tests
    display_summary
    
    print_status "Setup completed successfully!"
}

# Run main function
main "$@" 