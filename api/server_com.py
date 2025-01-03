import datetime
import os
from os import path
from logging import getLogger, StreamHandler, DEBUG
from typing import Any

import requests
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

load_dotenv(path.join(path.dirname(__file__), '.env'), verbose=True)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


# プライベートサーバーとのソケット通信
class SocketCom:
    def __init__(self, flask_app=None):
        if not flask_app:
            logger.debug("デフォルトのFlaskアプリケーションを使用します")
            from flask import Flask
            self.flask_app = Flask(__name__)
        else:
            self.flask_app = flask_app

        self.cs_connected = False
        self.sio = SocketIO(self.flask_app)

        self.sio.on_event("connect", self._on_connect, namespace="/")
        self.sio.on_event("broadcast_message", self._handle_message, namespace="/")

    def _on_connect(self):
        logger.info("CSサーバーが接続されました")
        self.cs_connected = True

    def _handle_message(self, data):
        logger.debug(data)

        datetime_now = datetime.datetime.now()
        emit("response", str(datetime_now), namespace="/", include_self=True)
        logger.debug("send message: {}".format(datetime_now))

    def get_data(self, function: str, data: dict) -> dict:
        data["function"] = function
        data["apiKey"] = os.environ["INNER_API_KEY"]

        res = requests.get(os.environ["INNER_API_URL"], params=data, headers={"Content-Type": "application/json"})
        return res.json()

    def post_data(self, function: str, data: dict) -> dict:
        data["function"] = function
        data["apiKey"] = os.environ["INNER_API_KEY"]

        res = requests.post(os.environ["INNER_API_URL"], data=data, headers={"Content-Type": "application/json"})
        return res.json()

    def run(self, app=None, host: str = "0.0.0.0", port: int = 50000, *args, **kwargs):
        # なぜかデバッグモードは動かなくなるので無効化
        kwargs["debug"] = False
        kwargs["log_output"] = True
        kwargs["allow_unsafe_werkzeug"] = True

        if not app:
            app = self.flask_app

        logger.info(f"サーバーを起動しました: http://localhost:{port} で稼働中")
        self.sio.run(app, host, port, *args, **kwargs)

    async def request_to_CS(self, request_type: str, data: Any) -> dict:
        self.sio.emit("cs_request", {"type": request_type, "data": data}, namespace="/")
        return {}


# CSサーバーとのデータのやり取り
class ConnectCS:
    def __init__(self, socket: SocketCom = None):
        """CSサーバーとのデータのやり取りを行うクラス

        Args:
            socket (SocketCom, optional): ソケットのクラスがあれば引数として指定。
        """

        if not socket:
            self.com = SocketCom()
        else:
            self.com = socket

    async def get_userinfo(self, id: str) -> dict:
        res = await self.com.request_to_CS("get_userinfo", {"id": id})
        return res

    async def get_userID(self, username: str) -> dict:
        res = await self.com.request_to_CS("get_username", {"username": username})
        return res

    def view_ad(self, ad_id: int, ip_address: str) -> dict:
        res = self.com.post_data("incrementAdViews", {"adId": ad_id, "ipAddress": ip_address})
        return res.get("url")  # レスポンスの仕様待ち


if __name__ == "__main__":
    serversocket = ConnectCS()

    serversocket.com.run()
