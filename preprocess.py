import numpy as np
import pandas as pd
from scipy import interpolate
from sklearn.preprocessing import MinMaxScaler

# CSV 파일 불러오기
sensor1 = pd.read_csv('Downloads/private/g1_sensor1.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
sensor2 = pd.read_csv('Downloads/private/g1_sensor2.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
sensor3 = pd.read_csv('Downloads/private/g1_sensor3.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
sensor4 = pd.read_csv('Downloads/private/g1_sensor4.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])

# 전처리 1 - 계측 시간의 동일화를 위한 데이터 선형보간
# 각 센서의 실제 시간 범위 확인
t_min = max(sensor1['time'].min(), sensor2['time'].min(), 
            sensor3['time'].min(), sensor4['time'].min())

x_new = np.arange(t_min, 98, 0.001)  # t_max → 98로 변경
y_new1 = []; y_new2 = []; y_new3 = []; y_new4 = []

for item in ['normal', 'type1', 'type2', 'type3']:
    f_linear1 = interpolate.interp1d(sensor1['time'], sensor1[item], kind='linear')
    y_new1.append(f_linear1(x_new))
    f_linear2 = interpolate.interp1d(sensor2['time'], sensor2[item], kind='linear')
    y_new2.append(f_linear2(x_new))
    f_linear3 = interpolate.interp1d(sensor3['time'], sensor3[item], kind='linear')
    y_new3.append(f_linear3(x_new))
    f_linear4 = interpolate.interp1d(sensor4['time'], sensor4[item], kind='linear')
    y_new4.append(f_linear4(x_new))

sensor1 = pd.DataFrame(np.array(y_new1).T, columns=['normal', 'type1', 'type2', 'type3'])
sensor2 = pd.DataFrame(np.array(y_new2).T, columns=['normal', 'type1', 'type2', 'type3'])
sensor3 = pd.DataFrame(np.array(y_new3).T, columns=['normal', 'type1', 'type2', 'type3'])
sensor4 = pd.DataFrame(np.array(y_new4).T, columns=['normal', 'type1', 'type2', 'type3'])

# 실제 취득된 형태로 데이터 재조정
normal_ = pd.concat([sensor1['normal'], sensor2['normal'], sensor3['normal'], sensor4['normal']], axis=1)
type1_  = pd.concat([sensor1['type1'],  sensor2['type1'],  sensor3['type1'],  sensor4['type1']],  axis=1)
type2_  = pd.concat([sensor1['type2'],  sensor2['type2'],  sensor3['type2'],  sensor4['type2']],  axis=1)
type3_  = pd.concat([sensor1['type3'],  sensor2['type3'],  sensor3['type3'],  sensor4['type3']],  axis=1)

normal_.columns = ['s1', 's2', 's3', 's4']
type1_.columns  = ['s1', 's2', 's3', 's4']
type2_.columns  = ['s1', 's2', 's3', 's4']
type3_.columns  = ['s1', 's2', 's3', 's4']

# 전처리 2 - 데이터 필터링 (노이즈 제거)
M = 15

def moving_avg(series, M):
    result = np.convolve(series, np.ones(M), 'valid') / M
    return result.reshape(len(result), 1)

normal_s1 = moving_avg(normal_['s1'], M)
normal_s2 = moving_avg(normal_['s2'], M)
normal_s3 = moving_avg(normal_['s3'], M)
normal_s4 = moving_avg(normal_['s4'], M)

type1_s1 = moving_avg(type1_['s1'], M)
type1_s2 = moving_avg(type1_['s2'], M)
type1_s3 = moving_avg(type1_['s3'], M)
type1_s4 = moving_avg(type1_['s4'], M)

type2_s1 = moving_avg(type2_['s1'], M)
type2_s2 = moving_avg(type2_['s2'], M)
type2_s3 = moving_avg(type2_['s3'], M)
type2_s4 = moving_avg(type2_['s4'], M)

type3_s1 = moving_avg(type3_['s1'], M)
type3_s2 = moving_avg(type3_['s2'], M)
type3_s3 = moving_avg(type3_['s3'], M)
type3_s4 = moving_avg(type3_['s4'], M)

normal_temp = np.concatenate((normal_s1, normal_s2, normal_s3, normal_s4), axis=1)
type1_temp  = np.concatenate((type1_s1,  type1_s2,  type1_s3,  type1_s4),  axis=1)
type2_temp  = np.concatenate((type2_s1,  type2_s2,  type2_s3,  type2_s4),  axis=1)
type3_temp  = np.concatenate((type3_s1,  type3_s2,  type3_s3,  type3_s4),  axis=1)

# 전처리 3 - 데이터 정규화
scaler = MinMaxScaler()
scaler.fit(normal_)

normal = scaler.transform(normal_temp)
type1  = scaler.transform(type1_temp)
type2  = scaler.transform(type2_temp)
type3  = scaler.transform(type3_temp)

# 데이터 사이즈 조정
# 97986개 중 앞뒤 잘라서 70000개 사용
normal = normal_temp[13000:83000][:]
type1  = type1_temp[13000:83000][:]
type2  = type2_temp[13000:83000][:]
type3  = type3_temp[13000:83000][:]
