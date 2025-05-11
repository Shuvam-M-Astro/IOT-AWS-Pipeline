import joblib
import os
import json
import numpy as np

model = joblib.load(os.path.join("/opt/ml/model", "model.joblib"))

def model_fn(model_dir):
    return model

def predict_fn(input_data, model):
    data = np.array([[input_data["temperature"], input_data["vibration"], input_data["pressure"]]])
    prediction = model.predict(data)
    return int(prediction[0])
