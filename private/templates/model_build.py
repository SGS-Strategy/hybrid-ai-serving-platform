# 라이브러리 불러오기
import argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
import os
from pathlib import Path
from minio import Minio
from urllib.parse import unquote

parser = argparse.ArgumentParser()
parser.add_argument('--data', default='/tmp/raw_data')
parser.add_argument('--output', default='/tmp')
parser.add_argument('--upload-minio', action='store_true')
args = parser.parse_args()

DATA_DIR = Path(args.data)
OUTPUT_DIR = Path(args.output)

# MinIO 클라이언트 설정
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'minio-api.minio-tenant.svc.cluster.local:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
DATASET_BUCKET = os.environ.get('DATASET_BUCKET', 'datasets')
ARTIFACT_BUCKET = os.environ.get('ARTIFACT_BUCKET', 'artifacts')
DATASET_OBJECT_KEY_RAW = os.environ.get('DATASET_OBJECT_KEY', '')
client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

REQUIRED_CSV_FILES = [f'g1_sensor{i}.csv' for i in range(1, 5)]


def resolve_local_data_dir(base_dir: Path) -> Path:
    if all((base_dir / name).exists() for name in REQUIRED_CSV_FILES):
        return base_dir
    raw_data_dir = base_dir / 'raw-data'
    if all((raw_data_dir / name).exists() for name in REQUIRED_CSV_FILES):
        return raw_data_dir
    return base_dir


def resolve_dataset_metadata(dataset_object_key_raw: str):
    decoded_key = unquote(dataset_object_key_raw).strip()
    if not decoded_key:
        return "", "", ""

    dataset_prefix = decoded_key
    if dataset_prefix.endswith('/_SUCCESS'):
        dataset_prefix = dataset_prefix[:-len('_SUCCESS')]
    dataset_prefix = dataset_prefix.rstrip('/')
    if dataset_prefix:
        dataset_prefix = dataset_prefix + '/'

    dataset_version = dataset_prefix.rstrip('/').split('/')[-1] if dataset_prefix else ""
    return decoded_key, dataset_prefix, dataset_version


def ensure_dataset_csvs(target_dir: Path, dataset_object_key_raw: str):
    dataset_object_key, dataset_prefix, dataset_version = resolve_dataset_metadata(dataset_object_key_raw)

    print(f"DATASET_OBJECT_KEY={dataset_object_key or '<unset>'}")
    print(f"DATASET_PREFIX={dataset_prefix or '<unset>'}")
    print(f"DATASET_VERSION={dataset_version or '<unset>'}")

    if not dataset_object_key:
        raise RuntimeError(
            "DATASET_OBJECT_KEY is required when local CSV files are unavailable. "
            f"DATASET_OBJECT_KEY={dataset_object_key or '<unset>'}, "
            f"DATASET_PREFIX={dataset_prefix or '<unset>'}, "
            f"DATASET_VERSION={dataset_version or '<unset>'}, "
            "found_csv_objects=[], missing_files="
            f"{REQUIRED_CSV_FILES}"
        )

    csv_objects = sorted(
        obj.object_name
        for obj in client.list_objects(DATASET_BUCKET, prefix=dataset_prefix, recursive=True)
        if obj.object_name.endswith('.csv')
    )
    print(f"발견한 CSV object 목록: {csv_objects}")

    csv_object_map = {Path(object_name).name: object_name for object_name in csv_objects}
    missing_files = [name for name in REQUIRED_CSV_FILES if name not in csv_object_map]
    if missing_files:
        raise RuntimeError(
            "Required dataset CSV files are missing. "
            f"DATASET_OBJECT_KEY={dataset_object_key}, "
            f"DATASET_PREFIX={dataset_prefix}, "
            f"DATASET_VERSION={dataset_version}, "
            f"found_csv_objects={csv_objects}, "
            f"missing_files={missing_files}"
        )

    downloaded_csv_objects = []
    for file_name in REQUIRED_CSV_FILES:
        object_name = csv_object_map[file_name]
        local_path = target_dir / file_name
        client.fget_object(DATASET_BUCKET, object_name, str(local_path))
        downloaded_csv_objects.append(object_name)

    print(f"다운로드한 CSV object 목록: {downloaded_csv_objects}")
    print(f"로컬 저장 경로: {target_dir}")
    print("CSV 다운로드 완료!")


# MinIO에서 CSV 다운로드 또는 이미 받은 데이터셋 사용
os.makedirs(DATA_DIR, exist_ok=True)
DATA_DIR = resolve_local_data_dir(DATA_DIR)

if all((DATA_DIR / name).exists() for name in REQUIRED_CSV_FILES):
    print(f"CSV 데이터 사용: {DATA_DIR}")
else:
    ensure_dataset_csvs(DATA_DIR, DATASET_OBJECT_KEY_RAW)

# 데이터 불러오기
sensor1 = pd.read_csv(DATA_DIR / 'g1_sensor1.csv', names = ['time', 'normal', 'type1', 'type2', 'type3'])
sensor2 = pd.read_csv(DATA_DIR / 'g1_sensor2.csv', names = ['time', 'normal', 'type1', 'type2', 'type3'])
sensor3 = pd.read_csv(DATA_DIR / 'g1_sensor3.csv', names = ['time', 'normal', 'type1', 'type2', 'type3'])
sensor4 = pd.read_csv(DATA_DIR / 'g1_sensor4.csv', names = ['time', 'normal', 'type1', 'type2', 'type3'])

# 데이터 선형보간
from scipy import interpolate
x_new = np.arange(0, 140, 0.001)
y_new1 = []; y_new2 = []; y_new3 = []; y_new4 = []
for item in ['normal', 'type1', 'type2', 'type3']:
    f_linear1 = interpolate.interp1d(sensor1['time'], sensor1[item], kind='linear'); y_new1.append(f_linear1(x_new))
    f_linear2 = interpolate.interp1d(sensor2['time'], sensor2[item], kind='linear'); y_new2.append(f_linear2(x_new))
    f_linear3 = interpolate.interp1d(sensor3['time'], sensor3[item], kind='linear'); y_new3.append(f_linear3(x_new))
    f_linear4 = interpolate.interp1d(sensor4['time'], sensor4[item], kind='linear'); y_new4.append(f_linear4(x_new))

sensor1 = pd.DataFrame(np.array(y_new1).T, columns = ['normal', 'type1', 'type2', 'type3'])
sensor2 = pd.DataFrame(np.array(y_new2).T, columns = ['normal', 'type1', 'type2', 'type3'])
sensor3 = pd.DataFrame(np.array(y_new3).T, columns = ['normal', 'type1', 'type2', 'type3'])
sensor4 = pd.DataFrame(np.array(y_new4).T, columns = ['normal', 'type1', 'type2', 'type3'])

# 데이터 조정
normal_ = pd.concat([sensor1['normal'], sensor2['normal'], sensor3['normal'], sensor4['normal']], axis=1)
type1_ = pd.concat([sensor1['type1'], sensor2['type1'], sensor3['type1'], sensor4['type1']], axis=1)
type2_ = pd.concat([sensor1['type2'], sensor2['type2'], sensor3['type2'], sensor4['type2']], axis=1)
type3_ = pd.concat([sensor1['type3'], sensor2['type3'], sensor3['type3'], sensor4['type3']], axis=1)

normal_.columns = ['s1', 's2', 's3', 's4']; type1_.columns = ['s1', 's2', 's3', 's4']
type2_.columns = ['s1', 's2', 's3', 's4']; type3_.columns = ['s1', 's2', 's3', 's4']

# [데이터 전처리]
# 데이터 필터링(이동평균필터)
M =15

normal_s1 = np.convolve(normal_['s1'], np.ones(M), 'valid') / M; normal_s1 = normal_s1.reshape(len(normal_s1),1)
normal_s2 = np.convolve(normal_['s2'], np.ones(M), 'valid') / M; normal_s2 = normal_s2.reshape(len(normal_s2),1)
normal_s3 = np.convolve(normal_['s3'], np.ones(M), 'valid') / M; normal_s3 = normal_s3.reshape(len(normal_s3),1)
normal_s4 = np.convolve(normal_['s4'], np.ones(M), 'valid') / M; normal_s4 = normal_s4.reshape(len(normal_s4),1)

type1_s1 = np.convolve(type1_['s1'], np.ones(M), 'valid') / M; type1_s1 = type1_s1.reshape(len(type1_s1),1)
type1_s2 = np.convolve(type1_['s2'], np.ones(M), 'valid') / M; type1_s2 = type1_s2.reshape(len(type1_s2),1)
type1_s3 = np.convolve(type1_['s3'], np.ones(M), 'valid') / M; type1_s3 = type1_s3.reshape(len(type1_s3),1)
type1_s4 = np.convolve(type1_['s4'], np.ones(M), 'valid') / M; type1_s4 = type1_s4.reshape(len(type1_s4),1)

type2_s1 = np.convolve(type2_['s1'], np.ones(M), 'valid') / M; type2_s1 = type2_s1.reshape(len(type2_s1),1)
type2_s2 = np.convolve(type2_['s2'], np.ones(M), 'valid') / M; type2_s2 = type2_s2.reshape(len(type2_s2),1)
type2_s3 = np.convolve(type2_['s3'], np.ones(M), 'valid') / M; type2_s3 = type2_s3.reshape(len(type2_s3),1)
type2_s4 = np.convolve(type2_['s4'], np.ones(M), 'valid') / M; type2_s4 = type2_s4.reshape(len(type2_s4),1)

type3_s1 = np.convolve(type3_['s1'], np.ones(M), 'valid') / M; type3_s1 = type3_s1.reshape(len(type3_s1),1)
type3_s2 = np.convolve(type3_['s2'], np.ones(M), 'valid') / M; type3_s2 = type3_s2.reshape(len(type3_s2),1)
type3_s3 = np.convolve(type3_['s3'], np.ones(M), 'valid') / M; type3_s3 = type3_s3.reshape(len(type3_s3),1)
type3_s4 = np.convolve(type3_['s4'], np.ones(M), 'valid') / M; type3_s4 = type3_s4.reshape(len(type3_s4),1)

normal_temp = np.concatenate((normal_s1,normal_s2,normal_s3,normal_s4), axis =1)
type1_temp = np.concatenate((type1_s1,type1_s2,type1_s3,type1_s4), axis =1)
type2_temp = np.concatenate((type2_s1,type2_s2,type2_s3,type2_s4), axis =1)
type3_temp = np.concatenate((type3_s1,type3_s2,type3_s3,type3_s4), axis =1)

# 데이터 정규화
from sklearn.preprocessing import MinMaxScaler
scaler = MinMaxScaler()
scaler.fit(normal_)
normal = scaler.transform(normal_temp)
type1 = scaler.transform(type1_temp)
type2 = scaler.transform(type2_temp)
type3 = scaler.transform(type3_temp)

# 데이터 조정
normal = normal[30000:130000][:]
type1 = type1[30000:130000][:]
type2 = type2[30000:130000][:]
type3 = type3[30000:130000][:]

# 데이터 분배
normal_train = normal[:][:60000]; normal_valid = normal[:][60000:80000]; normal_test = normal[:][80000:]
type1_train = type1[:][:60000]; type1_valid = type1[:][60000:80000]; type1_test = type1[:][80000:]
type2_train = type2[:][:60000]; type2_valid = type2[:][60000:80000]; type2_test = type2[:][80000:]
type3_train = type3[:][:60000]; type3_valid = type3[:][60000:80000]; type3_test = type3[:][80000:]

train = np.concatenate((normal_train,type1_train,type2_train,type3_train))
valid = np.concatenate((normal_valid,type1_valid,type2_valid,type3_valid))
test = np.concatenate((normal_test,type1_test,type2_test,type3_test))

# 데이터 라벨링
train_label = np.concatenate((np.full((60000,1),0), np.full((60000,1),1), np.full((60000,1),2), np.full((60000,1),3)))
valid_label = np.concatenate((np.full((20000,1),0), np.full((20000,1),1), np.full((20000,1),2), np.full((20000,1),3)))
test_label = np.concatenate((np.full((20000,1),0), np.full((20000,1),1), np.full((20000,1),2), np.full((20000,1),3)))

# 데이터 뒤섞기
idx = np.arange(train.shape[0]); np.random.shuffle(idx);
train = train[:][idx]; train_label = train_label[:][idx]

idx_v = np.arange(valid.shape[0]); np.random.shuffle(idx_v);
valid = valid[:][idx_v]; valid_label = valid_label[:][idx_v]

idx_t = np.arange(test.shape[0]); np.random.shuffle(idx_t);
test = test[:][idx_t]; test_label = test_label[:][idx_t]

# 데이터 형태 변환
x_train = torch.from_numpy(train).float()
y_train = torch.from_numpy(train_label).float().T[0]
x_valid = torch.from_numpy(valid).float()
y_valid = torch.from_numpy(valid_label).float().T[0]
x_test = torch.from_numpy(test).float()
y_test = torch.from_numpy(test_label).float().T[0]

# 데이터 묶기
from torch.utils.data import TensorDataset
from torch.utils.data import DataLoader

train = TensorDataset(x_train, y_train)
train_dataloader = DataLoader(train, batch_size =5000, shuffle=True)

valid = TensorDataset(x_valid, y_valid)
valid_dataloader = DataLoader(valid, batch_size =len(x_valid), shuffle=False)

test = TensorDataset(x_test, y_test)
test_dataloader = DataLoader(test, batch_size =len(x_valid), shuffle=False)

# 심층신경망 모델 구축
class KAMP_DNN(nn.Module):
    def __init__(self):
        super(KAMP_DNN, self).__init__()
        self.layer1 = nn.Linear(in_features =4, out_features =100)
        self.layer2 = nn.Linear(in_features =100, out_features =100)
        self.layer3 = nn.Linear(in_features =100, out_features =100)
        self.layer4 = nn.Linear(in_features =100, out_features =4)
        
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
    
model_check = KAMP_DNN()
print(model_check)

# AI 분석 모델 학습
def train_model(model, criterion, optimizer, num_epochs, train_dataloader, PATH):
    loss_values = []
    loss_values_v = []
    check =0; accuracy_past = 0
    for epoch in range(1, num_epochs +1):
        #---------------------- 모델 학습 ---------------------#
        model.train()
        batch_number = 0
        running_loss = 0.0
        for batch_idx, samples in enumerate(train_dataloader):
            x_train, y_train = samples
            x_train, y_train = x_train.to(device), y_train.to(device)
            # 변수 초기화
            optimizer.zero_grad()
            y_hat = model.forward(x_train)
            loss = criterion(y_hat,y_train.long())
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            batch_number += 1
        loss_values.append(running_loss / batch_number)
        #---------------------- 모델 검증 ---------------------#
        model.eval()
        accuracy = 0.0
        total = 0.0
        for batch_idx, data in enumerate(valid_dataloader):
            x_valid, y_valid = data
            x_valid, y_valid = x_valid.to(device), y_valid.to(device)
            
            v_hat = model.forward(x_valid)
            v_loss = criterion(v_hat,y_valid.long())
            _, predicted = torch.max(v_hat.data, 1)
            total += y_valid.size(0)
            accuracy += (predicted == y_valid).sum().item()
        loss_values_v.append(loss.item())
        accuracy = (accuracy / total)
        #----------------Check for early stopping---------------#
        if epoch % 1 == 0:
            print('[Epoch {}/{}] [Train_Loss: {:.6f} /Valid_Loss: {:.6f}]'.format(epoch, num_epochs, loss.item(),v_loss.item()))
            print('[Epoch {}/{}] [Accuracy : {:.6f}]'.format(epoch, num_epochs, accuracy))
        if accuracy_past > accuracy:
            check += 1
        else:
            check = 0
            accuracy_past = accuracy
        if check > 50:
            print('This is time to do early stopping')
    torch.save(model.state_dict(), PATH + 'model_weights.pt')
    joblib.dump(scaler, PATH + 'scaler.pkl')
    return loss_values, loss_values_v

# 심층신경망 모델 학습
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'사용 디바이스: {device}')
DNN_model = KAMP_DNN().to(device)
num_epochs = 200
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(DNN_model.parameters())
os.makedirs(OUTPUT_DIR, exist_ok=True)
PATH = str(OUTPUT_DIR) + os.sep
DNN_loss_values, DNN_loss_values_v = train_model(DNN_model, criterion, optimizer, num_epochs, train_dataloader, PATH)

# MinIO artifacts 버킷에 업로드
if args.upload_minio or os.environ.get('UPLOAD_MINIO') == 'true' or 'MINIO_SECRET_KEY' in os.environ:
    print("MinIO 업로드 중...")
    client.fput_object(ARTIFACT_BUCKET, 'model_weights.pt', PATH + 'model_weights.pt')
    client.fput_object(ARTIFACT_BUCKET, 'scaler.pkl', PATH + 'scaler.pkl')
    print(f"업로드 완료! model_weights.pt, scaler.pkl → {ARTIFACT_BUCKET} 버킷")
else:
    print(f"학습 결과 저장 완료: {PATH}")
