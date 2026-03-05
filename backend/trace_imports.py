import sys
import os
import threading
import time

sys.path.append(os.getcwd())

def import_with_timeout(m, timeout=10):
    res = {"success": False, "error": None}
    def target():
        try:
            __import__(m)
            res["success"] = True
        except Exception as e:
            res["error"] = e
            
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"  TIMEOUT loading {m}")
        return False
    if not res["success"]:
        print(f"  ERROR loading {m}: {res['error']}")
        return False
    print(f"  SUCCESS loading {m}")
    return True

modules_to_test = [
    "app.core.settings",
    "app.core.logger",
    "app.core.middleware",
    "app.core.redis_client",
    "app.services.user_service",
    "app.services.session_service",
    "app.services.supermemory_service",
    "app.api.schemas",
    "app.agents.interviewer.tools",
    "app.agents.interviewer.prompts",
    "app.agents.interviewer.agent",
    "app.api.profile",
    "app.api.websocket",
    "app.api.routes",
    "app.main"
]

for m in modules_to_test:
    print(f"Loading {m}...")
    import_with_timeout(m)
