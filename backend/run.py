import os
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file into os.environ
load_dotenv()

# Keep WS protocol libraries at WARNING — DEBUG is very noisy once stable
logging.basicConfig(level=logging.INFO)
for lib_logger in ["wsproto", "websockets", "uvicorn.protocols.websockets"]:
    logging.getLogger(lib_logger).setLevel(logging.WARNING)

from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting RoundZero on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        ws="wsproto",                    # wsproto handles browser WS correctly
        ws_per_message_deflate=False,    # deflate breaks binary audio streaming
        timeout_keep_alive=300,          # keep long-running interview sessions alive
    )
