import pandas as pd
import numpy as np
from scipy import interpolate
from datetime import datetime, timedelta, timezone
import pytz
import os

# ===================== 1. 파일 불러오기 =====================
# KAMP 회전기계 고장유형 AI 데이터셋 (group1) 불러오기
# 각 파일은 time/normal/type1/type2/type3 5개 열로 구성
# - normal: 정상 상태 센서값
# - type1: 질량불균형 고장 상태 센서값
# - type2: 지지불량 고장 상태 센서값
# - type3: 질량불균형 + 지지불량 복합 고장 상태 센서값
DATA_PATH   = 'C:/Users/user/Downloads/data/'
OUTPUT_PATH = 'C:/Users/user/Downloads/'

s1 = pd.read_csv(DATA_PATH + 'g1_sensor1.csv', names=['time','normal','type1','type2','type3'])
s2 = pd.read_csv(DATA_PATH + 'g1_sensor2.csv', names=['time','normal','type1','type2','type3'])
s3 = pd.read_csv(DATA_PATH + 'g1_sensor3.csv', names=['time','normal','type1','type2','type3'])
s4 = pd.read_csv(DATA_PATH + 'g1_sensor4.csv', names=['time','normal','type1','type2','type3'])

# ===================== 2. 선형보간으로 시간축 통일 =====================
# 센서마다 샘플링 속도가 달라 데이터 개수가 제각각임
# 4개 센서의 공통 시간 범위를 찾아 0.001초(1ms) 간격으로 균일하게 재샘플링
# → 모든 센서를 동일한 시간축으로 통일 (1초당 1,000개 데이터)
t_min = max(s1['time'].min(), s2['time'].min(), s3['time'].min(), s4['time'].min())
t_max = min(s1['time'].max(), s2['time'].max(), s3['time'].max(), s4['time'].max())
x_new = np.arange(t_min, t_max, 0.001)
n_base = len(x_new)
print(f'기본 데이터 크기: {n_base} ({n_base*0.001:.1f}초)')

def interp_col(sensor, col):
    # 각 센서의 특정 열(normal/type1/type2/type3)을 선형보간
    f = interpolate.interp1d(sensor['time'], sensor[col], kind='linear')
    return f(x_new)

s1_interp = {col: interp_col(s1, col) for col in ['normal','type1','type2','type3']}
s2_interp = {col: interp_col(s2, col) for col in ['normal','type1','type2','type3']}
s3_interp = {col: interp_col(s3, col) for col in ['normal','type1','type2','type3']}
s4_interp = {col: interp_col(s4, col) for col in ['normal','type1','type2','type3']}

# ===================== 3. 5분(300초)으로 반복 =====================
# 원본 데이터는 약 42초 분량이므로 5분(300초) 분량으로 확장
# np.tile()로 원본을 반복한 뒤 미세한 랜덤 노이즈를 추가
# → 단순 반복이 아닌 자연스러운 센서 데이터처럼 보이게 처리
TARGET_SEC = 300        # 목표 시간 (초)
n_target   = TARGET_SEC * 1000  # 목표 데이터 개수 (300,000개)
n_repeat   = int(np.ceil(n_target / n_base))  # 반복 횟수 계산

def repeat_with_noise(arr, n_repeat, noise_scale=0.01):
    # 배열을 n_repeat번 반복 후 n_target 길이로 자르기
    repeated = np.tile(arr, n_repeat)[:n_target]
    # 원본 표준편차의 1% 수준의 노이즈 추가 (자연스러운 변동 표현)
    noise    = np.random.normal(0, noise_scale * np.std(arr), len(repeated))
    return repeated + noise

np.random.seed(42)  # 재현 가능한 결과를 위한 시드 고정
s1_rep = {col: repeat_with_noise(s1_interp[col], n_repeat) for col in ['normal','type1','type2','type3']}
s2_rep = {col: repeat_with_noise(s2_interp[col], n_repeat) for col in ['normal','type1','type2','type3']}
s3_rep = {col: repeat_with_noise(s3_interp[col], n_repeat) for col in ['normal','type1','type2','type3']}
s4_rep = {col: repeat_with_noise(s4_interp[col], n_repeat) for col in ['normal','type1','type2','type3']}

n = n_target
print(f'5분 데이터 크기: {n} ({n*0.001:.1f}초)')

# ===================== 4. 시계열 고장 구간 생성 =====================
# 실제 공장처럼 정상 데이터 중간에 고장 구간을 삽입
# 고장 타입별 1회씩 총 3회 발생 (Type1 → Type2 → Type3 순서)
# 고장 지속시간: 5~7초 (실제 기계 고장처럼 연속된 구간)
# 배치 위치: 전체 5분을 4등분해서 70초/140초/210초 근처에 균등 배치
# → 정상 94% / 고장 6% 비율 달성
FAULT_MIN_MS = 5000   # 고장 최소 지속시간 (5초)
FAULT_MAX_MS = 7000   # 고장 최대 지속시간 (7초)

np.random.seed(42)
labels = np.zeros(n, dtype=int)  # 전체를 0(정상)으로 초기화

fault_types    = [1, 2, 3]
fault_schedule = []

i = (n - 20000) // 4  # 첫 번째 고장 시작 위치 (약 70초 지점)
for fault_type in fault_types:
    fault_duration = np.random.randint(FAULT_MIN_MS, FAULT_MAX_MS)  # 고장 지속시간 랜덤 결정
    end = min(i + fault_duration, n)
    labels[i:end] = fault_type  # 해당 구간을 고장 타입으로 설정
    fault_schedule.append((i, end, fault_type))
    i += (n - 20000) // 4  # 다음 고장 위치로 이동 (약 70초 간격)

# ===================== 5. 비율 확인 =====================
print(f'정상: {np.sum(labels==0)}개 ({np.sum(labels==0)/n*100:.1f}%)')
print(f'Type1: {np.sum(labels==1)}개 ({np.sum(labels==1)/n*100:.1f}%)')
print(f'Type2: {np.sum(labels==2)}개 ({np.sum(labels==2)/n*100:.1f}%)')
print(f'Type3: {np.sum(labels==3)}개 ({np.sum(labels==3)/n*100:.1f}%)')
print()
print('고장 스케줄:')
for s, e, t in fault_schedule:
    print(f'  Type{t}: {s/1000:.1f}초 ~ {e/1000:.1f}초 (지속: {(e-s)/1000:.1f}초)')

# ===================== 6. 레이블에 따라 센서값 선택 =====================
# 각 시간 포인트의 레이블(0/1/2/3)에 따라 원본 데이터의 해당 열 값을 선택
# - 레이블 0(정상) → normal 열 값 사용
# - 레이블 1(Type1) → type1 열 값 사용
# - 레이블 2(Type2) → type2 열 값 사용
# - 레이블 3(Type3) → type3 열 값 사용
def select_val(interp, labels):
    return np.where(labels==0, interp['normal'],
           np.where(labels==1, interp['type1'],
           np.where(labels==2, interp['type2'], interp['type3'])))

sensor1_vals = select_val(s1_rep, labels)
sensor2_vals = select_val(s2_rep, labels)
sensor3_vals = select_val(s3_rep, labels)
sensor4_vals = select_val(s4_rep, labels)

# ===================== 7. 시간 컬럼 생성 =====================
# 절대시간: 코드 실행 시점의 한국 시간(KST) 기준으로 1ms씩 증가
# 상대시간: 0.000초부터 시작해서 0.001초씩 증가 (0~299.999초)
kst           = pytz.timezone("Asia/Seoul")
base_time     = datetime.now(kst).replace(microsecond=0, tzinfo=None)
abs_times     = [base_time + timedelta(seconds=i/1000) for i in range(n)]
abs_times_str = [t.strftime('%Y-%m-%d %H:%M:%S') for t in abs_times]
rel_times     = np.round(np.arange(0, n * 0.001, 0.001)[:n], 3)

# ===================== 8. 최종 CSV 저장 =====================
# 컬럼 구성:
# - absolute_time: 절대시간 (KST, 초 단위)
# - relative_time: 상대시간 (0~299.999초)
# - sensor1~4: 4개 센서의 측정값
df = pd.DataFrame({
    'absolute_time': abs_times_str,
    'relative_time': rel_times,
    'sensor1':       sensor1_vals,
    'sensor2':       sensor2_vals,
    'sensor3':       sensor3_vals,
    'sensor4':       sensor4_vals
})

df.to_csv(OUTPUT_PATH + 'sensor_data_output.csv', index=False)
print(f'\n완료! 총 {len(df)}행 저장됨')
print(f'저장 위치: {OUTPUT_PATH}sensor_data_output.csv')
print(df.head(5))