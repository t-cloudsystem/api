import os
from logging import getLogger, StreamHandler, DEBUG
import pathlib
import hashlib

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, FileResponse

from utils.data_model import APIInfo, HealthInfo, User, Team, APIError, ReportData, report_message
from utils.cs_requests import CSRequestIterator, CSRequests
from utils.html_templates import HTMLTemplates, docs_description
from utils.exceptions import CSServerNotConnectedError
from utils.discord_webhook import DiscordWebhook

load_dotenv(verbose=True)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False


tags_metadata = [
    {
        "name": "Server Info",
        "description": "サーバーに関する情報を取得します。",
    },
    {
        "name": "Users",
        "description": "ユーザーデータを取得します。",
    },
    {
        "name": "Teams",
        "description": "チームデータを取得します。",
    },
    {
        "name": "Ads",
        "description": "takechi-Adsの表示や情報を取得します。",
    },
    {
        "name": "Internal Endpoint",
        "description": "API内部や管理者が用いるエンドポイントです。ほとんどは認証が必要です。",
    },
]

app = FastAPI(
    title="たーけクラウドシステムAPI v2",
    description=docs_description,
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
    openapi_tags=tags_metadata,
)
cs_request_iterator = CSRequestIterator()
cs_server = CSRequests(cs_request_iterator)
html_templates = HTMLTemplates()
discord_webhook = DiscordWebhook(os.getenv("DISCORD_WEBHOOK_URL"))
responses_templates = {
    404: {"model": APIError, "description": "Not Found"},
    500: {"model": APIError, "description": "Internal Server Error"},
    503: {"model": APIError, "description": "Service Unavailable"},
}


@app.exception_handler(CSServerNotConnectedError)
async def unicorn_exception_handler(request: Request, exc: CSServerNotConnectedError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": exc.message},
    )


@app.get("/", response_model=APIInfo, tags=["Server Info"])
async def api_info():
    """APIの基本情報を取得します。"""
    return APIInfo()


@app.get("/health/", response_model=HealthInfo, tags=["Server Info"])
async def get_health():
    """APIの稼働状態を取得します。"""
    return HealthInfo(
        version="ver.2.0.0(beta)",
        api_status="OK",
        cs_status="OK" if cs_server.connected else "Not working"
    )


@app.post("/report/", tags=["Server Info"])
async def report_issue(report_data: ReportData):
    """API経由でクイック報告を行います。定型文のみ送信できるため、Scratchにおけるルールには違反しません。"""
    try:
        await discord_webhook.send_quick_report(report_data.user_id, report_message[report_data.type])
    except Exception as e:
        logger.error(f"Error sending report to Discord: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=APIError(message="Failed to send report to Discord."))

    return JSONResponse(status_code=status.HTTP_200_OK, content={"message": "Report sent successfully."})


@app.get("/user/id/{user_id}/", response_model=User, responses=responses_templates, tags=["Users"])
async def get_user_by_id(user_id: int):
    """ユーザーIDからユーザーデータ（ユーザー名、ポイントなど）を取得します。"""
    if not cs_server.connected:
        raise CSServerNotConnectedError()

    try:
        user = await cs_server.send_request("get_user_by_id", {"id": user_id})
    except RuntimeError as e:
        if str(e) == "User not found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "User not found"})

        logger.error(f"Error fetching user {user_id}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return User(**user)


@app.get("/user/name/{user_name}/", response_model=User, responses=responses_templates, tags=["Users"])
async def get_user_by_name(user_name: str):
    """ユーザー名からユーザーデータ（ユーザーID、ポイントなど）を取得します。"""
    if not cs_server.connected:
        raise CSServerNotConnectedError()

    try:
        user = await cs_server.send_request("get_user_by_name", {"name": user_name})
    except RuntimeError as e:
        if str(e) == "User not found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "User not found"})

        logger.error(f"Error fetching user {user_name}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return User(**user)


@app.get("/user/{user_id}/", deprecated=True, tags=["Users"])
async def get_user_root(user_id: int):
    """ユーザーIDからユーザーデータを取得します。上の2つのいずれかを利用してください。"""
    return RedirectResponse(url=f"/user/id/{user_id}/")


@app.get("/team/{team_id}/", response_model=Team, responses=responses_templates, tags=["Teams"])
async def get_team(team_id: int):
    """チームIDからチームデータを取得します。"""
    if not cs_server.connected:
        raise CSServerNotConnectedError()

    try:
        team = await cs_server.send_request("get_team_by_id", {"id": team_id})
    except RuntimeError as e:
        if str(e) == "Team not found":
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Team not found"})

        logger.error(f"Error fetching team {team_id}: {str(e)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "unknown error occurred"})

    return Team(**team)


@app.get("/ads/{ad_id}/",
         responses={200: {"description": "Redirect to the ad project"},
                    404: {"content": {"text/html": {}}, "description": "Ad not found"},
                    503: {"content": {"text/html": {}}, "description": "CS server is not working"}}, tags=["Ads"])
async def takechi_ad(ad_id: int, request: Request):
    """takechi-Adsのプロジェクトにリダイレクトします。
       アクセスできない場合は、HTMLでエラーメッセージを表示します。
    """
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
    """CSサーバー用WebSocket接続。認証後、CSサーバーへのリクエストを送信します。"""
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


@app.get("/assets/{path:path}", tags=["Internal Endpoint"])
async def get_asset(path: str):
    """HTMLテンプレートや静的ファイルを取得します。"""
    try:
        assets_dir = pathlib.Path("assets/public/").resolve()
        asset_path = (assets_dir / path).resolve()

        if not str(asset_path).startswith(str(assets_dir)):
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})

        if not asset_path.exists() or not asset_path.is_file():
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})

        return FileResponse(asset_path)

    except (OSError, ValueError) as e:
        logger.warning(f"Invalid asset path requested: {path}, error: {e}")
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"error": "Asset not found"})
