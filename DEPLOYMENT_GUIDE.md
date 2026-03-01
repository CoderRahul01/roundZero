# Free Tier Deployment Guide

## Overview

This guide walks you through deploying RoundZero AI Interview Coach using free tier services:
- **Backend**: Railway (Free tier: 500 hours/month, $5 credit)
- **Frontend**: Vercel (Free tier: Unlimited hobby projects)
- **Database**: MongoDB Atlas (Free tier: 512MB)
- **Redis**: Upstash (Free tier: 10K commands/day)

## Prerequisites

1. GitHub account
2. Railway account (https://railway.app)
3. Vercel account (https://vercel.com)
4. MongoDB Atlas account (https://www.mongodb.com/cloud/atlas)
5. Upstash account (https://upstash.com)
6. Groq API key (https://console.groq.com)

## Step 1: Setup MongoDB Atlas (Database)

1. Go to https://www.mongodb.com/cloud/atlas/register
2. Create a free cluster (M0 Sandbox - 512MB)
3. Create database user:
   - Username: `roundzero`
   - Password: Generate strong password
4. Add IP whitelist: `0.0.0.0/0` (allow from anywhere)
5. Get connection string:
   - Click "Connect" → "Connect your application"
   - Copy connection string: `mongodb+srv://roundzero:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
6. Save this as `MONGODB_URI`

## Step 2: Setup Upstash Redis (Session Storage)

1. Go to https://console.upstash.com
2. Create new Redis database:
   - Name: `roundzero-sessions`
   - Type: Regional
   - Region: Choose closest to your Railway region
3. Copy credentials:
   - `UPSTASH_REDIS_REST_URL`: https://xxx.upstash.io
   - `UPSTASH_REDIS_REST_TOKEN`: Your token
4. Save these values

## Step 3: Get Groq API Key (AI)

1. Go to https://console.groq.com/keys
2. Sign up (no credit card required)
3. Create new API key
4. Copy key: `gsk_xxxxxxxxxxxxx`
5. Save as `GROQ_API_KEY`

## Step 4: Deploy Backend to Railway

### 4.1 Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit with free tier deployment"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/roundzero.git
git branch -M main
git push -u origin main
```

### 4.2 Deploy on Railway

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `roundzero` repository
4. Railway will auto-detect the configuration from `railway.toml`

### 4.3 Configure Environment Variables

In Railway dashboard, add these environment variables:

```bash
# Free Tier Configuration
USE_FREE_TIER=true
ENVIRONMENT=production

# Database
MONGODB_URI=mongodb+srv://roundzero:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority

# Redis Session Store
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token_here

# AI Configuration
GROQ_API_KEY=gsk_xxxxxxxxxxxxx

# JWT Secret (generate random string)
JWT_SECRET=your_random_secret_here_min_32_chars

# CORS (will update after Vercel deployment)
CORS_ORIGINS=http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_MAX=10
RATE_LIMIT_WINDOW_SECONDS=60

# Logging
LOG_LEVEL=info

# Python
PYTHONUNBUFFERED=1
```

### 4.4 Generate JWT Secret

```bash
# Generate secure random secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4.5 Deploy

1. Click "Deploy" in Railway
2. Wait for build to complete (~3-5 minutes)
3. Railway will provide a URL: `https://your-app.up.railway.app`
4. Test health endpoint: `https://your-app.up.railway.app/health`

## Step 5: Deploy Frontend to Vercel

### 5.1 Deploy from GitHub

1. Go to https://vercel.com/new
2. Import your GitHub repository
3. Configure project:
   - Framework Preset: Create React App
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `build`

### 5.2 Configure Environment Variables

Add these in Vercel dashboard:

```bash
REACT_APP_API_URL=https://your-app.up.railway.app
REACT_APP_ENVIRONMENT=production
```

### 5.3 Deploy

1. Click "Deploy"
2. Wait for build (~2-3 minutes)
3. Vercel will provide URL: `https://your-app.vercel.app`

## Step 6: Update CORS Configuration

1. Go back to Railway dashboard
2. Update `CORS_ORIGINS` environment variable:
   ```
   CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
   ```
3. Redeploy backend (Railway will auto-redeploy)

## Step 7: Initialize Database

### 7.1 Run Migration Script

```bash
# From your local machine
cd backend

# Set environment variables
export MONGODB_URI="your_mongodb_uri"
export USE_FREE_TIER=true

# Run migration
uv run python data/migrate_to_mongodb.py
```

### 7.2 Verify Data

```bash
# Check migration status
uv run python check_migration_status.py
```

Expected output:
```
✅ MongoDB connection successful
✅ Found X questions in database
```

## Step 8: Test Deployment

### 8.1 Test Backend

```bash
# Health check
curl https://your-app.up.railway.app/health

# Ready check
curl https://your-app.up.railway.app/ready
```

Expected response:
```json
{
  "status": "ready",
  "environment": "production",
  "dependencies": {
    "database": true,
    "pinecone": false,
    "claude": false
  }
}
```

### 8.2 Test Frontend

1. Open `https://your-app.vercel.app`
2. You should see the RoundZero landing page
3. Try starting a session (requires authentication setup)

## Step 9: Setup Authentication (Optional)

### Option A: Supabase Auth (Recommended)

1. Create Supabase project: https://supabase.com/dashboard
2. Enable Email authentication
3. Get credentials:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
4. Add to both Railway and Vercel

### Option B: Custom JWT

Use the JWT secret you generated earlier. Frontend will need to implement login flow.

## Step 10: Monitoring & Maintenance

### Railway Monitoring

1. Check logs: Railway Dashboard → Deployments → Logs
2. Monitor usage: Railway Dashboard → Usage
3. Free tier limits:
   - 500 execution hours/month
   - $5 credit/month
   - Sleeps after 30 min inactivity

### Vercel Monitoring

1. Check deployments: Vercel Dashboard → Deployments
2. View analytics: Vercel Dashboard → Analytics
3. Free tier limits:
   - Unlimited deployments
   - 100GB bandwidth/month
   - 100 serverless function executions/day

### MongoDB Atlas Monitoring

1. Check metrics: Atlas Dashboard → Metrics
2. Free tier limits:
   - 512MB storage
   - Shared CPU
   - 100 connections

### Upstash Redis Monitoring

1. Check usage: Upstash Console → Database → Metrics
2. Free tier limits:
   - 10K commands/day
   - 256MB storage
   - 100 concurrent connections

## Troubleshooting

### Backend won't start

1. Check Railway logs for errors
2. Verify all environment variables are set
3. Check MongoDB connection string
4. Verify Groq API key is valid

### Frontend can't connect to backend

1. Verify `REACT_APP_API_URL` is correct
2. Check CORS configuration in Railway
3. Test backend health endpoint directly
4. Check browser console for errors

### Database connection fails

1. Verify MongoDB URI is correct
2. Check IP whitelist includes `0.0.0.0/0`
3. Verify database user credentials
4. Test connection locally first

### Redis connection fails

1. Verify Upstash credentials
2. Check free tier limits (10K commands/day)
3. Test with curl:
   ```bash
   curl -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN" \
        $UPSTASH_REDIS_REST_URL/ping
   ```

### Groq API errors

1. Verify API key is valid
2. Check rate limits (free tier: 30 requests/min)
3. Monitor usage at https://console.groq.com

## Cost Optimization

### Railway
- Enable sleep mode (auto-enabled on free tier)
- Monitor execution hours
- Use health checks to prevent unnecessary wake-ups

### Vercel
- Enable edge caching
- Optimize bundle size
- Use static generation where possible

### MongoDB Atlas
- Create indexes for frequently queried fields
- Monitor storage usage
- Archive old sessions

### Upstash Redis
- Set TTL on session data (1 hour default)
- Monitor command usage
- Clean up expired sessions

## Scaling Beyond Free Tier

When you outgrow free tier:

1. **Railway**: Upgrade to Hobby ($5/month) or Pro ($20/month)
2. **Vercel**: Upgrade to Pro ($20/month)
3. **MongoDB**: Upgrade to M10 ($0.08/hour)
4. **Upstash**: Upgrade to Pay-as-you-go ($0.2/100K commands)
5. **Groq**: Contact for enterprise pricing

## Security Checklist

- [ ] JWT secret is strong and random
- [ ] MongoDB user has minimal permissions
- [ ] CORS origins are restricted to your domains
- [ ] Rate limiting is enabled
- [ ] Environment variables are not committed to git
- [ ] HTTPS is enforced (automatic on Railway/Vercel)
- [ ] API keys are rotated regularly

## Next Steps

1. Setup custom domain (optional)
2. Configure monitoring alerts
3. Setup CI/CD pipeline
4. Add error tracking (Sentry)
5. Setup analytics (PostHog, Mixpanel)

## Support

- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- MongoDB: https://www.mongodb.com/support
- Upstash: https://upstash.com/docs

## Useful Commands

```bash
# Check Railway logs
railway logs

# Redeploy Railway
railway up

# Check Vercel logs
vercel logs

# Redeploy Vercel
vercel --prod

# Test backend locally with production env
cd backend
export $(cat .env | xargs)
export USE_FREE_TIER=true
uv run uvicorn main:app --reload

# Test frontend locally with production API
cd frontend
REACT_APP_API_URL=https://your-app.up.railway.app npm start
```
