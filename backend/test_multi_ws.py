import asyncio
import websockets
import json
import sys

async def connect_and_disconnect(user_id, session_id):
    uri = f"ws://localhost:8000/ws/{user_id}/{session_id}?mode=behavioral"
    print(f"Attempting WebSocket connection to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"SUCCESS: Connected to {session_id}")
            # Send end session signal
            await websocket.send(json.dumps({"type": "end_session"}))
            print("Sent end_session signal.")
            # Small delay to allow cleanup
            await asyncio.sleep(0.5)
        print(f"Disconnected from {session_id}")
        return True
    except Exception as e:
        print(f"FAILURE: Connection failed for {session_id}: {e}")
        return False

async def main():
    user_id = "test_user"
    # Test 1: First connection
    success1 = await connect_and_disconnect(user_id, "session_1")
    if not success1:
        sys.exit(1)
    
    print("\nAttempting second connection (different session)...")
    success2 = await connect_and_disconnect(user_id, "session_2")
    if not success2:
        sys.exit(1)

    print("\nAttempting third connection (same session ID - should fail if not cleaned up properly)...")
    success3 = await connect_and_disconnect(user_id, "session_1")
    if not success3:
        sys.exit(1)

    print("\nALL TESTS PASSED: Multiple connections successful.")

if __name__ == "__main__":
    asyncio.run(main())
