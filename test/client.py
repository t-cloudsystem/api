import asyncio
import websockets


async def connect_to_websocket():
    uri = "ws://localhost:8080/pipe"
    async with websockets.connect(uri, ping_timeout=10) as websocket:
        # サーバーにメッセージを送信
        await websocket.send("Hello, WebSocket!")

        # サーバーからのメッセージを受信
        response = await websocket.recv()
        print(f"Received from server: {response}")

# asyncioでクライアントを実行
asyncio.get_event_loop().run_until_complete(connect_to_websocket())
