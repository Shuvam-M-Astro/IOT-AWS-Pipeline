#!/bin/bash

# IoT Pipeline Cleanup Script
# This script removes all AWS resources created by the IoT pipeline

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

# Check if user wants to proceed
confirm_cleanup() {
    print_warning "This will delete ALL AWS resources created by the IoT pipeline!"
    print_warning "This action cannot be undone!"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        print_status "Cleanup cancelled."
        exit 0
    fi
}

# Delete SageMaker endpoints
delete_sagemaker_endpoints() {
    print_header "Deleting SageMaker Endpoints"
    
    # List endpoints
    ENDPOINTS=$(aws sagemaker list-endpoints --region "$REGION" --query 'Endpoints[?contains(EndpointName, `sensor-anomaly-endpoint`)].EndpointName' --output text)
    
    for endpoint in $ENDPOINTS; do
        if [ ! -z "$endpoint" ]; then
            print_status "Deleting endpoint: $endpoint"
            aws sagemaker delete-endpoint --endpoint-name "$endpoint" --region "$REGION"
        fi
    done
    
    print_status "SageMaker endpoints deleted successfully!"
}

# Delete Lambda functions
delete_lambda_functions() {
    print_header "Deleting Lambda Functions"
    
    # List Lambda functions
    FUNCTIONS=$(aws lambda list-functions --region "$REGION" --query 'Functions[?contains(FunctionName, `iot-pipeline`)].FunctionName' --output text)
    
    for function in $FUNCTIONS; do
        if [ ! -z "$function" ]; then
            print_status "Deleting Lambda function: $function"
            aws lambda delete-function --function-name "$function" --region "$REGION"
        fi
    done
    
    print_status "Lambda functions deleted successfully!"
}

# Delete Kinesis streams
delete_kinesis_streams() {
    print_header "Deleting Kinesis Streams"
    
    # List streams
    STREAMS=$(aws kinesis list-streams --region "$REGION" --query 'StreamNames[?contains(@, `iot-sensor-stream`)]' --output text)
    
    for stream in $STREAMS; do
        if [ ! -z "$stream" ]; then
            print_status "Deleting Kinesis stream: $stream"
            aws kinesis delete-stream --stream-name "$stream" --region "$REGION"
        fi
    done
    
    print_status "Kinesis streams deleted successfully!"
}

# Delete Firehose delivery streams
delete_firehose_streams() {
    print_header "Deleting Kinesis Firehose Streams"
    
    # List delivery streams
    STREAMS=$(aws firehose list-delivery-streams --region "$REGION" --query 'DeliveryStreamNames[?contains(@, `iot-pipeline`)]' --output text)
    
    for stream in $STREAMS; do
        if [ ! -z "$stream" ]; then
            print_status "Deleting Firehose stream: $stream"
            aws firehose delete-delivery-stream --delivery-stream-name "$stream" --region "$REGION"
        fi
    done
    
    print_status "Firehose streams deleted successfully!"
}

# Delete S3 buckets
delete_s3_buckets() {
    print_header "Deleting S3 Buckets"
    
    # List buckets
    BUCKETS=$(aws s3 ls --region "$REGION" | grep iot-sensor-data-bucket | awk '{print $3}')
    
    for bucket in $BUCKETS; do
        if [ ! -z "$bucket" ]; then
            print_status "Deleting S3 bucket: $bucket"
            
            # Delete all objects in bucket
            aws s3 rm s3://"$bucket" --recursive --region "$REGION"
            
            # Delete bucket
            aws s3 rb s3://"$bucket" --region "$REGION"
        fi
    done
    
    print_status "S3 buckets deleted successfully!"
}

# Delete SNS topics
delete_sns_topics() {
    print_header "Deleting SNS Topics"
    
    # List topics
    TOPICS=$(aws sns list-topics --region "$REGION" --query 'Topics[?contains(TopicArn, `iot-alerts`)].TopicArn' --output text)
    
    for topic in $TOPICS; do
        if [ ! -z "$topic" ]; then
            print_status "Deleting SNS topic: $topic"
            aws sns delete-topic --topic-arn "$topic" --region "$REGION"
        fi
    done
    
    print_status "SNS topics deleted successfully!"
}

# Delete Glue resources
delete_glue_resources() {
    print_header "Deleting Glue Resources"
    
    # Delete crawlers
    CRAWLERS=$(aws glue get-crawlers --region "$REGION" --query 'CrawlerList[?contains(Name, `iot-pipeline`)].Name' --output text)
    
    for crawler in $CRAWLERS; do
        if [ ! -z "$crawler" ]; then
            print_status "Deleting Glue crawler: $crawler"
            aws glue delete-crawler --name "$crawler" --region "$REGION"
        fi
    done
    
    # Delete databases
    DATABASES=$(aws glue get-databases --region "$REGION" --query 'DatabaseList[?contains(Name, `iot_pipeline`)].Name' --output text)
    
    for database in $DATABASES; do
        if [ ! -z "$database" ]; then
            print_status "Deleting Glue database: $database"
            aws glue delete-database --name "$database" --region "$REGION"
        fi
    done
    
    print_status "Glue resources deleted successfully!"
}

# Delete IAM roles
delete_iam_roles() {
    print_header "Deleting IAM Roles"
    
    # List roles
    ROLES=$(aws iam list-roles --query 'Roles[?contains(RoleName, `iot-pipeline`)].RoleName' --output text)
    
    for role in $ROLES; do
        if [ ! -z "$role" ]; then
            print_status "Deleting IAM role: $role"
            
            # Detach policies
            POLICIES=$(aws iam list-attached-role-policies --role-name "$role" --query 'AttachedPolicies[].PolicyArn' --output text)
            for policy in $POLICIES; do
                if [ ! -z "$policy" ]; then
                    aws iam detach-role-policy --role-name "$role" --policy-arn "$policy"
                fi
            done
            
            # Delete inline policies
            INLINE_POLICIES=$(aws iam list-role-policies --role-name "$role" --query 'PolicyNames' --output text)
            for policy in $INLINE_POLICIES; do
                if [ ! -z "$policy" ]; then
                    aws iam delete-role-policy --role-name "$role" --policy-name "$policy"
                fi
            done
            
            # Delete role
            aws iam delete-role --role-name "$role"
        fi
    done
    
    print_status "IAM roles deleted successfully!"
}

# Delete CloudWatch dashboards
delete_cloudwatch_dashboards() {
    print_header "Deleting CloudWatch Dashboards"
    
    # List dashboards
    DASHBOARDS=$(aws cloudwatch list-dashboards --region "$REGION" --query 'DashboardEntries[?contains(DashboardName, `iot-pipeline`)].DashboardName' --output text)
    
    for dashboard in $DASHBOARDS; do
        if [ ! -z "$dashboard" ]; then
            print_status "Deleting CloudWatch dashboard: $dashboard"
            aws cloudwatch delete-dashboards --dashboard-names "$dashboard" --region "$REGION"
        fi
    done
    
    print_status "CloudWatch dashboards deleted successfully!"
}

# Delete CloudWatch alarms
delete_cloudwatch_alarms() {
    print_header "Deleting CloudWatch Alarms"
    
    # List alarms
    ALARMS=$(aws cloudwatch describe-alarms --region "$REGION" --query 'MetricAlarms[?contains(AlarmName, `iot-pipeline`)].AlarmName' --output text)
    
    for alarm in $ALARMS; do
        if [ ! -z "$alarm" ]; then
            print_status "Deleting CloudWatch alarm: $alarm"
            aws cloudwatch delete-alarms --alarm-names "$alarm" --region "$REGION"
        fi
    done
    
    print_status "CloudWatch alarms deleted successfully!"
}

# Delete IoT resources
delete_iot_resources() {
    print_header "Deleting IoT Resources"
    
    # Delete thing groups
    THING_GROUPS=$(aws iot list-thing-groups --region "$REGION" --query 'thingGroups[?contains(groupName, `iot-pipeline`)].groupName' --output text)
    
    for group in $THING_GROUPS; do
        if [ ! -z "$group" ]; then
            print_status "Deleting IoT thing group: $group"
            aws iot delete-thing-group --thing-group-name "$group" --region "$REGION"
        fi
    done
    
    # Delete policies
    POLICIES=$(aws iot list-policies --region "$REGION" --query 'policies[?contains(policyName, `iot-pipeline`)].policyName' --output text)
    
    for policy in $POLICIES; do
        if [ ! -z "$policy" ]; then
            print_status "Deleting IoT policy: $policy"
            aws iot delete-policy --policy-name "$policy" --region "$REGION"
        fi
    done
    
    print_status "IoT resources deleted successfully!"
}

# Delete VPC resources
delete_vpc_resources() {
    print_header "Deleting VPC Resources"
    
    # Get VPC ID
    VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=tag:Name,Values=*iot-pipeline*" --query 'Vpcs[0].VpcId' --output text)
    
    if [ ! -z "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
        print_status "Deleting VPC: $VPC_ID"
        
        # Delete internet gateway
        IGW_ID=$(aws ec2 describe-internet-gateways --region "$REGION" --filters "Name=attachment.vpc-id,Values=$VPC_ID" --query 'InternetGateways[0].InternetGatewayId' --output text)
        if [ ! -z "$IGW_ID" ] && [ "$IGW_ID" != "None" ]; then
            aws ec2 detach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID" --region "$REGION"
            aws ec2 delete-internet-gateway --internet-gateway-id "$IGW_ID" --region "$REGION"
        fi
        
        # Delete subnets
        SUBNET_IDS=$(aws ec2 describe-subnets --region "$REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].SubnetId' --output text)
        for subnet in $SUBNET_IDS; do
            if [ ! -z "$subnet" ]; then
                aws ec2 delete-subnet --subnet-id "$subnet" --region "$REGION"
            fi
        done
        
        # Delete route tables
        ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables --region "$REGION" --filters "Name=vpc-id,Values=$VPC_ID" --query 'RouteTables[].RouteTableId' --output text)
        for route_table in $ROUTE_TABLE_IDS; do
            if [ ! -z "$route_table" ]; then
                aws ec2 delete-route-table --route-table-id "$route_table" --region "$REGION"
            fi
        done
        
        # Delete VPC
        aws ec2 delete-vpc --vpc-id "$VPC_ID" --region "$REGION"
    fi
    
    print_status "VPC resources deleted successfully!"
}

# Delete Terraform state
delete_terraform_state() {
    print_header "Deleting Terraform State"
    
    if [ -d "terraform" ]; then
        cd terraform
        
        # Destroy infrastructure
        print_status "Destroying infrastructure with Terraform..."
        terraform destroy -var="project_name=$PROJECT_NAME" -var="environment=dev" -auto-approve
        
        cd ..
    fi
    
    print_status "Terraform state deleted successfully!"
}

# Clean up local files
cleanup_local_files() {
    print_header "Cleaning Up Local Files"
    
    # Remove generated files
    rm -f infrastructure_outputs.json
    rm -rf lambda/lambda_function.zip
    rm -rf sagemaker/models
    rm -f sagemaker/training_data.csv
    
    # Remove virtual environment
    if [ -d "venv" ]; then
        rm -rf venv
    fi
    
    print_status "Local files cleaned up successfully!"
}

# Main cleanup function
main() {
    print_header "IoT Pipeline Cleanup"
    
    # Confirm cleanup
    confirm_cleanup
    
    # Delete resources in reverse order of creation
    delete_sagemaker_endpoints
    delete_lambda_functions
    delete_kinesis_streams
    delete_firehose_streams
    delete_s3_buckets
    delete_sns_topics
    delete_glue_resources
    delete_cloudwatch_dashboards
    delete_cloudwatch_alarms
    delete_iot_resources
    delete_vpc_resources
    delete_terraform_state
    cleanup_local_files
    
    print_status "Cleanup completed successfully!"
    print_warning "Please verify that all resources have been deleted in the AWS console."
}

# Run main function
main "$@" 