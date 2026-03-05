
import sys
from unittest.mock import MagicMock

# Mock anthropic to prevent heavy import in google.adk
sys.modules["anthropic"] = MagicMock()
sys.modules["anthropic.types"] = MagicMock()

import time

print("DEBUG: Attempting 'import google.adk' with anthropic mocked...")
start = time.perf_counter()
import google.adk
end = time.perf_counter()
print(f"DEBUG: Success in {end - start:.4f}s")

# Check if Gemini still works
from google.adk.models import google_llm
print(f"DEBUG: Gemini imported: {google_llm.Gemini}")
