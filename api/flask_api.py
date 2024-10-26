import json
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

        self.app.add_url_rule('/', 'top', self.topics)
        self.app.add_url_rule('/pay', 'pay', self.pay)

        logger.debug(f"Registered routes: {self.app.url_map}")

    def get_app(self):
        return self.app

    def topics(self):
        print("あ")
        return jsonify(['device1', 'device2'])

    def pay(self):
        data = request.data.decode('utf-8')
        data = json.loads(data)
        return json.dumps({'message': 'received', 'data': data})
