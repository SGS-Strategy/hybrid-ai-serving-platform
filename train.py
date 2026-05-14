import numpy as np
import torch
import torch.nn as nn
import os
from torch.utils.data import TensorDataset, DataLoader
from model import KAMP_DNN

# 데이터 분배 (학습/검증/테스트)
# 학습 : 검증 : 테스트 = 6 : 2 : 2
normal_train = normal[:42000];  normal_valid = normal[42000:56000];  normal_test = normal[56000:]
type1_train  = type1[:42000];   type1_valid  = type1[42000:56000];   type1_test  = type1[56000:]
type2_train  = type2[:42000];   type2_valid  = type2[42000:56000];   type2_test  = type2[56000:]
type3_train  = type3[:42000];   type3_valid  = type3[42000:56000];   type3_test  = type3[56000:]

train = np.concatenate((normal_train, type1_train, type2_train, type3_train))
valid = np.concatenate((normal_valid, type1_valid, type2_valid, type3_valid))
test  = np.concatenate((normal_test,  type1_test,  type2_test,  type3_test))

# 데이터 라벨링
# normal = 0 / type 1 = 1 / type 2 = 2 / type 3 = 3
train_label = np.concatenate((np.full((42000, 1), 0), np.full((42000, 1), 1), np.full((42000, 1), 2), np.full((42000, 1), 3)))
valid_label = np.concatenate((np.full((14000, 1), 0), np.full((14000, 1), 1), np.full((14000, 1), 2), np.full((14000, 1), 3)))
test_label  = np.concatenate((np.full((14000, 1), 0), np.full((14000, 1), 1), np.full((14000, 1), 2), np.full((14000, 1), 3)))

# 데이터 뒤섞기
# 순서에 의존하지 않고 임의의 데이터가 입력되는 것으로 간주하기 위함
idx = np.arange(train.shape[0])
np.random.shuffle(idx)
train       = train[idx]
train_label = train_label[idx]

idx_v = np.arange(valid.shape[0])
np.random.shuffle(idx_v)
valid       = valid[idx_v]
valid_label = valid_label[idx_v]

idx_t = np.arange(test.shape[0])
np.random.shuffle(idx_t)
test       = test[idx_t]
test_label = test_label[idx_t]

# 데이터 형태 변환 (array -> tensor 형태)
x_train = torch.from_numpy(train).float()
y_train = torch.from_numpy(train_label).float().T[0]

x_valid = torch.from_numpy(valid).float()
y_valid = torch.from_numpy(valid_label).float().T[0]

x_test = torch.from_numpy(test).float()
y_test = torch.from_numpy(test_label).float().T[0]

# 데이터 묶기
train          = TensorDataset(x_train, y_train)
train_dataloader = DataLoader(train, batch_size=5000, shuffle=True)

valid          = TensorDataset(x_valid, y_valid)
valid_dataloader = DataLoader(valid, batch_size=len(x_valid), shuffle=False)

test           = TensorDataset(x_test, y_test)
test_dataloader  = DataLoader(test,  batch_size=len(x_valid), shuffle=False)

# 모델 학습
def train_model(model, criterion, optimizer, num_epochs, train_dataloader, PATH):
    loss_values   = []
    loss_values_v = []
    check         = 0
    accuracy_past = 0

    for epoch in range(1, num_epochs + 1):

        #---------------------- 모델 학습 ----------------------#
        model.train()
        batch_number = 0
        running_loss = 0.0

        for batch_idx, samples in enumerate(train_dataloader):
            x_train, y_train = samples
            optimizer.zero_grad()
            y_hat = model.forward(x_train)
            loss  = criterion(y_hat, y_train.long())
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            batch_number += 1

        loss_values.append(running_loss / batch_number)

        #---------------------- 모델 검증 ----------------------#
        model.eval()
        accuracy = 0.0
        total    = 0.0

        for batch_idx, data in enumerate(valid_dataloader):
            x_valid, y_valid = data
            v_hat  = model.forward(x_valid)
            v_loss = criterion(v_hat, y_valid.long())
            _, predicted = torch.max(v_hat.data, 1)
            total    += y_valid.size(0)
            accuracy += (predicted == y_valid).sum().item()

        loss_values_v.append(v_loss.item())
        accuracy = accuracy / total

        #---------------- Check for early stopping --------------#
        if epoch % 1 == 0:
            print('[Epoch {}/{}] [Train_Loss: {:.6f} / Valid_Loss: {:.6f}]'.format(
                epoch, num_epochs, loss.item(), v_loss.item()))
            print('[Epoch {}/{}] [Accuracy : {:.6f}]'.format(
                epoch, num_epochs, accuracy))

        if accuracy_past > accuracy:
            check += 1
        else:
            check = 0
        accuracy_past = accuracy

        if check > 50:
            print('This is time to do early stopping')
            break

    torch.save(model, PATH + 'model.pt')
    return loss_values, loss_values_v

# DNN 모델 학습 실행
os.makedirs('save/DNN/', exist_ok=True)

DNN_model  = KAMP_DNN()
num_epochs = 200
criterion  = nn.CrossEntropyLoss()
optimizer  = torch.optim.Adam(DNN_model.parameters())
PATH       = 'save/DNN/'

DNN_loss_values, DNN_loss_values_v = train_model(DNN_model, criterion, optimizer, num_epochs, train_dataloader, PATH)
