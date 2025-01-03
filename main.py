import os
import sys
from threading import Thread
from time import sleep
from logging import getLogger, StreamHandler, DEBUG

from dotenv import load_dotenv

from api.flask_api import FlaskAPI
from api.server_com import SocketCom, ConnectCS
from discordbot.publicbot import csPublicBot


load_dotenv(verbose=True)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

flask_app = FlaskAPI(__name__)
app = SocketCom(flask_app.app)
cs_server = ConnectCS(app)
flask_app.add_cs_server(cs_server)

cs_bot = csPublicBot(cs_server)

if __name__ == "__main__":
    t = []
    if len(sys.argv) <= 1 or sys.argv[1] != "discord_only":
        t.append(Thread(target=app.run, kwargs={"port": os.getenv("PORT", 50000)}, daemon=True))

    if len(sys.argv) <= 1 or sys.argv[1] != "api_only":
        t.append(Thread(target=cs_bot.bot.run, args=(os.environ.get("DISCORD_TOKEN_CSPUBLIC"),), daemon=True))

    try:
        if len(t) == 0:
            logger.error("どのプロセスも起動しませんでした。引数を確認してください。")

        [thread.start() for thread in t]

        while True:
            sleep(60)

    except KeyboardInterrupt:
        logger.info("強制終了されました。スレッドを終了します。")

    except Exception as e:
        logger.error(f"エラーが発生しました。スレッドを終了します。 Exception: {e}")

    logger.info("プログラムを終了します。")
