import numpy as np
import torch
import torch.nn as nn
import os
from torch.utils.data import TensorDataset, DataLoader
from model import KAMP_DNN

# 학습 6 : 검증 2 : 테스트 2 비율로 데이터 분할 및 라벨링
def split_data(normal, type1, type2, type3):
    normal_train = normal[:42000]; normal_valid = normal[42000:56000]; normal_test = normal[56000:]
    type1_train  = type1[:42000];  type1_valid  = type1[42000:56000];  type1_test  = type1[56000:]
    type2_train  = type2[:42000];  type2_valid  = type2[42000:56000];  type2_test  = type2[56000:]
    type3_train  = type3[:42000];  type3_valid  = type3[42000:56000];  type3_test  = type3[56000:]

    train = np.concatenate((normal_train, type1_train, type2_train, type3_train))
    valid = np.concatenate((normal_valid, type1_valid, type2_valid, type3_valid))
    test  = np.concatenate((normal_test,  type1_test,  type2_test,  type3_test))

    # normal=0, type1=1, type2=2, type3=3 으로 라벨링
    train_label = np.concatenate((np.full((42000,1),0), np.full((42000,1),1), np.full((42000,1),2), np.full((42000,1),3)))
    valid_label = np.concatenate((np.full((14000,1),0), np.full((14000,1),1), np.full((14000,1),2), np.full((14000,1),3)))
    test_label  = np.concatenate((np.full((14000,1),0), np.full((14000,1),1), np.full((14000,1),2), np.full((14000,1),3)))

    return train, valid, test, train_label, valid_label, test_label

# 순서 의존성 제거를 위해 데이터 무작위 셔플
def shuffle_data(train, valid, test, train_label, valid_label, test_label):
    idx = np.arange(train.shape[0]); np.random.shuffle(idx)
    train, train_label = train[idx], train_label[idx]

    idx_v = np.arange(valid.shape[0]); np.random.shuffle(idx_v)
    valid, valid_label = valid[idx_v], valid_label[idx_v]

    idx_t = np.arange(test.shape[0]); np.random.shuffle(idx_t)
    test, test_label = test[idx_t], test_label[idx_t]

    return train, valid, test, train_label, valid_label, test_label

# DNN 모델 학습 (early stopping 적용)
def train_model(model, criterion, optimizer, num_epochs, train_dataloader, valid_dataloader, PATH):
    loss_values   = []
    loss_values_v = []
    check         = 0
    accuracy_past = 0

    for epoch in range(1, num_epochs + 1):

        # 학습
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

        # 검증
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

        print('[Epoch {}/{}] [Train_Loss: {:.6f} / Valid_Loss: {:.6f}]'.format(
            epoch, num_epochs, loss.item(), v_loss.item()))
        print('[Epoch {}/{}] [Accuracy : {:.6f}]'.format(epoch, num_epochs, accuracy))

        # Early Stopping - 50 epoch 연속으로 accuracy 개선 없으면 학습 중단
        if accuracy_past > accuracy:
            check += 1
        else:
            check = 0
        accuracy_past = accuracy

        if check > 50:
            print('This is time to do early stopping')
            break

    # 모델 저장
    os.makedirs(PATH, exist_ok=True)
    torch.save(model, PATH + 'model.pt')
    return loss_values, loss_values_v