import os
from logging import getLogger, StreamHandler, DEBUG
import pathlib
import hashlib

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, FileResponse

from utils.data_model import User
from utils.cs_requests import CSRequestIterator, CSRequests
from utils.html_templates import HTMLTemplates

load_dotenv(verbose=True)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

app = FastAPI(
    title="たーけクラウドシステムAPI v2",
    description="たーけクラウドシステムの公式APIです。さまざまな機能を提供しています。",
    version="2.0.0-beta",
    terms_of_service="https://scratch.mit.edu/projects/934818132/",
    contact={
        "name": "ito-noizi",
        "url": "https://scratch.mit.edu/users/ito-noizi/",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)
cs_request_iterator = CSRequestIterator()
cs_server = CSRequests(cs_request_iterator)
html_templates = HTMLTemplates()


@app.get("/")
async def read_root():
    """テスト
    """
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}


@app.get("/")
async def home():
    return {
        "website": "https://scratch.mit.edu/studios/33110478/",
        "author": "@takechi-scratch in t-cloudsystem admin team",
        "help": "https://scratch.mit.edu/users/ito-noizi/"
    }


@app.get("/health/")
async def health():
    return {
        "version": "ver.2.0.0(beta)",
        "api_status": "OK",
        "cs_status": "OK" if cs_server.connected else "Not working"
    }


@app.get("/user/id/{user_id}/", response_model=User)
async def get_user_by_id(user_id: int):
    if not cs_server.connected:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "CS server is not working"})

    try:
        user = await cs_server.send_request("get_user_by_id", {"id": user_id})
    except RuntimeError as e:
        if str(e) == "User not found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "User not found"})

        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return User(**user)


@app.get("/user/name/{name}/", response_model=User)
async def get_user_by_name(name: str):
    if not cs_server.connected:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"error": "CS server is not working"})

    try:
        user = await cs_server.send_request("get_user_by_name", {"name": name})
    except RuntimeError as e:
        if str(e) == "User not found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "User not found"})

        logger.error(f"Error fetching user {name}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return User(**user)


@app.get("/user/{user_id}/", deprecated=True)
async def get_user_root(user_id: int):
    """上の2つのいずれかを利用してください。"""
    return RedirectResponse(url=f"/user/id/{user_id}/")


@app.get("/ads/{ad_id}/")
async def takechi_ad(ad_id: int, request: Request):
    if not cs_server.connected:
        return HTMLResponse(html_templates.ads_not_available, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    hashed_ip = hashlib.sha256(f"{request.client.host}__{ad_id}".encode()).hexdigest()

    try:
        res = await cs_server.send_request("view_ad", {"id": ad_id, "hashed_ip": hashed_ip})
    except RuntimeError as e:
        if str(e) == "Ad not found":
            return HTMLResponse(html_templates.ads_not_found, status_code=status.HTTP_404_NOT_FOUND)

        logger.error(f"Error fetching ad {ad_id}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return RedirectResponse(url=res["project_url"])


@app.websocket("/admin/cs_server/ws")
async def cs_server_websocket(websocket: WebSocket):
    await websocket.accept()

    # 認証メッセージを待機
    try:
        auth_message = await websocket.receive_json()
        admin_password = os.getenv("CS_SERVER_PASSWORD")

        if auth_message.get("type") != "auth" or auth_message.get("password") != admin_password:
            logger.error("Authentication failed for CS server WebSocket")
            await websocket.send_json({"error": "Authentication failed"})
            await websocket.close(code=1008, reason="Authentication failed")
            return

        await websocket.send_json({"type": "info", "message": "Authenticated successfully"})
        logger.info("Admin WebSocket authenticated successfully")

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        await websocket.close(code=1011, reason="Authentication error")
        return

    cs_server.connected = True

    try:
        async for request in cs_request_iterator:
            await websocket.send_json({"type": "request", "data": request.model_dump()})

            res = await websocket.receive_json()
            if res.get("type") != "response" or "data" not in res:
                logger.error(f"Invalid response type received: {res.get('type')}")

            response_data = res["data"]
            logger.debug(f"Received response: {response_data}")

            if response_data.get("id") != request.id:
                logger.error(f"Response ID mismatch!!: expected {request.id}, got {response_data.get('id')}")
                continue

            request.result = response_data.get("result")
            request.error = response_data.get("error")
            request.completed = True
    except WebSocketDisconnect:
        logger.info("Admin WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket communication: {e}")
        if websocket.open:
            await websocket.close(code=1011, reason="WebSocket error")
    finally:
        cs_server.connected = False


@app.get("/assets/{path:path}")
async def get_asset(path: str):
    try:
        assets_dir = pathlib.Path("assets").resolve()
        asset_path = (assets_dir / path).resolve()

        if not str(asset_path).startswith(str(assets_dir)):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})

        if not asset_path.exists() or not asset_path.is_file():
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})

        return FileResponse(asset_path)

    except (OSError, ValueError) as e:
        logger.warning(f"Invalid asset path requested: {path}, error: {e}")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})
