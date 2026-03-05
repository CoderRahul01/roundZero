import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/ws?mode=buddy&session_id=test"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.send('{"text":"{}"}')
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_ws())
