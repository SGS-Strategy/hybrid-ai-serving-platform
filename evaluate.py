import torch
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix

# 테스트 데이터로 최종 정확도 평가
def test_model(PATH, test_dataloader):
    model = torch.load(PATH + 'model.pt')
    model.eval()
    total    = 0.0
    accuracy = 0.0

    for batch_idx, data in enumerate(test_dataloader):
        x_test, y_test = data
        t_hat  = model(x_test)
        _, predicted = torch.max(t_hat.data, 1)
        total    += y_test.size(0)
        accuracy += (predicted == y_test).sum().item()

    accuracy = accuracy / total
    print(accuracy)

# Confusion Matrix 시각화 및 저장
def draw_confusion_matrix(model, xt, yt, PATH):
    y_pred = []
    y_true = []

    model.eval()
    y_hat  = model(xt)
    output = (torch.max(torch.exp(y_hat), 1)[1]).data.cpu().numpy()
    y_pred.extend(output)
    labels = yt.data.cpu().numpy()
    y_true.extend(labels)

    classes = ('Normal', 'Type1', 'Type2', 'Type3')
    plt.figure(figsize=(7, 5))
    dlen  = float(len(xt))
    cm    = confusion_matrix(y_true, y_pred)
    df_cm = pd.DataFrame(cm / dlen, index=classes, columns=classes)

    sns.heatmap(df_cm, annot=True, cmap=plt.cm.Blues)
    plt.title("Confusion Matrix", size=24, fontweight='bold')
    plt.xlabel("Predicted Label", size=16)
    plt.ylabel("Actual Label",   size=16)
    plt.rc('xtick', labelsize=12)
    plt.rc('ytick', labelsize=12)
    plt.yticks(rotation=0)
    plt.savefig(PATH + 'cm_output.png')

# 학습/검증 Loss 그래프 시각화 및 저장
def plot_loss_graph(loss_values, loss_values_v, PATH):
    plt.figure()
    plt.plot(loss_values)
    plt.plot(loss_values_v)
    plt.title("Training & Validation Loss")
    plt.ylabel("loss",  fontsize="large")
    plt.xlabel("epoch", fontsize="large")
    plt.legend(["train", "validation"])
    plt.tight_layout()
    plt.savefig(PATH + 'lossplot_output.png')