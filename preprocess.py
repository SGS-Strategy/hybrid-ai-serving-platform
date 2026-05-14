import numpy as np
import pandas as pd
from scipy import interpolate
from sklearn.preprocessing import MinMaxScaler

# CSV 파일 불러오기
def load_data(base_path):
    sensor1 = pd.read_csv(base_path + 'g1_sensor1.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
    sensor2 = pd.read_csv(base_path + 'g1_sensor2.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
    sensor3 = pd.read_csv(base_path + 'g1_sensor3.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
    sensor4 = pd.read_csv(base_path + 'g1_sensor4.csv', names=['time', 'normal', 'type1', 'type2', 'type3'])
    return sensor1, sensor2, sensor3, sensor4

# 전처리 1 - 센서별 샘플링 속도가 달라 선형보간으로 시간축 통일 (0~98초, 0.001 간격)
def interpolate_sensor(sensor1, sensor2, sensor3, sensor4):
    t_min = max(sensor1['time'].min(), sensor2['time'].min(),
                sensor3['time'].min(), sensor4['time'].min())
    x_new = np.arange(t_min, 98, 0.001)

    def interp(sensor):
        y_new = []
        for item in ['normal', 'type1', 'type2', 'type3']:
            f = interpolate.interp1d(sensor['time'], sensor[item], kind='linear')
            y_new.append(f(x_new))
        return pd.DataFrame(np.array(y_new).T, columns=['normal', 'type1', 'type2', 'type3'])

    return interp(sensor1), interp(sensor2), interp(sensor3), interp(sensor4)

# 전처리 2 - 이동평균으로 노이즈 제거 (M=15)
def moving_avg(series, M=15):
    result = np.convolve(series, np.ones(M), 'valid') / M
    return result.reshape(len(result), 1)

def apply_moving_avg(sensor1, sensor2, sensor3, sensor4):
    def concat_sensors(s1, s2, s3, s4, col):
        return np.concatenate((moving_avg(s1[col]), moving_avg(s2[col]),
                               moving_avg(s3[col]), moving_avg(s4[col])), axis=1)
    normal_temp = concat_sensors(sensor1, sensor2, sensor3, sensor4, 'normal')
    type1_temp  = concat_sensors(sensor1, sensor2, sensor3, sensor4, 'type1')
    type2_temp  = concat_sensors(sensor1, sensor2, sensor3, sensor4, 'type2')
    type3_temp  = concat_sensors(sensor1, sensor2, sensor3, sensor4, 'type3')
    return normal_temp, type1_temp, type2_temp, type3_temp

# 전처리 3 - MinMaxScaler로 데이터 정규화 (0~1 범위)
def normalize(normal_temp, type1_temp, type2_temp, type3_temp, normal_):
    scaler = MinMaxScaler()
    scaler.fit(normal_)
    return (scaler.transform(normal_temp), scaler.transform(type1_temp),
            scaler.transform(type2_temp),  scaler.transform(type3_temp))

# 앞뒤 불안정 구간 제거 후 70000개로 슬라이싱
def slice_data(normal, type1, type2, type3):
    return (normal[13000:83000], type1[13000:83000],
            type2[13000:83000], type3[13000:83000])