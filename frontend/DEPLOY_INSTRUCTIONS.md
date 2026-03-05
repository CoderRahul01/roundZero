# Production Deployment Guide — RoundZero

The backend has been configured for Cloud Run and the frontend for Vercel.
Here are the exact manual steps to run or complete the deployment.

---

## 1. Cloud Run Deployment (Backend)

The deployment has **finished successfully**!
Your live backend URL is:
`https://roundzero-backend-543685349875.asia-south1.run.app`

**Known expected behavior in production:**
Cloud Run has a timeout. We set `--timeout 3600` (1 hour) which is plenty for any interview session. We also set `--session-affinity` which is mandatory for WebSocket routing to work properly across containers.

---

## 2. Vercel Deployment (Frontend)

Since you said "use the existing one" (which is `roundzero-xi.vercel.app`), follow these manual steps to connect it to the new Cloud Run backend:

### Step 2a: Push your code to GitHub

The frontend code now contains `vercel.json` (to fix React Router blank pages) and `api.ts` checks for `VITE_BACKEND_URL`. Push these changes to your repo:

```bash
git add .
git commit -m "chore: production deploy configs for Vercel and Cloud Run"
git push origin main
```

_Vercel will trigger an automatic build when you push._

### Step 2b: Set Vercel Environment Variables

Go to your **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**:

1. Add a new variable:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: `https://roundzero-backend-543685349875.asia-south1.run.app`
   - **Environments**: Select Production, Preview, Development
2. Add another variable:
   - **Key**: `VITE_NEON_AUTH_URL`
   - **Value**: `https://ep-weathered-sky-a1gk9bn4.neonauth.ap-southeast-1.aws.neon.tech/neondb/auth`
3. Hit Save.

### Step 2c: Redeploy in Vercel

Because environment variables are baked into the frontend during build time, you must trigger a new deployment for the changes to take effect:

1. Go to the **Deployments** tab in Vercel.
2. Click the three dots next to your latest deployment.
3. Select **Redeploy**.

---

## 3. Post-Deployment Checks

Once both are deployed, check if it works:

1. Go to `https://roundzero-xi.vercel.app`
2. Run through the interview setup screen
3. The AI should speak and respond.

If the WebSocket fails, you can test the backend directly:

```bash
npx wscat -c "wss://<CLOUD_RUN_URL_WITHOUT_HTTPS>/ws/test/test?mode=buddy"
```

_(You should see `Connected (press CTRL+C to quit)`)_
