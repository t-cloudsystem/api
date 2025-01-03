import json
import time
from logging import getLogger, StreamHandler, DEBUG

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class FlaskAPI:
    def __init__(self, name):
        self.app = Flask(name)
        CORS(self.app)
        self.app.json.sort_keys = False
        self.limiter = Limiter(key_func=get_remote_address, app=self.app, default_limits=["30 per minute"])

        self.cs_server = None
        self.server_started = time.time()
        self._set_url_rule()
        self._set_error_rule()

        logger.debug(f"Registered routes: {self.app.url_map}")

    def add_cs_server(self, cs_server):
        self.cs_server = cs_server

    def _make_res(self, data=None, status: int = 200, message: str = None):
        res_data = {"data": data, "status": int(status)}
        if message is not None:
            res_data["message"] = message

        return jsonify(res_data), int(status)

    def _set_url_rule(self):
        @self.app.route("/")
        def home():
            return self._make_res({
                "website": "https://scratch.mit.edu/studios/33110478/",
                "author": "@takechi-scratch",
                "help": "https://scratch.mit.edu/users/takechi-scratch/"
            })

        @self.app.route("/health/")
        def health():
            if self.socket and self.socket.cs_connected:
                cs_status = "OK"
            else:
                cs_status = "Not working"

            return jsonify({
                "version": "ver.2.0.1(beta)",
                "uptime": time.time() - self.server_started,
                "api_status": "OK",
                "cs_status": cs_status
            })

        @self.app.route("/ads/<int:ad_id>/")
        def takechi_ad(ad_id):
            return self._make_res({
                "ad_id": ad_id,
                "ad_name": "takechi",
                "ad_url": "https://scratch.mit.edu/projects/536982758/"
            })

    def _set_error_rule(self):
        @self.app.errorhandler(400)
        def error_400(error):
            return self._make_res(status=400, message="Bad Request")

        @self.app.errorhandler(403)
        def error_403(error):
            return self._make_res(status=403, message="Forbidden")

        @self.app.errorhandler(404)
        def error_404(error):
            return self._make_res(status=404, message="Not Found")

        @self.app.errorhandler(405)
        def error_405(error):
            return self._make_res(status=405, message="Method Not Allowed")

        @self.app.errorhandler(429)
        def error_429(error):
            return self._make_res(status=429, message="Too Many Requests")

        @self.app.errorhandler(500)
        def error_500(error):
            return self._make_res(status=500, message="Internal Server Error")
