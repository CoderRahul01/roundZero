# RoundZero Deployment Guide

## Overview

This guide covers deploying RoundZero to production:
- **Frontend**: Vercel (React/Vite)
- **Backend**: Railway or Render (FastAPI/Python)

## Prerequisites

- GitHub account
- Vercel account
- Railway or Render account
- All API keys ready (see Environment Variables section)

---

## Part 1: Backend Deployment (Railway or Render)

### Option A: Railway (Recommended)

1. **Push code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Create Railway Project**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and use `railway.json`

3. **Configure Environment Variables**
   
   In Railway dashboard, go to Variables tab and add:

   ```env
   # Required
   ANTHROPIC_API_KEY=your_anthropic_key
   GEMINI_API_KEY=your_gemini_key
   STREAM_API_KEY=your_stream_key
   STREAM_API_SECRET=your_stream_secret
   
   # Database (Neon Postgres)
   DATABASE_URL=your_neon_connection_string
   NEON_AUTH_URL=your_neon_auth_url
   NEON_AUTH_JWKS_URL=your_neon_jwks_url
   NEON_AUTH_ISSUER=your_neon_issuer
   NEON_AUTH_AUDIENCE=your_neon_audience
   
   # MongoDB
   MONGODB_URI=your_mongodb_atlas_uri
   
   # CORS (Add your Vercel domain after frontend deployment)
   CORS_ALLOW_ORIGINS=https://your-app.vercel.app,http://localhost:5173
   
   # Optional
   PINECONE_API_KEY=your_pinecone_key
   PINECONE_INDEX=interview-questions
   USE_PINECONE=false
   USE_VISION=false
   
   # App Config
   ENVIRONMENT=production
   LOG_LEVEL=info
   JWT_SECRET=your_secure_random_string_here
   ```

4. **Deploy**
   - Railway will automatically deploy
   - Wait for build to complete
   - Note your backend URL: `https://your-app.up.railway.app`

5. **Verify Deployment**
   ```bash
   curl https://your-app.up.railway.app/health
   ```

### Option B: Render

1. **Create Render Account** at [render.com](https://render.com)

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will detect `render.yaml`

3. **Configure Environment Variables** (same as Railway above)

4. **Deploy** and note your URL: `https://your-app.onrender.com`

---

## Part 2: Frontend Deployment (Vercel)

1. **Update Frontend API URL**
   
   Create `frontend/.env.production`:
   ```env
   VITE_API_URL=https://your-backend-url.up.railway.app
   ```

2. **Deploy to Vercel**
   
   ```bash
   # Install Vercel CLI
   npm install -g vercel
   
   # Deploy
   cd frontend
   vercel
   ```
   
   Or use Vercel Dashboard:
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Vercel will auto-detect Vite
   - Set Root Directory to `frontend`
   - Add environment variable: `VITE_API_URL=https://your-backend-url`
   - Click "Deploy"

3. **Note Your Frontend URL**: `https://your-app.vercel.app`

---

## Part 3: Connect Frontend and Backend

1. **Update Backend CORS**
   
   In Railway/Render, update the `CORS_ALLOW_ORIGINS` variable:
   ```env
   CORS_ALLOW_ORIGINS=https://your-app.vercel.app,http://localhost:5173
   ```

2. **Redeploy Backend** (Railway/Render will auto-redeploy on env change)

3. **Test the Connection**
   - Visit `https://your-app.vercel.app`
   - Try starting an interview
   - Check browser console for errors

---

## Part 4: Database Setup

### Neon Postgres

1. Create database at [neon.tech](https://neon.tech)
2. Copy connection string
3. Add to backend env as `DATABASE_URL`

### MongoDB Atlas

1. Create cluster at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create database user
3. Whitelist IP: `0.0.0.0/0` (all IPs for serverless)
4. Copy connection string
5. Add to backend env as `MONGODB_URI`

---

## Troubleshooting

### CORS Errors

**Problem**: Frontend can't connect to backend

**Solution**:
1. Check `CORS_ALLOW_ORIGINS` includes your Vercel URL
2. Ensure no trailing slashes in URLs
3. Check browser console for exact error

### Backend Won't Start

**Problem**: Railway/Render deployment fails

**Solution**:
1. Check build logs for missing dependencies
2. Verify all required env vars are set
3. Check Python version (should be 3.13)
4. Ensure `uv` is installing correctly

### Voice Not Working

**Problem**: AI voice doesn't play

**Solution**:
1. Check browser console for TTS errors
2. Verify Stream.io credentials
3. Check HTTPS (required for WebRTC)
4. Test with different browser

### Questions Not Progressing

**Problem**: Interview stuck on one question

**Solution**:
1. Check backend logs for `advance_question` calls
2. Verify Gemini API key is valid
3. Check MongoDB connection for question storage

---

## Environment Variables Reference

### Required Variables

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `ANTHROPIC_API_KEY` | Claude API key | [console.anthropic.com](https://console.anthropic.com) |
| `GEMINI_API_KEY` | Gemini API key | [aistudio.google.com](https://aistudio.google.com) |
| `STREAM_API_KEY` | Stream.io key | [getstream.io](https://getstream.io) |
| `STREAM_API_SECRET` | Stream.io secret | [getstream.io](https://getstream.io) |
| `DATABASE_URL` | Neon Postgres URL | [neon.tech](https://neon.tech) |
| `MONGODB_URI` | MongoDB Atlas URI | [mongodb.com](https://mongodb.com) |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PINECONE_API_KEY` | Pinecone vector DB | None |
| `USE_PINECONE` | Enable Pinecone | `false` |
| `USE_VISION` | Enable vision analysis | `false` |
| `LOG_LEVEL` | Logging level | `info` |

---

## Post-Deployment Checklist

- [ ] Backend health check passes
- [ ] Frontend loads without errors
- [ ] Can create new interview session
- [ ] Questions are generated
- [ ] Voice/audio works
- [ ] Interview progresses through questions
- [ ] Scorecard generates at end
- [ ] No CORS errors in console

---

## Monitoring

### Railway
- View logs: Railway dashboard → Deployments → Logs
- Metrics: Railway dashboard → Metrics

### Render
- View logs: Render dashboard → Logs
- Metrics: Render dashboard → Metrics

### Vercel
- View logs: Vercel dashboard → Deployments → Function Logs
- Analytics: Vercel dashboard → Analytics

---

## Scaling Considerations

### Free Tier Limits

**Railway Free**:
- $5 credit/month
- ~500 hours runtime
- Sleeps after 30min inactivity

**Render Free**:
- 750 hours/month
- Sleeps after 15min inactivity
- Slower cold starts

**Vercel Free**:
- 100GB bandwidth/month
- Unlimited deployments
- Edge network included

### Upgrade Path

When you need more:
1. **Railway Pro**: $20/month, no sleep, better performance
2. **Render Standard**: $7/month, no sleep, faster
3. **Vercel Pro**: $20/month, more bandwidth, analytics

---

## Support

For issues:
1. Check logs first (Railway/Render/Vercel dashboards)
2. Review browser console errors
3. Verify all environment variables
4. Test backend health endpoint
5. Check API key validity

---

## Quick Deploy Commands

```bash
# Backend (Railway)
railway login
railway init
railway up

# Frontend (Vercel)
vercel login
vercel --prod

# Check deployment
curl https://your-backend.up.railway.app/health
curl https://your-frontend.vercel.app
```

---

**Deployment complete!** Your RoundZero AI Interview Coach is now live. 🚀
