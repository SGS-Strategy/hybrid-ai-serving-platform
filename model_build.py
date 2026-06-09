import os
import random
import numpy as np
import pandas as pd
from scipy import interpolate
from sklearn.preprocessing import MinMaxScaler
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
import joblib
from minio import Minio

# ===== MinIO 설정 =====
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio.minio.svc.cluster.local:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
BUCKET = "kamp-models"

client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

# ===== CSV 다운로드 =====
print("CSV 다운로드 중...")
os.makedirs("/tmp/raw_data", exist_ok=True)
for i in range(1, 5):
    client.fget_object(BUCKET, f"raw-data/g1_sensor{i}.csv", f"/tmp/raw_data/g1_sensor{i}.csv")
print("CSV 다운로드 완료!")

# =========================
# 1. 데이터 불러오기
# =========================
sensor1 = pd.read_csv("/tmp/raw_data/g1_sensor1.csv", names=["time","normal","type1","type2","type3"])
sensor2 = pd.read_csv("/tmp/raw_data/g1_sensor2.csv", names=["time","normal","type1","type2","type3"])
sensor3 = pd.read_csv("/tmp/raw_data/g1_sensor3.csv", names=["time","normal","type1","type2","type3"])
sensor4 = pd.read_csv("/tmp/raw_data/g1_sensor4.csv", names=["time","normal","type1","type2","type3"])

# =========================
# 2. 선형보간
# =========================
t_min = max(
    sensor1["time"].min(),
    sensor2["time"].min(),
    sensor3["time"].min(),
    sensor4["time"].min()
)

t_max = min(
    sensor1["time"].max(),
    sensor2["time"].max(),
    sensor3["time"].max(),
    sensor4["time"].max()
)

x_new = np.arange(t_min, t_max - 0.01, 0.001)

y_new1, y_new2, y_new3, y_new4 = [], [], [], []

for item in ["normal", "type1", "type2", "type3"]:
    f1 = interpolate.interp1d(sensor1["time"], sensor1[item], kind="linear", bounds_error=False, fill_value="extrapolate")
    f2 = interpolate.interp1d(sensor2["time"], sensor2[item], kind="linear", bounds_error=False, fill_value="extrapolate")
    f3 = interpolate.interp1d(sensor3["time"], sensor3[item], kind="linear", bounds_error=False, fill_value="extrapolate")
    f4 = interpolate.interp1d(sensor4["time"], sensor4[item], kind="linear", bounds_error=False, fill_value="extrapolate")
    y_new1.append(f1(x_new))
    y_new2.append(f2(x_new))
    y_new3.append(f3(x_new))
    y_new4.append(f4(x_new))

sensor1 = pd.DataFrame(np.array(y_new1).T, columns=["normal", "type1", "type2", "type3"])
sensor2 = pd.DataFrame(np.array(y_new2).T, columns=["normal", "type1", "type2", "type3"])
sensor3 = pd.DataFrame(np.array(y_new3).T, columns=["normal", "type1", "type2", "type3"])
sensor4 = pd.DataFrame(np.array(y_new4).T, columns=["normal", "type1", "type2", "type3"])

# =========================
# 3. 센서별 데이터 조정
# =========================
normal_ = pd.concat([sensor1["normal"],sensor2["normal"],sensor3["normal"],sensor4["normal"]], axis=1)
type1_  = pd.concat([sensor1["type1"], sensor2["type1"], sensor3["type1"], sensor4["type1"]], axis=1)
type2_  = pd.concat([sensor1["type2"], sensor2["type2"], sensor3["type2"], sensor4["type2"]], axis=1)
type3_  = pd.concat([sensor1["type3"], sensor2["type3"], sensor3["type3"], sensor4["type3"]], axis=1)

normal_.columns = type1_.columns = type2_.columns = type3_.columns = ["s1","s2","s3","s4"]

# =========================
# 4. 이동평균
# =========================
M = 15

def moving_avg_4ch(df):
    result = []
    for col in ["s1","s2","s3","s4"]:
        result.append(np.convolve(df[col], np.ones(M), "valid") / M)
    return np.stack(result, axis=1)

normal_temp = moving_avg_4ch(normal_)
type1_temp  = moving_avg_4ch(type1_)
type2_temp  = moving_avg_4ch(type2_)
type3_temp  = moving_avg_4ch(type3_)

# =========================
# 5. MinMax 정규화
# =========================
scaler = MinMaxScaler()
scaler.fit(normal_)

normal = scaler.transform(normal_temp)
type1  = scaler.transform(type1_temp)
type2  = scaler.transform(type2_temp)
type3  = scaler.transform(type3_temp)

# =========================
# 6. 데이터 크기 조정
# =========================
normal = normal[30000:130000][:]
type1  = type1[30000:130000][:]
type2  = type2[30000:130000][:]
type3  = type3[30000:130000][:]

# =========================
# 7. 데이터 분배
# =========================
normal_train, normal_valid, normal_test = normal[:60000], normal[60000:80000], normal[80000:]
type1_train,  type1_valid,  type1_test  = type1[:60000],  type1[60000:80000],  type1[80000:]
type2_train,  type2_valid,  type2_test  = type2[:60000],  type2[60000:80000],  type2[80000:]
type3_train,  type3_valid,  type3_test  = type3[:60000],  type3[60000:80000],  type3[80000:]

train = np.concatenate((normal_train, type1_train, type2_train, type3_train))
valid = np.concatenate((normal_valid, type1_valid, type2_valid, type3_valid))
test  = np.concatenate((normal_test,  type1_test,  type2_test,  type3_test))

# =========================
# 8. 라벨 생성
# =========================
y_train = np.concatenate((np.zeros(len(normal_train)), np.ones(len(type1_train)), np.ones(len(type2_train))*2, np.ones(len(type3_train))*3))
y_valid = np.concatenate((np.zeros(len(normal_valid)), np.ones(len(type1_valid)), np.ones(len(type2_valid))*2, np.ones(len(type3_valid))*3))
y_test  = np.concatenate((np.zeros(len(normal_test)),  np.ones(len(type1_test)),  np.ones(len(type2_test))*2,  np.ones(len(type3_test))*3))

# =========================
# 9. Tensor 변환
# =========================
x_train = torch.Tensor(train)
x_valid = torch.Tensor(valid)
x_test  = torch.Tensor(test)
y_train = torch.LongTensor(y_train)
y_valid = torch.LongTensor(y_valid)
y_test  = torch.LongTensor(y_test)

# =========================
# 10. DataLoader
# =========================
train_dataloader = DataLoader(TensorDataset(x_train, y_train), batch_size=80000, shuffle=True)
valid_dataloader = DataLoader(TensorDataset(x_valid, y_valid), batch_size=80000, shuffle=False)
test_dataloader  = DataLoader(TensorDataset(x_test,  y_test),  batch_size=80000, shuffle=False)

# =========================
# 11. DNN 모델
# =========================
class KAMP_DNN(nn.Module):
    def __init__(self):
        super(KAMP_DNN, self).__init__()
        self.layer1  = nn.Linear(4, 100)
        self.layer2  = nn.Linear(100, 100)
        self.layer3  = nn.Linear(100, 100)
        self.layer4  = nn.Linear(100, 4)
        self.dropout = nn.Dropout(0.2)
        self.relu    = nn.ReLU()
    def forward(self, input):
        out = self.relu(self.dropout(self.layer1(input)))
        out = self.relu(self.dropout(self.layer2(out)))
        out = self.relu(self.dropout(self.layer3(out)))
        return self.layer4(out)

# =========================
# 12. 학습 함수
# =========================
def train_model(model, criterion, optimizer, num_epochs, train_dataloader, PATH):
    os.makedirs(PATH, exist_ok=True)
    loss_values, loss_values_v = [], []
    check = 0
    accuracy_past = 0.0

    for epoch in range(num_epochs):
        model.train()
        for x_batch, y_batch in train_dataloader:
            optimizer.zero_grad()
            loss = criterion(model(x_batch), y_batch)
            loss.backward()
            optimizer.step()
        loss_values.append(loss.item())

        model.eval()
        total, accuracy = 0.0, 0.0
        with torch.no_grad():
            for x_batch, y_batch in valid_dataloader:
                v_hat = model(x_batch)
                v_loss = criterion(v_hat, y_batch)
                _, predicted = torch.max(v_hat.data, 1)
                total += y_batch.size(0)
                accuracy += (predicted == y_batch).sum().item()

        accuracy /= total
        loss_values_v.append(v_loss.item())
        print(f"[Epoch {epoch+1}/{num_epochs}] Train Loss: {loss.item():.6f} Valid Loss: {v_loss.item():.6f} Accuracy: {accuracy:.6f}")

        if accuracy_past > accuracy:
            check += 1
        else:
            check = 0
        accuracy_past = accuracy

        if check > 50:
            print("Early stopping!")
            torch.save(model.state_dict(), PATH + "model.pt")
            joblib.dump(scaler, "/tmp/scaler.pkl")
            client.fput_object(BUCKET, "artifacts/model.pt", PATH + "model.pt")
            client.fput_object(BUCKET, "artifacts/scaler.pkl", "/tmp/scaler.pkl")
            print("저장 완료!")
            return loss_values, loss_values_v

    torch.save(model.state_dict(), PATH + "model.pt")
    joblib.dump(scaler, "/tmp/scaler.pkl")
    client.fput_object(BUCKET, "artifacts/model.pt", PATH + "model.pt")
    client.fput_object(BUCKET, "artifacts/scaler.pkl", "/tmp/scaler.pkl")
    print("저장 완료!")
    return loss_values, loss_values_v

# =========================
# 13. 학습 실행
# =========================
DNN_model = KAMP_DNN()
num_epochs = 200
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(DNN_model.parameters())
PATH = "/tmp/save/DNN/"

DNN_loss_values, DNN_loss_values_v = train_model(DNN_model, criterion, optimizer, num_epochs, train_dataloader, PATH)
