#!/usr/bin/env python3
"""Quick test to verify Stream.io token generation"""
import os
from dotenv import load_dotenv
load_dotenv()

from settings import get_settings
import jwt
import time

settings = get_settings()

print("=" * 60)
print("STREAM.IO TOKEN GENERATION TEST")
print("=" * 60)

# Check environment
api_secret = settings.stream_api_secret or os.getenv("STREAM_API_SECRET")
api_key = settings.stream_api_key or os.getenv("STREAM_API_KEY")

print(f"\n1. Environment Check:")
print(f"   STREAM_API_KEY: {'✓ SET' if api_key else '✗ NOT SET'}")
print(f"   STREAM_API_SECRET: {'✓ SET' if api_secret else '✗ NOT SET'}")

if api_secret:
    print(f"   Secret length: {len(api_secret)} chars")
    
    # Generate token
    payload = {
        "user_id": "test_user",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    token = jwt.encode(payload, api_secret, algorithm="HS256")
    
    print(f"\n2. Token Generation:")
    print(f"   ✓ Token generated successfully")
    print(f"   Token length: {len(token)} chars")
    print(f"   Token preview: {token[:50]}...")
else:
    print(f"\n2. Token Generation:")
    print(f"   ✗ FAILED - STREAM_API_SECRET not set")

print("\n" + "=" * 60)
