import torch
import torch.nn as nn
import json
import logging
import os
import joblib
import numpy as np
from ts.torch_handler.base_handler import BaseHandler

logger = logging.getLogger(__name__)
CLASS_LABELS = {0: "Normal", 1: "Type1", 2: "Type2", 3: "Type3"}

class KAMPDNNHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.scaler = None
        self.initialized = False

    def initialize(self, context):
        properties = context.system_properties
        model_dir = properties.get("model_dir")
        self.device = torch.device("cpu")
        model_pt_path = os.path.join(model_dir, "model.pt")
        state_dict = torch.load(model_pt_path, map_location=self.device)
        self.model = nn.Sequential(
            nn.Linear(4, 100), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(100, 100), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(100, 100), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(100, 4)
        )
        self.model.load_state_dict(state_dict)
        self.model.eval()
        scaler_path = os.path.join(model_dir, "scaler.pkl")
        if os.path.isfile(scaler_path):
            self.scaler = joblib.load(scaler_path)
        self.initialized = True

    def preprocess(self, data):
        inputs = []
        for row in data:
            body = row.get("body") or row.get("data") or row
            if isinstance(body, (bytes, bytearray)):
                body = json.loads(body.decode("utf-8"))
            elif isinstance(body, str):
                body = json.loads(body)
            sensor_data = body.get("instances", body.get("data", body))
            if isinstance(sensor_data[0], (int, float)):
                inputs.append(sensor_data)
            else:
                inputs.extend(sensor_data)
        inputs = np.array(inputs, dtype=np.float32)
        if self.scaler is not None:
            inputs = self.scaler.transform(inputs)
        return torch.tensor(inputs, dtype=torch.float32).to(self.device)

    def inference(self, inputs):
        with torch.no_grad():
            return self.model(inputs)

    def postprocess(self, outputs):
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
        return results
