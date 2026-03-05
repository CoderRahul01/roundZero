# RoundZero Frontend (React)

Premium interview simulator UI built with React + TypeScript (Create React App). Connects to the FastAPI backend and Stream WebRTC.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # add backend + Supabase keys
```

## Scripts

- `npm start` — dev server on http://localhost:3000
- `npm run build` — production build to `build/`
- `npm test -- --watch=false` — run unit tests once
- `npm run lint` — ESLint over `src/**/*.{ts,tsx}`

## Env Vars

```
REACT_APP_BACKEND_URL=http://localhost:8080
REACT_APP_NEON_AUTH_URL=
REACT_APP_ALLOW_LEGACY_DEV_AUTH=false
REACT_APP_JWT_SECRET=

Auth
- The frontend now uses Neon Auth (`REACT_APP_NEON_AUTH_URL`) and sends the Neon session token as `Authorization: Bearer <token>` to the backend.
- Sign in/sign up is integrated into the setup flow and blocks interview creation until authentication succeeds.
- `REACT_APP_ALLOW_LEGACY_DEV_AUTH=true` keeps a local mock-token fallback for local-only debugging; keep it disabled in production.
```

## Production Notes

- Backend URL must be HTTPS in production.
- Enable HTTP/2 + gzip at the edge; assets are already hashed.
- Set `GENERATE_SOURCEMAP=false` in CI to avoid leaking code in public builds.
