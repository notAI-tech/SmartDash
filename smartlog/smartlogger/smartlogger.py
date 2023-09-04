import os
import sys
import time
import uuid
import traceback
from liteindex import DefinedIndex


def upload_to_smartdash():
    import argparse

    parser = argparse.ArgumentParser(
        description="start service for syncing to smartdash"
    )
    parser.add_argument(
        "--save_dir", type=str, help="Directory to save logs", required=True
    )
    parser.add_argument(
        "--server_url", type=str, help="Smartdash server URL", required=True
    )
    args = parser.parse_args()

    print(f"Starting sync to {args.server_url}")
    _upload_to_smartdash(args.save_dir, args.server_url)


def _upload_to_smartdash(log_dir, url, batch_size=100):
    import requests
    from glob import glob

    def upload_data(name, index_type, db_prefix):
        last_sync_failed = False
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
                    resp = requests.post(
                        f"{url}/{index_type}", json=batch, timeout=5
                    ).json()
                    if not resp["success"] == True:
                        1 / 0

                    index.delete(keys)
                    backoff_time = 1
                    last_sync_failed = False
                except:
                    if len(keys) >= 50000:
                        index.delete(keys[:50000])
                        keys = keys[50000:]

                    if not last_sync_failed:
                        print(f"Failed to sync {name} logs to {url}")
                        last_sync_failed = True

                    backoff_time = min(backoff_time * 2, 60)
                    time.sleep(backoff_time)
            else:
                break

    while True:
        db_files_in_dir = glob(os.path.join(log_dir, "*.db"))
        for db_file in db_files_in_dir:
            name = "_".join(os.path.basename(db_file).split("_")[:-1])

            upload_data(name, "logs", "logs")
            upload_data(name, "ml_inputs_outputs", "logs")
            upload_data(name, "metrics", "logs")

        time.sleep(int(os.getenv("SYNC_SLEEP", 10)))


class SmartLogger:
    def __init__(self, name, save_to_dir="./", log_to_console=False):
        self.name = name
        self.log_to_console = log_to_console
        os.makedirs(save_to_dir, exist_ok=True)
        db_path = os.path.join(save_to_dir, f"{self.name}_logs.db")

        self.logs_index = DefinedIndex(
            f"{self.name}_logs",
            schema={
                "u_id": "",
                "level": "",
                "messages": [],
                "timestamp": 0,
                "stage": "",
                "tags": [],
            },
            db_path=db_path,
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
                "tags": [],
            },
            db_path=db_path,
            auto_key=True,
        )

        self.metrics_index = DefinedIndex(
            f"{self.name}_metrics",
            schema={
                "u_id": "",
                "metric": "",
                "value": 0,
                "timestamp": 0,
                "stage": "",
                "tags": [],
            },
            db_path=db_path,
            auto_key=True,
        )

    def _log(self, id, level, *messages, stage=None, tags=[]):
        timestamp = time.time()
        self.logs_index.add(
            {
                "u_id": str(id),
                "level": level,
                "messages": [str(_) for _ in messages],
                "timestamp": timestamp,
                "stage": stage,
                "tags": tags,
            }
        )

        if self.log_to_console:
            self._print_to_console(timestamp, id, level, messages, stage, tags)

    def _print_to_console(self, timestamp, id, level, messages, stage, tags=[]):
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

        formatted_message += f"tags: {tags}"

        print(formatted_message)

    def debug(self, id, *messages, stage=None, tags=[]):
        self._log(id, "DEBUG", *messages, stage=stage, tags=tags)

    def info(self, id, *messages, stage=None, tags=[]):
        self._log(id, "INFO", *messages, stage=stage, tags=tags)

    def warning(self, id, *messages, stage=None, tags=[]):
        self._log(id, "WARNING", *messages, stage=stage, tags=tags)

    def error(self, id, *messages, stage=None, tags=[]):
        self._log(id, "ERROR", *messages, stage=stage, tags=tags)

    def exception(self, id, *messages, stage=None, tags=[]):
        exc_info = sys.exc_info()
        traceback_string = "".join(traceback.format_exception(*exc_info))

        messages = (
            f"\nException Info: {exc_info}",
            f"\nTraceback:\n{traceback.format_exception(*exc_info)}",
            *messages,
        )
        self._log(id, "EXCEPTION", *messages, stage=stage, tags=tags)

    def ml_inputs_outputs(self, id, inputs, outputs, model_type, stage=None, tags=[]):
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
                "tags": tags,
            }
        )

    def metric(self, id, metric, value, stage=None, tags=[]):
        self.metrics_index.add(
            {
                "u_id": str(id),
                "metric": metric,
                "value": value,
                "timestamp": time.time(),
                "stage": stage,
                "tags": tags,
            }
        )

    def Stage(self, id, stage_name, tags=[], model_type=""):
        return self.StageConstructor(
            parent_logger=self,
            id=id,
            stage=stage_name,
            tags=tags,
            model_type=model_type,
        )

    class StageConstructor:
        def __init__(self, parent_logger, id, stage, tags=[], model_type=""):
            self.parent_logger = parent_logger
            self.id = str(id)
            self.stage = stage
            self.tags = tags
            self.model_type = model_type
            self.parent_logger.info(id, "Stage started", stage=stage, tags=tags)

        def failed(self, tags=[]):
            self.parent_logger.error(
                self.id, "Stage failed", stage=self.stage, tags=self.tags + tags
            )

        def success(self, tags=[]):
            self.parent_logger.info(
                self.id, "Stage succeeded", stage=self.stage, tags=self.tags + tags
            )

        # Wrapping parent logger functions within Stage class
        def debug(self, *messages, tags=[]):
            self.parent_logger.debug(
                self.id, *messages, stage=self.stage, tags=self.tags + tags
            )

        def info(self, *messages, tags=[]):
            self.parent_logger.info(
                self.id, *messages, stage=self.stage, tags=self.tags + tags
            )

        def warning(self, *messages, tags=[]):
            self.parent_logger.warning(
                self.id, *messages, stage=self.stage, tags=self.tags + tags
            )

        def error(self, *messages, tags=[]):
            self.parent_logger.error(
                self.id, *messages, stage=self.stage, tags=self.tags + tags
            )

        def exception(self, *messages, tags=[]):
            self.parent_logger.exception(
                self.id, *messages, stage=self.stage, tags=self.tags + tags
            )

        def ml_inputs_outputs(self, inputs, outputs, tags=[]):
            self.parent_logger.ml_inputs_outputs(
                self.id,
                inputs,
                outputs,
                self.model_type,
                stage=self.stage,
                tags=self.tags + tags,
            )

        def metric(self, metric, value, tags=[]):
            self.parent_logger.metric(
                self.id, metric, value, stage=self.stage, tags=self.tags + tags
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

        def create_some_log(logger):
            u_id = uuid.uuid4()
            for stage_name in [
                "preprocessing",
                "inference1",
                "inference2",
                "inference3",
                "inference5",
                "postprocessing",
            ]:
                stage = logger.Stage(
                    u_id, stage_name, tags=[f"tag.{random.randint(0, 10)}"]
                )

                stage.metric("metric1", random.randint(0, 100) / 100)

                if "inference" in stage_name and random.choice([1, 2, 3]) == 1:
                    continue

                stage.debug("test debug", 2, 3, 4, tags=["test:debug"])
                time.sleep(random.uniform(0.0001, 0.1))

                if random.choice([1, 2, 3, 4]) == 1:
                    stage.failed()
                else:
                    stage.success()
                    if stage_name == "postprocessing":
                        stage.ml_inputs_outputs([1, 2, 3], [4, 5, "66"])

        logger = SmartLogger("analytics")

        for _ in range(100):
            create_some_log(logger)

    elif sys.argv[1] == "upload":
        upload_to_smartdash()
