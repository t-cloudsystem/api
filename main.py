import os
from logging import getLogger, StreamHandler, DEBUG
from concurrent.futures import ThreadPoolExecutor

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
flask_app.add_cs_server(app)

cs_bot = csPublicBot()
if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(app.run, port=os.getenv("PORT", 50000))
        executor.submit(cs_bot.bot.run, os.environ.get("DISCORD_TOKEN_CSPUBLIC"))
