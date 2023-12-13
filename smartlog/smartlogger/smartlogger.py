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
    import pickle
    import requests
    from glob import glob

    def upload_data(db_file, batch_size=512):
        name = os.path.splitext(os.path.basename(db_file))[0]

        try:
            logs_index = DefinedIndex("logs", db_path=os.path.join(log_dir, db_file))

            key_value_index = DefinedIndex(
                "key_value", db_path=os.path.join(log_dir, db_file)
            )
        except:
            return

        total_n_logs_popped = 0
        total_n_key_value_popped = 0

        logs_index_total_len = logs_index.count()
        key_value_index_total_len = key_value_index.count()

        if logs_index_total_len or key_value_index_total_len:
            print(
                f"smartlogger {name}: syncing {logs_index_total_len} logs, {key_value_index_total_len} key values"
            )

        error_already_printed = False

        while True:
            logs_index_popped_data = logs_index.pop(n=batch_size)

            n_logs_popped = None
            n_key_value_popped = None

            if logs_index_popped_data:
                n_logs_popped = len(logs_index_popped_data)

                for k in logs_index_popped_data:
                    logs_index_popped_data[k]["app_name"] = name

                try:
                    resp = requests.post(
                        f"{url}/logs",
                        data=pickle.dumps(
                            logs_index_popped_data, protocol=pickle.HIGHEST_PROTOCOL
                        ),
                    ).json()

                    logs_index_popped_data = None

                    if not resp["success"] == True:
                        1 / 0

                    error_already_printed = False
                except Exception as ex:
                    if not error_already_printed:
                        print(f"smartlogger {name}: error syncing logs: {ex}")
                        error_already_printed = True

            key_value_index_popped_data = key_value_index.pop(n=batch_size)

            if key_value_index_popped_data:
                n_key_value_popped = len(key_value_index_popped_data)

                for k in key_value_index_popped_data:
                    key_value_index_popped_data[k]["app_name"] = name

                try:
                    resp = requests.post(
                        f"{url}/key_values",
                        data=pickle.dumps(
                            key_value_index_popped_data,
                            protocol=pickle.HIGHEST_PROTOCOL,
                        ),
                    ).json()

                    key_value_index_popped_data = None

                    if not resp["success"] == True:
                        1 / 0

                except Exception as ex:
                    pass

            total_n_key_value_popped += n_key_value_popped if n_key_value_popped else 0
            total_n_logs_popped += n_logs_popped if n_logs_popped else 0

            if not n_logs_popped and not n_key_value_popped:
                if total_n_logs_popped > 0 or total_n_key_value_popped > 0:
                    print(
                        f"smartlogger {name}: synced {total_n_logs_popped} logs, {total_n_key_value_popped} key values"
                    )
                    logs_index.vaccum()
                    key_value_index.vaccum()
                return

    while True:
        for db_file in glob(os.path.join(log_dir, "*.db")):
            upload_data(db_file, batch_size=batch_size)

        time.sleep(int(os.getenv("SYNC_SLEEP", 10)))


class SmartLogger:
    def __init__(self, name, dir="./", log_to_console=False):
        self.name = name
        self.log_to_console = log_to_console

        os.makedirs(dir, exist_ok=True)
        db_path = os.path.join(dir, f"{self.name}.db")

        self.logs_index = DefinedIndex(
            "logs",
            schema={
                "u_id": "string",
                "stage": "string",
                "level": "string",
                "messages": "json",
                "time": "number",
                "tags": "json",
            },
            db_path=db_path,
        )

        self.key_value_index = DefinedIndex(
            "key_value",
            schema={
                "u_id": "string",
                "key": "string",
                "num_value": "number",
                "str_value": "string",
                "other_value": "other",
                "name": "string",
                "timestamp": "number",
                "stage": "string",
                "tags": "json",
            },
            db_path=db_path,
        )

    def _log(self, id, level, *messages, stage=None, tags=[]):
        timestamp = time.time()

        self.logs_index.update(
            {
                str(uuid.uuid4()): {
                    "u_id": str(id),
                    "stage": stage,
                    "level": level,
                    "messages": [str(m) for m in messages],
                    "time": timestamp,
                    "tags": tags,
                }
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

    def key_value(self, id, key, value, name=None, stage=None, tags=[]):
        num_value = value if isinstance(value, (int, float)) else None
        str_value = value if isinstance(value, str) else None
        other_value = value if not num_value and not str_value else None
        self.key_value_index.update(
            {
                str(uuid.uuid4()): {
                    "u_id": str(id),
                    "key": key,
                    "num_value": num_value,
                    "str_value": str_value,
                    "other_value": other_value,
                    "name": name,
                    "timestamp": time.time(),
                    "stage": stage,
                    "tags": tags,
                }
            }
        )

    def Stage(self, id, stage_name, tags=[]):
        return self.StageConstructor(
            parent_logger=self, id=id, stage=stage_name, tags=tags
        )

    class StageConstructor:
        def __init__(self, parent_logger, id, stage, tags=[]):
            self.parent_logger = parent_logger
            self.id = str(id)
            self.stage = stage
            self.tags = tags
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

        def key_value(self, key, value, name=None, tags=[]):
            self.parent_logger.key_value(
                self.id, key, value, name=name, stage=self.stage, tags=self.tags + tags
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

                stage.key_value("metric1", random.randint(0, 100))

                if "inference" in stage_name and random.choice([1, 2, 3]) == 1:
                    continue

                stage.debug("test debug", 2, 3, 4, tags=["test:debug"])
                time.sleep(random.uniform(0.0001, 0.1))

                if random.choice([1, 2, 3, 4]) == 1:
                    stage.failed()
                else:
                    stage.success()
                    if stage_name == "postprocessing":
                        stage.key_value(
                            "model_inputs_and_predictions", ([1, 2, 3], [4, 5, "66"])
                        )

        logger = SmartLogger("analytics")

        for _ in range(100):
            create_some_log(logger)

    else:
        upload_to_smartdash()
