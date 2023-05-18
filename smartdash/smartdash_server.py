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

LOG_INDEX = DefinedIndex("log_index", {"app_name": "", "u_id": "", "level": "", "messages": [], "timestamp": 0}, "smartdash.db", auto_key=True)
TIMERS_INDEX = DefinedIndex("timers_index", {"app_name": "", "u_id": "", "stage": "", "timestamp": 0}, "smartdash.db", auto_key=True)
ML_INPUTS_OUTPUTS_INDEX = DefinedIndex("ml_inputs_outputs_index", {"app_name": "", "u_id": "", "inputs": [], "outputs": [], "model_type": "", "timestamp": 0}, "smartdash.db", auto_key=True)

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
        for _, log_data in LOG_INDEX.search(query={"app_name": app_name, "timestamp": {"$gt": from_time}}, sort_by="timestamp", reversed_sort=True, page=1):
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
        for _, log_data in TIMERS_INDEX.search(query={"app_name": app_name, "timestamp": {"$gt": from_time}}, sort_by="timestamp", reversed_sort=True, page=1):
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
        for _, log_data in ML_INPUTS_OUTPUTS_INDEX.search(query={"app_name": app_name, "timestamp": {"$gt": from_time}}, sort_by="timestamp", reversed_sort=True, page=1):
            logs.append(log_data)
        resp.media = logs
        resp.status = falcon.HTTP_200

app = falcon.App(cors_enable=True)
app.req_options.auto_parse_form_urlencoded = True
app = falcon.App(
    middleware=falcon.CORSMiddleware(allow_origins="*", allow_credentials="*")
)

app.add_route("/logs", AddLogs())
app.add_route("/timers", AddTimers())
app.add_route("/ml_inputs_outputs", AddMLInputsOutputs())


if __name__ == "__main__":
    from gevent.pywsgi import WSGIServer
    http_server = WSGIServer(("", 6788), app)
    print("SmartDash server started at 6788")
    http_server.serve_forever()
