# roundZero Quick Troubleshooting Guide

## \ud83d\ude80 Quick Start

```bash
cd /path/to/roundZero/backend
bash run_diagnostic.sh
```

## \ud83d\udd34 Common Errors & Fixes

### Error: WebSocket 400 Bad Request

**ROOT CAUSE:** Middleware blocking WebSocket upgrade

**FIX #1 - JWT Middleware (Most Common)**

- Ensure `JWTAuthMiddleware` skips WebSocket scopes.

**FIX #2 - CORS Middleware**

- Use `CORSASGIMiddleware` instead of Starlette's `CORSMiddleware`.

---

### Error: Gemini 1008 Model Not Found

**ROOT CAUSE:** Incorrect model name or unavailable for API key

**FIX:**

- Update model name in `.env`: `GEMINI_MODEL=gemini-2.5-flash-native-audio-latest`

---

### Error: Port 8000 Already in Use

**ROOT CAUSE:** macOS AirPlay Receiver uses port 8000

**FIX:**

- Use port **8080** for the backend.
- Update `backend/app/main.py` and `frontend/src/api.ts`.
- Disable AirPlay Receiver in System Settings.

---

## \ud83d\udccb Pre-Flight Checklist

- [ ] All API keys set in `.env`
- [ ] Port 8080 available (not 8000)
- [ ] Pinecone index created and seeded
- [ ] Redis instance active
- [ ] Neon database accessible
- [ ] Correct Gemini model name

**Verify with:**

```bash
cd backend
bash run_diagnostic.sh
```
