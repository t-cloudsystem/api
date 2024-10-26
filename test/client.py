import socketio
from datetime import datetime


class MyCustomNamespace(socketio.ClientNamespace):  # 名前空間を設定するクラス
    def on_connect(self):
        print('[{}] connect'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    def on_disconnect(self):
        print('[{}] disconnect'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    def on_response(self, msg):
        print('[{}] response : {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))

    def cs_res(self, msg):
        print('[{}] CSresponse : {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))


class SocketIOClient:
    def __init__(self, host, path):
        self.host = host
        self.path = path
        self.sio = socketio.Client()

    def connect(self):
        self.sio.register_namespace(MyCustomNamespace(self.path))  # 名前空間を設定
        self.sio.connect(self.host)  # サーバーに接続
        self.sio.start_background_task(self.my_background_task, 123)  # バックグラウンドタスクの登録 (123は引数の書き方の参考のため、処理には使っていない)
        self.sio.wait()  # イベントが待ち

    def my_background_task(self, my_argument):  # ここにバックグランド処理のコードを書く
        while True:
            input_data = input("send data:")  # ターミナルから入力された文字を取得
            self.sio.emit('broadcast_message', input_data, namespace=self.path)  # ターミナルで入力された文字をサーバーに送信
            self.sio.sleep(1)


if __name__ == '__main__':
    sio_client = SocketIOClient('http://127.0.0.1:50000', '/')  # SocketIOClientクラスをインスタンス化
    sio_client.connect()
