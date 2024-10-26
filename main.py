from logging import getLogger, StreamHandler, DEBUG

from api.flask_api import FlaskAPI
from api.server_com import SocketCom, ConnectCS

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

flask_app = FlaskAPI(__name__).get_app()
app = SocketCom(flask_app)
cs_server = ConnectCS(app)

if __name__ == "__main__":
    # "debug=True"を設定すると動かなくなります
    app.run()
