import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file into os.environ
load_dotenv()

from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Railway requires binding to 0.0.0.0 and the assigned PORT
    uvicorn.run(app, host="0.0.0.0", port=port)
