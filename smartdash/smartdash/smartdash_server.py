from gevent import monkey

monkey.patch_all()
import gevent
import os
import time
import json
import uuid
import falcon
import logging
import requests
import mimetypes
from datetime import datetime

from liteindex import DefinedIndex

db_path = os.path.join(os.getenv("SMARTDASH_SAVE_DIR", "./"), "smartdash.db")

LOG_INDEX = DefinedIndex(
    "log_index",
    {
        "app_name": "",
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

ML_INPUTS_OUTPUTS_INDEX = DefinedIndex(
    "ml_inputs_outputs_index",
    {
        "app_name": "",
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

METRICS_INDEX = DefinedIndex(
    f"metrics_index",
    schema={"app_name": "", "metric": "", "value": 0, "timestamp": 0},
    db_path=db_path,
    auto_key=True,
)


class HealthCheck(object):
    def on_get(self, req, resp):
        resp.media = {"status": "ok"}


class GetDashMetrics(object):
    def on_get(self, req, resp):
        eight_hours_ago = (
            time.time() - float(req.params.get("last_n_hours", 8)) * 60 * 60
        )
        long_running_if_greater_than = (
            time.time() - float(req.params.get("long_running_n_hours", 1)) * 60 * 60
        )

        # Fetch logs from the last 8 hours

        data_by_id = {}

        for _, log in LOG_INDEX.search(
            {
                "app_name": req.params["app_name"],
                "timestamp": {"$gte": eight_hours_ago},
            },
            sort_by="timestamp",
            page=1,
            page_size=1000,
        ):
            if log["u_id"] not in data_by_id:
                data_by_id[log["u_id"]] = {
                    "logs": [],
                    "ml_inputs_outputs": [],
                    "stage_wise_times": {},
                    "success": None,
                    "failed": None,
                    "in_process": None,
                    "long_running": False,
                }

            data_by_id[log["u_id"]]["logs"].append(log)

        # Fetch metrics from the last 8 hours
        METRICS_DATA = METRICS_INDEX.search(
            {
                "app_name": req.params["app_name"],
                "timestamp": {"$gte": eight_hours_ago},
            },
            sort_by="timestamp",
            page=1,
            page_size=1000,
        )

        for _, ml_inputs_outputs in ML_INPUTS_OUTPUTS_INDEX.search(
            {
                "app_name": req.params["app_name"],
                "timestamp": {"$gte": eight_hours_ago},
            },
            sort_by="timestamp",
            page=1,
            page_size=1000,
        ):
            if ml_inputs_outputs["u_id"] not in data_by_id:
                data_by_id[log["u_id"]] = {
                    "logs": [],
                    "ml_inputs_outputs": [],
                    "stage_wise_times": {},
                    "success": None,
                    "failed": None,
                    "in_process": None,
                    "long_running": False,
                }

            data_by_id[log["u_id"]]["ml_inputs_outputs"].append(ml_inputs_outputs)

        # Calculate stage wise timers
        for u_id, data in data_by_id.items():
            stage_timers = {}
            logs = data["logs"]
            for log in logs:
                stage = log["stage"]
                if stage not in stage_timers:
                    stage_timers[stage] = {
                        "start": log["timestamp"],
                        "end": log["timestamp"],
                    }
                else:
                    stage_timers[stage]["end"] = log["timestamp"]

            if logs:
                if logs[-1]["level"] == "ERROR":
                    data_by_id[u_id]["failed"] = True
                elif logs[-1]["messages"][0] == "Stage succeeded":
                    data_by_id[u_id]["success"] = True
                elif time.time() - logs[-1]["timestamp"] > long_running_if_greater_than:
                    data_by_id[u_id]["long_running"] = True
                else:
                    data_by_id[u_id]["in_process"] = True

            if stage_timers:
                data_by_id[u_id]["stage_wise_times"] = stage_timers

        resp.media = {
            "success": True,
            "data_by_uid": data_by_id,
            "metrics": METRICS_DATA,
        }
        resp.status = falcon.HTTP_200


class AppNames(object):
    def on_get(self, req, resp):
        resp.media = {
            "success": True,
            "app_names": list(
                set(
                    LOG_INDEX.distinct("app_name")
                    + METRICS_INDEX.distinct("app_name")
                    + ML_INPUTS_OUTPUTS_INDEX.distinct("app_name")
                )
            ),
        }
        resp.status = falcon.HTTP_200


class AddLogs(object):
    def on_post(self, req, resp):
        data = req.media
        id = LOG_INDEX.add(data)
        resp.media = {"success": True, "id": id}
        resp.status = falcon.HTTP_200


class AddMetrics(object):
    def on_post(self, req, resp):
        data = req.media
        id = METRICS_INDEX.add(data)
        resp.media = {"success": True, "id": id}
        resp.status = falcon.HTTP_200


class AddMLInputsOutputs(object):
    def on_post(self, req, resp):
        data = req.media
        id = ML_INPUTS_OUTPUTS_INDEX.add(data)
        resp.media = {"success": True, "id": id}
        resp.status = falcon.HTTP_200


def main(port=8080):
    app = falcon.App(cors_enable=True)
    app.req_options.auto_parse_form_urlencoded = True
    app = falcon.App(
        middleware=falcon.CORSMiddleware(allow_origins="*", allow_credentials="*")
    )

    app.add_route("/logs", AddLogs())
    app.add_route("/metrics", AddMetrics())
    app.add_route("/ml_inputs_outputs", AddMLInputsOutputs())
    app.add_route("/app_names", AppNames())
    app.add_route("/get_dash_metrics", GetDashMetrics())
    app.add_route("/health", HealthCheck())

    import gunicorn.app.base

    class StandaloneApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    host = os.getenv("HOST", "0.0.0.0")

    options = {
        "preload": "",
        "bind": "%s:%s" % (host, port),
        "workers": 3,
        "worker_connections": 1000,
        "worker_class": "gevent",
        "timeout": 120,
    }

    StandaloneApplication(app, options).run()
