# sensor_simulator.py
import time
import json
import random
import ssl
import paho.mqtt.client as mqtt

client_id = "sensor-device-01"
endpoint = "<your-iot-endpoint>"  # e.g., a3k7odshai.iot.eu-central-1.amazonaws.com
topic = "factory/machine1/data"

# Paths to AWS IoT Core credentials
ca_path = "./AmazonRootCA1.pem"
cert_path = "./device-certificate.pem.crt"
key_path = "./private.pem.key"

def get_sensor_data():
    return {
        "machine_id": "MCH001",
        "timestamp": int(time.time()),
        "temperature": round(random.uniform(40, 90), 2),
        "vibration": round(random.uniform(0.1, 2.5), 2),
        "pressure": round(random.uniform(80, 120), 2)
    }

client = mqtt.Client(client_id)
client.tls_set(ca_path, certfile=cert_path, keyfile=key_path, tls_version=ssl.PROTOCOL_TLSv1_2)
client.connect(endpoint, 8883, 60)
client.loop_start()

while True:
    payload = get_sensor_data()
    client.publish(topic, json.dumps(payload), qos=1)
    print("Published:", payload)
    time.sleep(5)
