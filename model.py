import torch
import torch.nn as nn

# DNN 모델 구조 정의
class KAMP_DNN(nn.Module):
    
    def __init__(self):
        super(KAMP_DNN, self).__init__()
        self.layer1  = nn.Linear(in_features=4,   out_features=100)  # 입력층 (센서 4개)
        self.layer2  = nn.Linear(in_features=100, out_features=100)  # 은닉층 1
        self.layer3  = nn.Linear(in_features=100, out_features=100)  # 은닉층 2
        self.layer4  = nn.Linear(in_features=100, out_features=4)    # 출력층 (클래스 4개)
        self.dropout = nn.Dropout(0.2)   # 과적합 방지
        self.relu    = nn.ReLU()          # 활성화 함수

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