
import logging
import time
import sys

# Configure logging to see what's happening
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug_import")

print("DEBUG: Starting import test...", flush=True)
start_time = time.time()

try:
    print("DEBUG: Attempting to import pinecone...", flush=True)
    import pinecone
    print(f"DEBUG: pinecone imported in {time.time() - start_time:.2f}s", flush=True)
    
    print("DEBUG: Attempting to import Pinecone from pinecone...", flush=True)
    from pinecone import Pinecone
    print(f"DEBUG: Pinecone imported in {time.time() - start_time:.2f}s", flush=True)
    
except Exception as e:
    print(f"DEBUG: Import failed with error: {e}", flush=True)

print("DEBUG: Test finished.", flush=True)
