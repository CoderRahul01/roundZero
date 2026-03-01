# RoundZero Deployment Checklist

## Pre-Deployment

- [ ] All code committed to GitHub
- [ ] `.env` files are in `.gitignore` (never commit secrets!)
- [ ] All API keys ready and valid
- [ ] Databases created (Neon Postgres, MongoDB Atlas)

## Backend Deployment (Railway/Render)

- [ ] Create Railway/Render account
- [ ] Connect GitHub repository
- [ ] Add all environment variables (see DEPLOYMENT.md)
- [ ] Deploy backend
- [ ] Test health endpoint: `curl https://your-backend.up.railway.app/health`
- [ ] Note backend URL for frontend config

## Frontend Deployment (Vercel)

- [ ] Create `frontend/.env.production` with backend URL
- [ ] Deploy to Vercel (CLI or dashboard)
- [ ] Test frontend loads: visit `https://your-app.vercel.app`
- [ ] Note frontend URL for backend CORS

## Connect Frontend ↔ Backend

- [ ] Update backend `CORS_ALLOW_ORIGINS` with Vercel URL
- [ ] Redeploy backend (auto-triggers on env change)
- [ ] Test connection: start an interview on frontend
- [ ] Check browser console for CORS errors (should be none)

## Functional Testing

- [ ] Can access frontend homepage
- [ ] Can start new interview session
- [ ] Questions are generated and displayed
- [ ] Can speak/type answers
- [ ] Interview progresses through questions
- [ ] Scorecard generates at end
- [ ] No console errors

## Post-Deployment

- [ ] Share frontend URL with users
- [ ] Monitor logs for errors
- [ ] Set up uptime monitoring (optional)
- [ ] Document any issues for future fixes

## Environment Variables Checklist

### Backend (Required)
- [ ] `ANTHROPIC_API_KEY`
- [ ] `GEMINI_API_KEY`
- [ ] `STREAM_API_KEY`
- [ ] `STREAM_API_SECRET`
- [ ] `DATABASE_URL`
- [ ] `MONGODB_URI`
- [ ] `CORS_ALLOW_ORIGINS` (with Vercel URL)
- [ ] `JWT_SECRET`

### Frontend (Required)
- [ ] `VITE_API_URL` (backend URL)

## Quick Test Commands

```bash
# Test backend health
curl https://your-backend.up.railway.app/health

# Test frontend
curl https://your-app.vercel.app

# Test CORS (from browser console on frontend)
fetch('https://your-backend.up.railway.app/health')
  .then(r => r.json())
  .then(console.log)
```

## Troubleshooting Quick Fixes

### CORS Error
```env
# Backend: Update CORS_ALLOW_ORIGINS
CORS_ALLOW_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

### Backend Won't Start
- Check Railway/Render logs
- Verify all required env vars are set
- Check Python version (3.13)

### Frontend Can't Connect
- Verify `VITE_API_URL` is correct
- Check backend is running (health endpoint)
- Check CORS configuration

---

**Ready to deploy?** Follow DEPLOYMENT.md for detailed steps!
