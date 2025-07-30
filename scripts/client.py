# CSサーバー用スクリプト
# TODO: DBとの連携・CSサーバーへの移植

import os
import json
import asyncio
from logging import getLogger, StreamHandler, DEBUG, Logger

import websockets
from websockets.asyncio.client import ClientConnection
from dotenv import load_dotenv

load_dotenv()


class APIRequestHandler:
    def __init__(self, api_url, *, cs_server_password: str | None = None, logger: Logger | None = None):
        self.api_url = api_url
        self.cs_server_password = cs_server_password or os.getenv("CS_SERVER_PASSWORD")
        if not self.cs_server_password:
            raise ValueError("CS_SERVER_PASSWORDを引数または環境変数に設定してください。")

        if logger is not None:
            self.logger = logger
        else:
            self.logger = getLogger(__name__)
            handler = StreamHandler()
            handler.setLevel(DEBUG)
            self.logger.setLevel(DEBUG)
            self.logger.addHandler(handler)
            self.logger.propagate = False

    async def _make_response(self, request_type: str, request_data: dict) -> dict:
        """レスポンスを生成する"""
        match request_type:
            case "get_user_by_id":
                self.logger.info(f"Processing request for user ID: {request_data['id']}")
                return {
                    "id": request_data["id"],
                    "name": "takechi-scratch",
                    "point": 100,
                    "icon": "https://example.com/icon.png",
                    "teams": [1, 2, 3]
                }

            case "get_user_by_name":
                self.logger.info(f"Processing request for user name: {request_data['name']}")
                return {
                    "id": 100,
                    "name": request_data["name"],
                    "point": 123,
                    "icon": "https://example.com/icon2.png",
                    "teams": [1, 2, 3]
                }

            case "view_ad":
                self.logger.info(f"Processing ad view request for ID: {request_data["id"]} from IP: {request_data["hashed_ip"]}")
                ad_id = request_data["id"]
                if ad_id % 3 != 1:  # Simulating ad not found for testing
                    raise RuntimeError("Ad not found")

                return {
                    "project_url": f"https://scratch.mit.edu/projects/{870204802}/",
                }

            case "get_team_by_id":
                self.logger.info(f"Processing request for team ID: {request_data['id']}")
                return {
                    "id": request_data["id"],
                    "name": "たーけクラウドシステム管理チーム",
                    "studio_url": "https://scratch.mit.edu/studios/12345678/",
                    "leader": 11,
                    "users": [12, 13, 14],
                    "review": 4.5,
                    "point": 1000,
                    "yield_rate": 50
                }

            case "get_user_count":
                self.logger.info("Processing request for user count")
                return {"user_count": 100}

            case "get_user_ranking":
                self.logger.info(f"Processing request for user ranking with limit: {request_data['limit']}")
                return [{
                    "id": i + 1,
                    "name": "takechi-scratch",
                    "point": 100 * (50 - i),
                    "icon": "https://example.com/icon.png",
                    "teams": [1, 2, 3]
                } for i in range(request_data["limit"])]

            case _:
                raise ValueError(f"Unknown request type: {request_data['type']}")

    async def _communicate_with_cs_server(self, websocket: ClientConnection):
        await websocket.send(json.dumps({"type": "auth", "password": self.cs_server_password}))
        res = await websocket.recv()
        if "error" in res:
            self.logger.error(f"Authentication failed: {res}")
            return
        self.logger.info("Authenticated successfully with CS server")

        while True:
            try:
                request = await websocket.recv()
                request_data = json.loads(request)["data"]
                self.logger.info(f"Received request: {request_data}")

                try:
                    res = await self._make_response(request_data["type"], request_data["data"])
                    request_data["result"] = res
                except Exception as e:
                    self.logger.error(f"Error processing request: {e}")
                    request_data["error"] = str(e)

                self.logger.debug(f"Sending response: {request_data}")
                await websocket.send(json.dumps({"type": "response", "data": request_data}))

            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("Connection closed")
                break
            except Exception as e:
                self.logger.error(f"Error: {e}")
                break

    async def run(self):
        async for websocket in websockets.connect(self.api_url):
            try:
                await self._communicate_with_cs_server(websocket)
            except websockets.exceptions.ConnectionClosed:
                continue
            except Exception as e:
                self.logger.error(f"Error in WebSocket communication: {e}")
                break
            finally:
                await websocket.close()
                self.logger.info("WebSocket connection closed")


if __name__ == "__main__":
    handler = APIRequestHandler(
        api_url="ws://127.0.0.1:8000/admin/cs_server/ws",
        cs_server_password=os.getenv("CS_SERVER_PASSWORD")
    )
    asyncio.run(handler.run())
