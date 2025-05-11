import base64
import json
import boto3

firehose = boto3.client("firehose")
FIREHOSE_STREAM_NAME = "iot-delivery-stream"

def lambda_handler(event, context):
    for record in event['Records']:
        payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
        data = json.loads(payload)
        
        # Add simple derived field
        anomaly_score = 0
        if data['temperature'] > 85 or data['vibration'] > 2.0 or data['pressure'] > 110:
            anomaly_score = 1

        data['anomaly_score'] = anomaly_score
        
        # Send to Firehose
        firehose.put_record(
            DeliveryStreamName=FIREHOSE_STREAM_NAME,
            Record={"Data": json.dumps(data) + "\n"}
        )
        
    return {"statusCode": 200, "body": "Processed"}
