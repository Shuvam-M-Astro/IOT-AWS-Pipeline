variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Name of the project, used for resource naming"
  type        = string
  default     = "iot-pipeline"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones for subnets"
  type        = list(string)
  default     = ["eu-central-1a", "eu-central-1b"]
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for IoT data"
  type        = string
  default     = "iot-sensor-data-bucket"
}

variable "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  type        = string
  default     = "iot-sensor-stream"
}

variable "kinesis_shard_count" {
  description = "Number of shards for Kinesis stream"
  type        = number
  default     = 1
}

variable "sns_topic_name" {
  description = "Name of the SNS topic for alerts"
  type        = string
  default     = "iot-alerts"
}

variable "alert_emails" {
  description = "List of email addresses for SNS alerts"
  type        = list(string)
  default     = ["admin@example.com"]
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  type        = string
  default     = "sensor-anomaly-endpoint"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "firehose_buffering_size" {
  description = "Firehose buffering size in MB"
  type        = number
  default     = 5
}

variable "firehose_buffering_interval" {
  description = "Firehose buffering interval in seconds"
  type        = number
  default     = 60
}

variable "glue_crawler_schedule" {
  description = "Schedule for Glue crawler (cron expression)"
  type        = string
  default     = "cron(0 */6 * * ? *)"  # Every 6 hours
}

variable "cloudwatch_log_retention" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "iot-pipeline"
    Environment = "dev"
    ManagedBy   = "Terraform"
  }
} 