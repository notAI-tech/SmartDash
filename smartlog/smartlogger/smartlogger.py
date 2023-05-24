import os
import sys
import time
import uuid
import logging
from liteindex import DefinedIndex


def upload_to_smartdash():
    import argparse

    parser = argparse.ArgumentParser(description="Smartlogger sync service")
    parser.add_argument(
        "--name",
        type=str,
        help="name, given at log or timer initialization time.",
        required=True,
    )
    parser.add_argument(
        "--save_dir", type=str, help="Directory to save logs", required=True
    )
    parser.add_argument(
        "--smartdash_url", type=str, help="Smartdash server URL", required=True
    )
    args = parser.parse_args()
    _upload_to_smartdash(args.name, args.save_dir, args.smartdash_url)


def _upload_to_smartdash(name, log_dir, url, batch_size=100):
    import requests

    def upload_data(name, index_type, db_prefix):
        try:
            index = DefinedIndex(
                f"{name}_{index_type}",
                db_path=os.path.join(log_dir, f"{name}_{db_prefix}.db"),
            )
        except:
            return

        while True:
            backoff_time = 1

            batch = []
            keys = []

            for k, v in index.search(n=batch_size):
                v["app_name"] = name
                batch.append(v)
                keys.append(k)

            if batch:
                try:
                    resp = requests.post(f"{url}/{index_type}", json=batch).json()
                    if not resp["success"] == True:
                        1 / 0

                    index.delete(keys)
                    backoff_time = 1
                except:
                    backoff_time = min(backoff_time * 2, 60)
                    time.sleep(backoff_time)
            else:
                break

    while True:
        upload_data(name, "logs", "logs")
        upload_data(name, "ml_inputs_outputs", "logs")
        upload_data(name, "timers", "timers")
        time.sleep(int(os.getenv("SYNC_SLEEP", 10)))


class SmartTimer:
    def __init__(self, name, save_to_dir="./"):
        self.name = name
        os.makedirs(save_to_dir, exist_ok=True)
        self.timers_index = DefinedIndex(
            f"{self.name}_timers",
            schema={
                "u_id": "",
                "stage": "",
                "timestamp": 0,
                "failed": False,
                "start": False,
            },
            db_path=os.path.join(save_to_dir, f"{self.name}_timers.db"),
            auto_key=True,
        )

    def start(self, id, stage="begin"):
        self.timers_index.add(
            {
                "u_id": str(id),
                "stage": stage,
                "timestamp": time.time(),
                "failed": False,
                "start": True,
            }
        )

    def finished(self, id, stage="end"):
        self.timers_index.add(
            {
                "u_id": str(id),
                "stage": stage,
                "timestamp": time.time(),
                "failed": False,
                "start": False,
            }
        )

    def failed(self, id, stage="end"):
        self.timers_index.add(
            {
                "u_id": str(id),
                "stage": stage,
                "timestamp": time.time(),
                "failed": True,
                "start": False,
            }
        )


class SmartLogger:
    def __init__(self, name, save_to_dir="./", log_to_console=True):
        self.name = name
        self.log_to_console = log_to_console

        self.logs_index = DefinedIndex(
            f"{self.name}_logs",
            schema={
                "u_id": "",
                "level": "",
                "messages": [],
                "timestamp": 0,
                "stage": "",
            },
            db_path=os.path.join(save_to_dir, f"{self.name}_logs.db"),
            auto_key=True,
        )

        self.ml_inputs_outputs_index = DefinedIndex(
            f"{self.name}_ml_inputs_outputs",
            schema={
                "u_id": "",
                "inputs": [],
                "outputs": [],
                "model_type": "",
                "timestamp": 0,
                "stage": "",
            },
            db_path=os.path.join(save_to_dir, f"{self.name}_logs.db"),
            auto_key=True,
        )

    def _log(self, id, level, *messages, stage=None):
        timestamp = time.time()
        self.logs_index.add(
            {
                "u_id": str(id),
                "level": level,
                "messages": [str(_) for _ in messages],
                "timestamp": timestamp,
                "stage": stage,
            }
        )

        if self.log_to_console:
            self._print_to_console(timestamp, id, level, messages, stage)

    def _print_to_console(self, timestamp, id, level, messages, stage):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        log_colors = {
            "INFO": "\033[94m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "EXCEPTION": "\033[91m",
            "DEBUG": "\033[92m",
        }
        stage_color = "\033[95m"
        reset_color = "\033[0m"

        formatted_message = f"{log_colors[level]}{timestamp} {id} {stage_color}{stage}: {level}: {reset_color}"
        for message in messages:
            formatted_message += f"{message} "

        print(formatted_message)

    def debug(self, id, *messages, stage=None):
        self._log(id, "DEBUG", *messages, stage=stage)

    def info(self, id, *messages, stage=None):
        self._log(id, "INFO", *messages, stage=stage)

    def warning(self, id, *messages, stage=None):
        self._log(id, "WARNING", *messages, stage=stage)

    def error(self, id, *messages, stage=None):
        self._log(id, "ERROR", *messages, stage=stage)

    def exception(self, id, exc, *messages, stage=None):
        messages = (str(exc),) + messages
        self._log(id, "EXCEPTION", *messages, stage=stage)

    def ml_inputs_outputs(self, id, inputs, outputs, model_type, stage=None):
        if not isinstance(inputs, (list, tuple)):
            raise ValueError("inputs must be a list or tuple")
        if not isinstance(outputs, (list, tuple)):
            raise ValueError("outputs must be a list or tuple")
        if len(inputs) != len(outputs):
            raise ValueError("inputs and outputs must be the same length")

        self.ml_inputs_outputs_index.add(
            {
                "u_id": str(id),
                "inputs": inputs,
                "outputs": outputs,
                "model_type": model_type,
                "timestamp": time.time(),
                "stage": stage,
            }
        )


if __name__ == "__main__":
    import sys
    import uuid
    import time
    import random

    if sys.argv[1] == "dummy":
        import random
        import time
        import uuid

        def create_some_log(timer, logger):
            u_id = str(uuid.uuid4())

            timer.start(id=u_id)
            time.sleep(random.randint(100, 600) / 1000)
            timer.start(id=u_id, stage="feature_extraction")
            time.sleep(random.randint(100, 600) / 1000)

            if random.choice([0, 1, 2, 3, 4]) == 3:
                timer.failed(id=u_id, stage="feature_extraction")
            else:
                timer.finished(id=u_id, stage="feature_extraction")

            time.sleep(random.randint(100, 600) / 1000)
            timer.finished(id=u_id)

            logger.debug(
                u_id, "message_1", "message_2", "message_3", stage="optional_stage"
            )
            logger.info(u_id, "message_5", "message_6", stage="optional_stage")
            logger.warning(u_id, "message_7", "message_8")
            logger.exception(u_id, "message_9", "message_10")
            logger.ml_inputs_outputs(u_id, ["inputs"], ["outputs"], "model_type")

        timer = SmartTimer("analytics")
        logger = SmartLogger("analytics")

        for _ in range(100):
            create_some_log(timer, logger)
            print(_)

    elif sys.argv[1] == "upload":
        upload_to_smartdash("analytics", "./", "http://localhost:6788")
