import asyncio
import os
from logging import getLogger, StreamHandler, DEBUG

from dotenv import load_dotenv

load_dotenv(verbose=True)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False
