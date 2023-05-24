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

LOG_INDEX = DefinedIndex(
    "log_index",
    {
        "app_name": "",
        "u_id": "",
        "level": "",
        "messages": [],
        "timestamp": 0,
        "stage": "",
    },
    "smartdash.db",
    auto_key=True,
)
TIMERS_INDEX = DefinedIndex(
    "timers_index",
    {
        "app_name": "",
        "u_id": "",
        "stage": "",
        "timestamp": 0,
        "failed": False,
        "start": False,
    },
    "smartdash.db",
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
    },
    "smartdash.db",
    auto_key=True,
)


class AppNames(object):
    def on_get(self, req, resp):
        resp.media = {
            "success": True,
            "app_names": list(
                set(
                    LOG_INDEX.distinct("app_name")
                    + TIMERS_INDEX.distinct("app_name")
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

    def on_get(self, req, resp):
        from_time = time.time() - (int(req.params.get("last_n_hours", 8)) * 60 * 60)

        app_name = req.params["app_name"]

        logs = []
        for _, log_data in LOG_INDEX.search(
            query={"app_name": app_name, "timestamp": {"$gt": from_time}},
            sort_by="timestamp",
            reversed_sort=True,
            page=1,
        ):
            logs.append(log_data)

        resp.media = logs
        resp.status = falcon.HTTP_200


class AddTimers(object):
    def on_post(self, req, resp):
        data = req.media
        id = TIMERS_INDEX.add(data)
        resp.media = {"success": True, "id": id}
        resp.status = falcon.HTTP_200

    def on_get(self, req, resp):
        from_time = time.time() - (int(req.params.get("last_n_hours", 8)) * 60 * 60)

        app_name = req.params["app_name"]

        logs = []
        for _, log_data in TIMERS_INDEX.search(
            query={"app_name": app_name, "timestamp": {"$gt": from_time}},
            sort_by="timestamp",
            reversed_sort=True,
            page=1,
        ):
            logs.append(log_data)
        resp.media = logs
        resp.status = falcon.HTTP_200


class AddMLInputsOutputs(object):
    def on_post(self, req, resp):
        data = req.media
        id = ML_INPUTS_OUTPUTS_INDEX.add(data)
        resp.media = {"success": True, "id": id}
        resp.status = falcon.HTTP_200

    def on_get(self, req, resp):
        from_time = time.time() - (int(req.params.get("last_n_hours", 8)) * 60 * 60)

        app_name = req.params["app_name"]

        logs = []
        for _, log_data in ML_INPUTS_OUTPUTS_INDEX.search(
            query={"app_name": app_name, "timestamp": {"$gt": from_time}},
            sort_by="timestamp",
            reversed_sort=True,
            page=1,
        ):
            logs.append(log_data)
        resp.media = logs
        resp.status = falcon.HTTP_200


def main(port=8080):
    app = falcon.App(cors_enable=True)
    app.req_options.auto_parse_form_urlencoded = True
    app = falcon.App(
        middleware=falcon.CORSMiddleware(allow_origins="*", allow_credentials="*")
    )

    app.add_route("/logs", AddLogs())
    app.add_route("/timers", AddTimers())
    app.add_route("/ml_inputs_outputs", AddMLInputsOutputs())
    app.add_route("/app_names", AppNames())

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
