import requests
import json
import time

def test_session_start():
    url = "http://localhost:8000/session/start"
    payload = {
        "user_id": "test_user_ai",
        "role": "Software Engineer",
        "topics": ["algorithms"],
        "difficulty": "medium",
        "mode": "buddy"
    }
    import jwt
    secret = "roundzero-super-secret-key"
    token = jwt.encode({"sub": "test_user_ai", "name": "AI Tester"}, secret, algorithm="HS256")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Give the server a moment to settle
    time.sleep(2)
    test_session_start()
