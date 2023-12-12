from gevent import monkey

monkey.patch_all()
import gevent
import os
import time
import json
import uuid
import pickle
import falcon
import logging
import requests
import mimetypes
from datetime import datetime

from liteindex import DefinedIndex

db_path = os.path.join(os.getenv("SMARTDASH_SAVE_DIR", "./"), "smartdash.db")

LOG_INDEX = DefinedIndex(
    "logs",
    schema={
        "app_name": "string",
        "u_id": "string",
        "stage": "string",
        "level": "string",
        "messages": "json",
        "time": "number",
        "tags": "json",
    },
    db_path=db_path,
)

KV_INDEX = DefinedIndex(
    "key_value",
    schema={
        "app_name": "string",
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


class HealthCheck(object):
    def on_get(self, req, resp):
        resp.media = {"status": "ok"}


class AddLogs(object):
    def on_post(self, req, resp):
        LOG_INDEX.update(pickle.loads(req.stream.read()))

        resp.media = {"success": True}
        resp.status = falcon.HTTP_200


class AddKeyValues(object):
    def on_post(self, req, resp):
        KV_INDEX.update(pickle.loads(req.stream.read()))

        resp.media = {"success": True}
        resp.status = falcon.HTTP_200


def main(port=8080):
    app = falcon.App(cors_enable=True)
    app.req_options.auto_parse_form_urlencoded = True
    app = falcon.App(
        middleware=falcon.CORSMiddleware(allow_origins="*", allow_credentials="*")
    )

    app.add_route("/logs", AddLogs())
    app.add_route("/key_values", AddKeyValues())
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
