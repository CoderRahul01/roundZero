
import time
import sys

def test_import(module_name):
    print(f"DEBUG: Attempting 'import {module_name}'...")
    start = time.perf_counter()
    try:
        __import__(module_name)
        end = time.perf_counter()
        print(f"DEBUG: Success in {end - start:.4f}s")
    except Exception as e:
        print(f"DEBUG: Failed: {e}")

# Test sub-imports of google.adk
test_import("google.adk.version")
test_import("google.adk.agents.context")
test_import("google.adk.agents.llm_agent")
test_import("google.adk.runners")
