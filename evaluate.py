import torch
from sklearn.metrics import confusion_matrix

# 모델 평가
def test_model(model, PATH):
    model = torch.load(PATH + 'model.pt')

    #---------------------- 모델 시험 ----------------------#
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
    #-------------------------------------------------------#
    print(accuracy)

# 평가 실행
PATH = 'save/DNN/'
test_model(DNN_model, PATH)