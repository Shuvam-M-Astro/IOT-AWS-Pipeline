#!/bin/bash

# Lambda Deployment Script
# This script packages and deploys Lambda functions to AWS

set -e

# Configuration
FUNCTION_NAME="iot-pipeline-inference-alert"
REGION="eu-central-1"
RUNTIME="python3.9"
HANDLER="inference_and_alert.lambda_handler"
TIMEOUT=30
MEMORY_SIZE=256

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
fi

# Create deployment package
print_status "Creating deployment package..."

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
PACKAGE_DIR="$TEMP_DIR/package"

mkdir -p "$PACKAGE_DIR"

# Copy Lambda function files
cp inference_and_alert.py "$PACKAGE_DIR/"
cp data_transformer.py "$PACKAGE_DIR/"

# Create requirements.txt if it doesn't exist
if [ ! -f requirements.txt ]; then
    print_status "Creating requirements.txt..."
    cat > requirements.txt << EOF
boto3>=1.26.0
botocore>=1.29.0
EOF
fi

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt -t "$PACKAGE_DIR/" --quiet

# Create ZIP file
print_status "Creating ZIP file..."
cd "$PACKAGE_DIR"
zip -r ../lambda_function.zip . > /dev/null
cd - > /dev/null

# Check if function exists
FUNCTION_EXISTS=$(aws lambda list-functions --region "$REGION" --query "Functions[?FunctionName=='$FUNCTION_NAME'].FunctionName" --output text)

if [ "$FUNCTION_EXISTS" = "$FUNCTION_NAME" ]; then
    print_status "Updating existing Lambda function..."
    
    # Update function code
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$TEMP_DIR/lambda_function.zip" \
        --region "$REGION"
    
    # Update function configuration
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY_SIZE" \
        --region "$REGION"
        
    print_status "Lambda function updated successfully!"
    
else
    print_status "Creating new Lambda function..."
    
    # Create function
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime "$RUNTIME" \
        --role "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/iot-pipeline-lambda-role" \
        --handler "$HANDLER" \
        --zip-file "fileb://$TEMP_DIR/lambda_function.zip" \
        --timeout "$TIMEOUT" \
        --memory-size "$MEMORY_SIZE" \
        --region "$REGION" \
        --environment Variables='{SNS_TOPIC_ARN="arn:aws:sns:eu-central-1:'$(aws sts get-caller-identity --query Account --output text)':iot-alerts",SAGEMAKER_ENDPOINT="sensor-anomaly-endpoint",LOG_LEVEL="INFO"}'
        
    print_status "Lambda function created successfully!"
fi

# Clean up
rm -rf "$TEMP_DIR"

print_status "Deployment completed successfully!"

# Display function information
print_status "Function details:"
aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.{FunctionName:FunctionName,FunctionArn:FunctionArn,Runtime:Runtime,Handler:Handler,Timeout:Timeout,MemorySize:MemorySize}' --output table

print_status "You can now test the function or check CloudWatch logs for execution details." 