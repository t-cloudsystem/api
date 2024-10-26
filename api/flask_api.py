import json
import time
from logging import getLogger, StreamHandler, DEBUG

from flask import Flask, request, jsonify
from flask_cors import CORS

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class FlaskAPI:
    def __init__(self, name):
        self.websocket = None
        self.app = Flask(name)
        CORS(self.app)

        self.socket = None
        self.server_started = time.time()
        self._set_url_rule()

        logger.debug(f"Registered routes: {self.app.url_map}")

    def get_app(self):
        return self.app

    def add_cs_server(self, socket_com):
        self.socket = socket_com

    def _set_url_rule(self):
        @self.app.route('/')
        def home():
            return jsonify({
                "website": "https://scratch.mit.edu/studios/33110478/",
                "author": "@takechi-scratch",
                "help": "https://scratch.mit.edu/users/takechi-scratch/"
            })

        @self.app.route('/health/')
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

        @self.app.errorhandler(400)
        def error_400(error):
            return jsonify({"message": "error", "status": 400}), 400

        @self.app.errorhandler(403)
        def error_403(error):
            return jsonify({"message": "error", "status": 403}), 403

        @self.app.errorhandler(404)
        def error_404(error):
            return jsonify({"message": "error", "status": 404}), 404

        @self.app.errorhandler(405)
        def error_405(error):
            return jsonify({"message": "error", "status": 405}), 405

        @self.pp.errorhandler(500)
        def error_500(error):
            return jsonify({"message": "error", "status": 500}), 500
