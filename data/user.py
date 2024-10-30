from logging import getLogger, StreamHandler, DEBUG

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


class User:
    def __init__(self, cs_server, **kwargs):
        self._cs_server = cs_server
        if kwargs.get("username") is None and kwargs.get("id") is None:
            raise Exception("ユーザー情報不足のため、インスタンスを作成できません")

        self.username: str = kwargs.get("username", self.get_username())
        self.id: int = kwargs.get("id", self.get_id())

    async def get_username(self):
        return await self._cs_server.request_to_CS("get_username", self.id)

    async def get_id(self):
        return await self._cs_server.request_to_CS("get_id", self.username)
