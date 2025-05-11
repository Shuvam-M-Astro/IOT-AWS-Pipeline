# train_model.py
from sklearn.ensemble import RandomForestClassifier
import joblib
import pandas as pd
import numpy as np

df = pd.read_csv("training_data.csv")
X = df[["temperature", "vibration", "pressure"]]
y = df["anomaly_score"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "model.joblib")
