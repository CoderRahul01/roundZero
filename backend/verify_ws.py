import asyncio
import websockets
import json
import sys

async def verify_handshake():
    uri = "ws://localhost:8000/ws/test_user/test_session_id?mode=behavioral"
    print(f"Attempting WebSocket handshake with {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("SUCCESS: WebSocket handshake completed.")
            # Send a tiny PCM-like byte chunk to see if it accepts
            await websocket.send(b'\x00\x00' * 10)
            print("SUCCESS: Sent binary data.")
            
            # Send an end session signal
            await websocket.send(json.dumps({"type": "end_session"}))
            print("SUCCESS: Sent end_session signal.")
            
            # Wait for a potential close or response
            try:
                msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"RECEIVED: {msg[:100]}...")
            except asyncio.TimeoutError:
                print("No immediate response from server (expected if no agent output triggered yet).")
            
    except Exception as e:
        print(f"FAILURE: WebSocket connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Note: Requires uvicorn to be running
    try:
        asyncio.run(verify_handshake())
    except KeyboardInterrupt:
        pass
