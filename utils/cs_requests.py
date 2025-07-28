import asyncio
import uuid

from .data_model import WaitingServerRequest


class CSRequestIterator:
    def __init__(self):
        self.next_request = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        while self.next_request is None:
            await asyncio.sleep(1 / 100)
        self.now_request = self.next_request
        self.next_request = None

        return self.now_request

    async def set_next_request(self, request: WaitingServerRequest):
        while self.next_request is not None:
            await asyncio.sleep(1 / 100)
        self.next_request = request


class CSRequests:
    def __init__(self, cs_server_iterator: CSRequestIterator):
        self.cs_server_iterator = cs_server_iterator
        self.requests = {}
        self.connected = False

    async def send_request(self, type: str, data: dict) -> str:
        if not self.connected:
            raise RuntimeError("CS server is not connected")

        """サーバーリクエストを送信する"""
        request_id = uuid.uuid4().hex
        request = WaitingServerRequest(id=request_id, type=type, data=data)
        await self.cs_server_iterator.set_next_request(request)
        self.requests[request_id] = request

        while not request.completed:
            await asyncio.sleep(1 / 100)

        if request.error:
            raise RuntimeError(request.error)

        return request.result
