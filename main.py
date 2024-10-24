from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from logging import getLogger, StreamHandler, DEBUG

from api.flask_api import FlaskAPI

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

# websocket = None
app = FlaskAPI(__name__).get_app()


if __name__ == "__main__":
    app.debug = True
    host = 'localhost'
    port = 50000

    server = WSGIServer(
        (host, port),
        app,
        handler_class=WebSocketHandler,
        # log=logger
    )

    logger.info(f"Server running on ws://{host}:{port}/pipe")
    server.serve_forever()
