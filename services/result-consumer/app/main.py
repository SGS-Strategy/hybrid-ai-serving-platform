import logging
import os
import time


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("result-consumer")


def run() -> None:
    interval_seconds = int(os.getenv("RESULT_CONSUMER_POLL_INTERVAL_SECONDS", "30"))
    logger.info(
        "result consumer started bootstrap_servers=%s result_topic=%s consumer_group=%s",
        os.getenv("BOOTSTRAP_SERVERS", "replace-me:9092"),
        os.getenv("RESULT_TOPIC", "inference-results"),
        os.getenv("RESULT_CONSUMER_GROUP", "result-consumers"),
    )

    while True:
        logger.info("waiting for result messages")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
