import sys
import os

print("Starting import trace...")

try:
    print("1. Importing pydantic...")
    from pydantic import Field
    print("1. Success")
    
    print("2. Importing pydantic_settings...")
    from pydantic_settings import BaseSettings
    print("2. Success")
    
    print("3. Importing app.core.settings...")
    sys.path.append(os.getcwd())
    from app.core.settings import get_settings
    print("3. Success")
    
    print("4. Importing app.core.middleware...")
    from app.core.middleware import AuthTokenVerifier
    print("4. Success")
    
except Exception as e:
    print(f"Error: {e}")
