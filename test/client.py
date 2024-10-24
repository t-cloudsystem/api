import asyncio
import websockets


async def connect_to_websocket():
    uri = "ws://127.0.0.1:50000/pipe"
    try:
        async with websockets.connect(uri, ping_timeout=10, close_timeout=20) as websocket:
            # サーバーにメッセージを送信
            await websocket.send("Hello, WebSocket!")

            # サーバーからのメッセージを受信
            response = await websocket.recv()
            print(f"Received from server: {response}")
    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.InvalidURI, websockets.exceptions.ConnectionClosedOK) as e:
        print(f"WebSocket error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# asyncioでクライアントを実行
asyncio.run(connect_to_websocket())
