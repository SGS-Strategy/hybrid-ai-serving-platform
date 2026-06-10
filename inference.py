import torch
import torch.nn as nn
import json
import logging
import os
import joblib
import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

CLASS_LABELS = {0: "Normal", 1: "Type1", 2: "Type2", 3: "Type3"}

MODEL_DIR = os.environ.get("MODEL_DIR", "/model")

device = torch.device("cpu")

model = nn.Sequential(
    nn.Linear(4, 100), nn.ReLU(), nn.Dropout(0.2),
    nn.Linear(100, 100), nn.ReLU(), nn.Dropout(0.2),
    nn.Linear(100, 100), nn.ReLU(), nn.Dropout(0.2),
    nn.Linear(100, 4)
)
model.load_state_dict(torch.load(os.path.join(MODEL_DIR, "model.pt"), map_location=device))
model.eval()

scaler = None
scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
if os.path.isfile(scaler_path):
    scaler = joblib.load(scaler_path)

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
async def predict(request: Request):
    body = await request.json()
    sensor_data = body.get("instances", body.get("data", body))
    if isinstance(sensor_data[0], (int, float)):
        sensor_data = [sensor_data]
    inputs = np.array(sensor_data, dtype=np.float32)
    if scaler is not None:
        inputs = scaler.transform(inputs)
    tensor = torch.tensor(inputs, dtype=torch.float32).to(device)
    with torch.no_grad():
        outputs = model(tensor)
    probabilities = torch.softmax(outputs, dim=1)
    predicted_classes = torch.argmax(probabilities, dim=1)
    results = []
    for i in range(len(predicted_classes)):
        class_id = predicted_classes[i].item()
        probs = probabilities[i].tolist()
        results.append({
            "class_id": class_id,
            "class_name": CLASS_LABELS[class_id],
            "probabilities": {CLASS_LABELS[j]: round(probs[j], 4) for j in range(4)}
        })
    return JSONResponse({"predictions": results})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
