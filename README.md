# IoT Predictive Maintenance Pipeline (AWS)

A comprehensive IoT data pipeline for predictive maintenance using AWS services. This project demonstrates a complete end-to-end solution for collecting, processing, analyzing, and alerting on industrial sensor data.

![Architecture](images/image.png)

## 🏗️ Architecture

```
IoT Devices → AWS IoT Core → Kinesis Data Streams → Lambda → Firehose → S3
                                                      ↓
                                              SageMaker Endpoint
                                                      ↓
                                              SNS Alerts
                                                      ↓
                                              CloudWatch Monitoring
```

### Components

- **AWS IoT Core**: MQTT message ingestion and device management
- **Kinesis Data Streams**: Real-time data streaming
- **Lambda Functions**: Data transformation and feature engineering
- **Kinesis Firehose**: Batch data delivery to S3
- **S3**: Data lake storage
- **Glue**: ETL jobs and data catalog
- **Athena**: Interactive querying
- **SageMaker**: ML model training and inference
- **SNS**: Alert notifications
- **CloudWatch**: Monitoring and logging
- **IAM**: Security and access management

## 🚀 Features

- **Real-time Processing**: Stream processing with sub-second latency
- **ML-powered Anomaly Detection**: Automated detection of equipment issues
- **Scalable Architecture**: Handles thousands of IoT devices
- **Data Lake**: Query historical data with SQL
- **Monitoring & Alerting**: Comprehensive observability
- **Security**: End-to-end encryption and IAM policies
- **Infrastructure as Code**: Terraform for reproducible deployments

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0
- Python 3.8+
- Docker (for local development)

## 🛠️ Setup Instructions

### 1. Clone and Configure

```bash
git clone <repository-url>
cd IOT-AWS-Pipeline
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and default region
```

### 3. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### 4. Deploy Lambda Functions

```bash
cd ../lambda
./deploy.sh
```

### 5. Train and Deploy ML Model

```bash
cd ../sagemaker
python train_model.py
./deploy_model.sh
```

### 6. Start Sensor Simulator

```bash
cd ../sensor_simulator
python sensor_simulator.py
```

## 📁 Project Structure

```
IOT-AWS-Pipeline/
├── terraform/                 # Infrastructure as Code
│   ├── main.tf               # Main Terraform configuration
│   ├── variables.tf          # Variable definitions
│   ├── outputs.tf            # Output values
│   └── modules/              # Reusable Terraform modules
├── lambda/                   # AWS Lambda Functions
│   ├── inference_and_alert.py
│   ├── data_transformer.py
│   └── deploy.sh
├── sagemaker/               # ML Model Training & Inference
│   ├── train_model.py
│   ├── inference.py
│   └── deploy_model.sh
├── sensor_simulator/        # IoT Device Simulator
│   ├── sensor_simulator.py
│   └── requirements.txt
├── glue/                    # ETL Jobs
│   ├── etl_job.py
│   └── crawler.py
├── athena/                  # SQL Queries
│   ├── queries.sql
│   └── views.sql
├── firehose/               # Firehose Configuration
│   └── firehose_s3_config.json
├── monitoring/             # CloudWatch Dashboards & Alarms
│   ├── dashboard.json
│   └── alarms.json
├── scripts/               # Utility Scripts
│   ├── setup.sh
│   └── cleanup.sh
├── docs/                  # Documentation
│   ├── architecture.md
│   └── api.md
└── tests/                 # Test Suite
    ├── unit/
    └── integration/
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
AWS_REGION=eu-central-1
S3_BUCKET_NAME=iot-sensor-data-bucket
KINESIS_STREAM_NAME=iot-sensor-stream
SAGEMAKER_ENDPOINT_NAME=sensor-anomaly-endpoint
SNS_TOPIC_NAME=iot-alerts
```

### AWS IoT Core Setup

1. Create IoT certificates and policies
2. Download certificates to `sensor_simulator/` directory
3. Update endpoint in `sensor_simulator.py`

## 📊 Monitoring

### CloudWatch Dashboards

- **IoT Metrics**: Device connectivity and message rates
- **Data Pipeline**: Kinesis, Lambda, and Firehose metrics
- **ML Performance**: SageMaker endpoint metrics
- **Cost Monitoring**: AWS service costs

### Alerts

- Anomaly detection alerts via SNS
- Pipeline failure notifications
- Cost threshold alerts
- Performance degradation alerts

## 🔍 Querying Data

### Athena Queries

```sql
-- Recent anomalies
SELECT * FROM sensor_data 
WHERE anomaly_detected = true 
ORDER BY timestamp DESC 
LIMIT 100;

-- Machine performance trends
SELECT machine_id, 
       AVG(temperature) as avg_temp,
       AVG(vibration) as avg_vibration
FROM sensor_data 
WHERE timestamp >= NOW() - INTERVAL '24' HOUR
GROUP BY machine_id;
```

## 🧪 Testing

### Unit Tests

```bash
cd tests/unit
python -m pytest
```

### Integration Tests

```bash
cd tests/integration
python -m pytest
```

### Load Testing

```bash
cd tests/load
python load_test.py
```

## 🚨 Troubleshooting

### Common Issues

1. **IoT Connection Issues**: Check certificates and policies
2. **Lambda Timeouts**: Increase timeout or optimize code
3. **SageMaker Cold Start**: Use provisioned concurrency
4. **Data Pipeline Delays**: Check Firehose buffering settings

### Logs

- **IoT Core**: CloudWatch Logs in `/aws/iot/`
- **Lambda**: CloudWatch Logs in `/aws/lambda/`
- **SageMaker**: CloudWatch Logs in `/aws/sagemaker/`

## 📈 Performance Optimization

- **Lambda**: Use provisioned concurrency for consistent latency
- **Kinesis**: Adjust shard count based on throughput
- **Firehose**: Optimize buffering for cost vs latency
- **SageMaker**: Use multi-model endpoints for cost efficiency

## 🔒 Security

- **Encryption**: All data encrypted in transit and at rest
- **IAM**: Least privilege access policies
- **VPC**: Network isolation where applicable
- **Monitoring**: Security event logging and alerting

## 💰 Cost Optimization

- **S3 Lifecycle**: Automatic data archival
- **Lambda**: Right-sizing memory allocation
- **SageMaker**: Spot instances for training
- **Kinesis**: On-demand scaling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For questions and support:
- Create an issue in the repository
- Check the [documentation](docs/)
- Review the [troubleshooting guide](docs/troubleshooting.md)
