import os
import csv
import json
import time
import threading
from datetime import datetime, timezone, timedelta
import paho.mqtt.client as mqtt

# 환경변수 설정
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")  # MQTT 브로커 주소
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))        # MQTT 포트 설정 (기본 1883)
DATA_DIR = os.getenv("DATA_DIR", "./public")         # CSV 데이터 저장 폴더
SPEED_FACTOR = float(os.getenv("SPEED_FACTOR", 1.0)) # 재생 속도 조절

# 센서별 CSV 파일 매핑
SENSOR_FILES = {
    "sensor1": "g1_sensor1.csv",
    "sensor2": "g1_sensor2.csv",
    "sensor3": "g1_sensor3.csv",
    "sensor4": "g1_sensor4.csv",
}

# 센서 하나의 CSV를 읽고 MQTT로 publish하는 함수
def publish_sensor_data(client, sensor_id, filename):
    file_path = os.path.join(DATA_DIR, filename)
    topic = f"factory/{sensor_id}"

    print(f"[LOAD] {sensor_id}: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        first_relative_time = None
        prev_relative_time = None

        # 실제 설비 시작 시각 (UTC 기준)
        base_time = datetime.now(timezone.utc)

        print(f"[START] {sensor_id} publish start")

        for row in reader:
            original_relative_time = float(row[0])

            # 첫 데이터 기준 상대시간 리셋
            if first_relative_time is None:
                first_relative_time = original_relative_time
                prev_relative_time = original_relative_time

            # 리셋된 상대시간 (0초부터 시작)
            relative_time = original_relative_time - first_relative_time

            # 실제 센서 sampling 간격 재현
            delay = original_relative_time - prev_relative_time
            if delay > 0:
                time.sleep(delay / SPEED_FACTOR)

            # 실제 운영 절대시간 생성
            event_time = base_time + timedelta(seconds=relative_time)

            # MQTT로 보낼 JSON 데이터 생성
            message = {
                "event_time": event_time.isoformat(),
                "relative_time": round(relative_time, 6),
                "sensor_id": sensor_id,
                "normal": float(row[1]),
                "type1": float(row[2]),
                "type2": float(row[3]),
                "type3": float(row[4]),
            }

            # MQTT publish 실행 (QoS 1: At least once / QoS 2: Exactly once)
            client.publish(topic, json.dumps(message), qos=1)

            prev_relative_time = original_relative_time

    print(f"[DONE] {sensor_id} publish complete")


def main():
    print("[MQTT] connecting...")

    client = mqtt.Client()                     # MQTT 클라이언트 생성
    client.connect(MQTT_BROKER, MQTT_PORT, 60) # MQTT 브로커 연결
    client.loop_start()                        # 비동기 네트워크 루프 시작

    threads = []

    # 4개 센서를 실제 설비처럼 병렬 송신
    for sensor_id, filename in SENSOR_FILES.items():
        t = threading.Thread(
            target=publish_sensor_data,
            args=(client, sensor_id, filename)
        )
        t.start()
        threads.append(t)

    # 모든 센서 송신 완료 대기
    for t in threads:
        t.join()

    client.loop_stop()
    client.disconnect()

    print("[DONE] factory simulator complete")


if __name__ == "__main__":
    main()