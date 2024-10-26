import datetime
from logging import getLogger, StreamHandler, DEBUG
from typing import Any

from flask_socketio import SocketIO, emit

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

        self.sio = SocketIO(self.flask_app)

        self.sio.on_event("connect", self._on_connect, namespace="/")
        self.sio.on_event("broadcast_message", self._handle_message, namespace="/")

    def _on_connect(self):
        logger.info("CSサーバーが接続されました")

    def _handle_message(self, data):
        logger.debug(data)

        datetime_now = datetime.datetime.now()
        emit("response", str(datetime_now), namespace="/", include_self=True)
        logger.debug("send message: {}".format(datetime_now))

    def run(self, app=None, host: str = "0.0.0.0", port: int = 50000, *args, **kwargs):
        # なぜかデバッグモードは動かなくなる
        kwargs["debug"] = False
        kwargs["log_output"] = True

        if not app:
            app = self.flask_app

        logger.info(f"サーバーを起動しました: http://localhost:{port} で稼働中")
        self.sio.run(app, host, port, *args, **kwargs)

    async def request_to_CS(self, request_type: str, data: Any) -> dict:
        self.sio.emit("cs_request", {"type": request_type, "data": data}, namespace="/")


# CSサーバーとのデータのやり取り
class ConnectCS:
    def __init__(self, socket: SocketCom = None):
        """CSサーバーとのデータのやり取りを行うクラス

        Args:
            socket (SocketCom, optional): ソケットのクラスがあれば引数として指定。
        """

        if not socket:
            self.socket = SocketCom()
        else:
            self.socket = socket

    def get_userinfo(self, username: str) -> dict:
        self.socket.request_to_CS("get_userinfo", {"username": username})


if __name__ == "__main__":
    serversocket = ConnectCS()

    serversocket.socket.run()
