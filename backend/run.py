import os
from main import runner, app

if __name__ == "__main__":
    if runner:
        # Use the Vision Agents framework runner
        runner.run()
    else:
        # Fallback to direct uvicorn
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
