# roundZero Diagnostic Suite

## Overview

This comprehensive diagnostic script tests all components of the roundZero AI interview coach system to identify configuration issues, connectivity problems, and integration failures.

## What It Tests

### 1. **Environment Configuration** \u2705

- Validates all required and optional environment variables
- Checks for proper API key configuration
- Verifies database connection strings

### 2. **Backend Health** \ud83c\udfe5

- Tests if backend server is running
- Validates health endpoint
- Checks CORS configuration
- Verifies all HTTP routes are accessible

### 3. **WebSocket Connection** \ud83d\udd0c

- Tests WebSocket handshake (101 Switching Protocols)
- Validates bidirectional message passing
- Identifies middleware interference (400 Bad Request issues)
- Tests graceful connection close
- **Diagnoses common issues**:
  - CORS middleware blocking WS upgrades
  - JWT middleware intercepting connections
  - BaseHTTPMiddleware incompatibility
  - Route path mismatches

### 4. **Gemini API** \ud83e\udd16

- Validates Google API key
- Lists all available Gemini models
- Identifies Live API compatible models
- Tests specific model connectivity
- **Detects model errors** (1008 Model Not Found)

### 5. **Pinecone Vector Database** \ud83d\udcca

- Tests Pinecone API connectivity
- Lists available indexes
- Validates question bank access
- Checks vector dimensions and counts

### 6. **Upstash Redis** \ud83d\udcbe

- Tests REST API connectivity
- Validates SET/GET operations
- Checks session storage capability

### 7. **Full Pipeline Integration** \ud83d\udd04

- Tests complete interview flow:
  1. User profile creation
  2. Session initialization
  3. WebSocket connection to active session
  4. Agent response verification

## Usage

### Quick Start

```bash
# Navigate to your backend directory
cd /path/to/roundZero/backend

# Run the diagnostic
bash run_diagnostic.sh
```

### Manual Execution

```bash
# From backend directory with .env file
cd /path/to/roundZero/backend

# Using uv (recommended)
uv run python diagnose_roundzero.py

# Using pip
python diagnose_roundzero.py
```

### Custom Backend URL

```bash
# Set custom backend URL
export BACKEND_URL=http://localhost:8080
uv run python diagnose_roundzero.py
```

## Prerequisites

The diagnostic script will automatically install required dependencies:

- `httpx` - For HTTP testing
- `websockets` - For WebSocket testing
- `python-dotenv` - For environment variable loading

## Output

### Terminal Output

The diagnostic provides color-coded real-time results:

- \u2705 **Green** - Test passed
- \u274c **Red** - Test failed
- \u26a0\ufe0f **Yellow** - Warning (non-critical)
- \u2139\ufe0f **Blue** - Informational
