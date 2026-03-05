
import logging
import time
import sys
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_import")

print("DEBUG: Starting comprehensive import test...", flush=True)
start_overall = time.time()

def test_import(module_name, from_name=None):
    s = time.time()
    try:
        if from_name:
            print(f"DEBUG: Attempting 'from {module_name} import {from_name}'...", flush=True)
            exec(f"from {module_name} import {from_name}")
        else:
            print(f"DEBUG: Attempting 'import {module_name}'...", flush=True)
            exec(f"import {module_name}")
        print(f"DEBUG: Success in {time.time() - s:.4f}s", flush=True)
    except Exception as e:
        print(f"DEBUG: FAILED: {e}", flush=True)

# Test critical path
test_import("pydantic_settings", "BaseSettings")
test_import("app.core.settings", "get_settings")

print("DEBUG: Testing get_settings() call...", flush=True)
s = time.time()
try:
    from app.core.settings import get_settings
    settings = get_settings()
    print(f"DEBUG: get_settings() returned in {time.time() - s:.4f}s", flush=True)
except Exception as e:
    print(f"DEBUG: get_settings() FAILED: {e}", flush=True)

test_import("pinecone", "Pinecone")
test_import("google.adk")
test_import("app.services.question_service", "QuestionService")
test_import("app.agents.interviewer.tools", "get_interviewer_tools")
test_import("app.agents.interviewer.agent", "InterviewerAgent")

print(f"DEBUG: Total time: {time.time() - start_overall:.4f}s", flush=True)
print("DEBUG: Test finished.", flush=True)
