# KAMP DNN 모델 🔧

## 프로젝트 설명
KAMP 회전기계 고장유형 AI 데이터셋을 활용하여 센서 데이터 기반으로
회전기계의 고장 유형을 분류하는 DNN(Deep Neural Network) 모델

## 사용 기술
- Python 3.7.3
- PyTorch
- Scikit-learn
- Pandas / Numpy
- Scipy
- Matplotlib / Seaborn

## 데이터셋
- **출처**: KAMP 회전기계 고장유형 AI 데이터셋
- **센서**: sensor1 ~ sensor4 (4개 센서)
- **클래스**: 4가지 (Normal, Type1, Type2, Type3)
- **데이터 크기**
  - Train: 240,000개
  - Validation: 80,000개
  - Test: 80,000개

## 데이터 전처리
1. 선형 보간 (Linear Interpolation)
2. 이동평균 (Moving Average, M=15)
3. 정규화 (MinMaxScaler)
4. 데이터 슬라이싱 및 셔플

## 모델 구조
```
Input(4) → Linear(100) → ReLU → Dropout(0.2)
→ Linear(100) → ReLU → Dropout(0.2)
→ Linear(100) → ReLU → Dropout(0.2)
→ Linear(4) → Output
```

## 학습 설정
- Optimizer: Adam
- Loss Function: CrossEntropyLoss
- Batch Size: 5000
- Max Epochs: 1000
- Early Stopping: 50 epochs

## 모델 성능
- 정확도: 75.9%

## 실행 방법
1. 라이브러리 설치
```
pip install torch scikit-learn pandas numpy matplotlib seaborn scipy
```

2. Jupyter Notebook 실행
```
jupyter notebook
```

3. 3rd_project.ipynb 실행
