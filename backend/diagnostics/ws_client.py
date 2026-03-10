import asyncio
import json
import websockets
import sys

async def test_ws_handshake(user_id, session_id, base_url="ws://localhost:8000"):
    """
    Diagnostic tool to test the WebSocket handshake and heartbeat.
    Run this against a running backend.
    """
    uri = f"{base_url}/ws/{user_id}/{session_id}?mode=buddy"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected! ✅")
            
            # 1. Listen for initial greeting or ping
            print("Waiting for messages...")
            for _ in range(3):
                msg = await websocket.recv()
                data = json.loads(msg)
                print(f"Received: {data}")
                
                if data.get("type") == "ping":
                    print("Received heartbeat ping. Sending pong... 💓")
                    await websocket.send(json.dumps({"type": "pong"}))
                
            print("Handshake and heartbeat test passed. Closing connection.")
            
    except Exception as e:
        print(f"Connection failed: {e} ❌")
        sys.exit(1)

if __name__ == "__main__":
    import uuid
    u_id = f"test_user_{uuid.uuid4().hex[:4]}"
    s_id = f"test_sess_{uuid.uuid4().hex[:4]}"
    asyncio.run(test_ws_handshake(u_id, s_id))
