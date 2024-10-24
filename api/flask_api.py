import json
import datetime
import time
import websocket
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
        self.app.add_url_rule('/pipe', 'pipe', self.pipe)

        logger.info(f"Registered routes: {self.app.url_map}")

        return

    def get_app(self):
        return self.app

    def topics(self):
        print("あ")
        return jsonify(['device1', 'device2'])

    def pay(self):
        data = request.data.decode('utf-8')
        data = json.loads(data)
        return json.dumps({'message': 'received', 'data': data})

    def pipe(self):
        """websocketでメッセージを送信"""
        logger.debug(request.environ)
        logger.debug("アクセスあり")
        if request.environ.get('wsgi.websocket'):
            ws: websocket = request.environ['wsgi.websocket']
            try:
                while True:
                    logger.debug("確認中")
                    time.sleep(0.1)
                    res = ws.receive()
                    logger.info(f'[ws received] {res}')
                    data = json.loads(res)
                    if data is None:
                        break
                    ws.send(json.dumps(
                        {'time': str(datetime.datetime.now()), 'message': data['value']}
                    ))
            except Exception as e:
                logger.error(f"エラー発生 内容:{e}")
            finally:
                ws.close("終了")

        logger.debug("完了")

        return "websocket"
