import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

PATH = '/app/'

class KAMP_DNN(nn.Module):
    def __init__(self):
        super(KAMP_DNN, self).__init__()
        self.layer1 = nn.Linear(in_features=4, out_features=100)
        self.layer2 = nn.Linear(in_features=100, out_features=100)
        self.layer3 = nn.Linear(in_features=100, out_features=100)
        self.layer4 = nn.Linear(in_features=100, out_features=4)
        self.dropout = nn.Dropout(0.2)
        self.relu = nn.ReLU()
    
    def forward(self, input):
        out = self.layer1(input)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.layer2(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.layer3(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.layer4(out)
        return out

model = None
scaler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, scaler
    model = torch.load(PATH + 'model.pt', weights_only=False)
    scaler = joblib.load(PATH + 'scaler.pkl')
    model.eval()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.post("/v1/models/pdm:predict")
def predict(payload: dict):
    df_raw = pd.DataFrame(payload["inputs"])
    
    # 학습과 100% 동일한 전처리 (이동평균필터 M=15)
    M = 15
    s1_f = np.convolve(df_raw['sensor1'], np.ones(M), 'valid') / M
    s2_f = np.convolve(df_raw['sensor2'], np.ones(M), 'valid') / M
    s3_f = np.convolve(df_raw['sensor3'], np.ones(M), 'valid') / M
    s4_f = np.convolve(df_raw['sensor4'], np.ones(M), 'valid') / M
    
    features_temp = np.concatenate((
        s1_f.reshape(-1, 1), 
        s2_f.reshape(-1, 1), 
        s3_f.reshape(-1, 1), 
        s4_f.reshape(-1, 1)
    ), axis=1)

    # 학습과 100% 동일한 전처리 및 경고 우회 (MinMax 스케일링)
    df_features = pd.DataFrame(features_temp, columns=['s1', 's2', 's3', 's4'])
    features_scaled = scaler.transform(df_features)

    # 텐서 변환 및 순방향 연산
    x_tensor = torch.from_numpy(features_scaled).float()
    
    with torch.no_grad():
        outputs = model(x_tensor)
        _, predicted_classes = torch.max(outputs.data, 1)
        
    # 최빈값 기준으로 최종 결과 도출
    final_class = int(torch.mode(predicted_classes).values.item())
    
    # 숫자를 명확한 텍스트 상태 값으로 매핑
    class_mapping = {
        0: "normal",
        1: "type1",
        2: "type2",
        3: "type3"
    }
    
    return {"predictions": [{"class_name": class_mapping.get(final_class, "unknown")}]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)