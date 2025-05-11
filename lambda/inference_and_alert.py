import boto3
import json

runtime = boto3.client('sagemaker-runtime')
sns = boto3.client('sns')

SNS_TOPIC_ARN = "arn:aws:sns:eu-central-1:<your-account-id>:iot-alerts"
SAGEMAKER_ENDPOINT = "sensor-anomaly-endpoint"

def lambda_handler(event, context):
    record = json.loads(event["Records"][0]["body"])
    payload = {
        "temperature": record["temperature"],
        "vibration": record["vibration"],
        "pressure": record["pressure"]
    }

    response = runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    prediction = int(response['Body'].read().decode())
    if prediction == 1:
        message = f"Anomaly detected on {record['machine_id']}: {payload}"
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=message, Subject="IoT Anomaly Alert")
    
    return {"statusCode": 200, "body": "Checked anomaly"}
