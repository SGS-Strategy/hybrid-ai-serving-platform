import json
import logging
import os
import time
from typing import Any

import httpx


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("inference-worker")


def _predict_url() -> str:
    base_url = os.getenv(
        "PREDICTOR_URL",
        "http://predictor-predictor-default.inference.svc.cluster.local",
    ).rstrip("/")
    endpoint = os.getenv("PREDICTOR_ENDPOINT", "/v1/models/default:predict")
    return f"{base_url}{endpoint}"


def build_sample_payload() -> dict[str, Any]:
    return {
        "inputs": [1, 2, 3],
        "parameters": {
            "source": "bootstrap-worker",
            "request_topic": os.getenv("REQUEST_TOPIC", "inference-requests"),
        },
    }


def run() -> None:
    interval_seconds = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "30"))
    logger.info(
        "worker started bootstrap_servers=%s request_topic=%s result_topic=%s",
        os.getenv("BOOTSTRAP_SERVERS", "replace-me:9092"),
        os.getenv("REQUEST_TOPIC", "inference-requests"),
        os.getenv("RESULT_TOPIC", "inference-results"),
    )

    while True:
        payload = build_sample_payload()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(_predict_url(), json=payload)
                response.raise_for_status()
                logger.info("processed sample job result=%s", json.dumps(response.json()))
        except Exception as exc:  # noqa: BLE001
            logger.exception("worker iteration failed: %s", exc)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
