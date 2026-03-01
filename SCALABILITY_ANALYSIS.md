# RoundZero Scalability Analysis
## Current State vs. README Vision for 100-200 Concurrent Users

**Analysis Date:** February 27, 2026  
**Target:** Support 100-200 concurrent interview sessions with <500ms latency

---

## Executive Summary

### Current Implementation Status: ⚠️ **60% Complete**

**What's Working:**
- ✅ Core interview logic and decision engine
- ✅ MongoDB integration with connection pooling (50 connections)
- ✅ Vision Agents framework integration
- ✅ JWT authentication with Neon Auth
- ✅ Rate limiting with Upstash Redis
- ✅ SSE (Server-Sent Events) for real-time updates

**Critical Gaps for 100-200 Users:**
- ❌ No horizontal scaling (single FastAPI instance)
- ❌ In-memory session storage (not distributed)
- ❌ No load balancer configuration
- ❌ Stream WebRTC not fully integrated (demo mode in frontend)
- ❌ No connection pooling for Neon Postgres
- ❌ No caching layer for questions
- ❌ No monitoring/observability for production

---

## Detailed Component Analysis

### 1. **Backend Architecture** 🔴 CRITICAL BOTTLENECK

#### Current State:
```python
# backend/main.py - Single process FastAPI
app = FastAPI(title="RoundZero AI Backend")
service = get_interviewer_service()  # Singleton, in-memory
```

**Issues:**
- **In-memory session storage**: `self.sessions: dict[str, SessionState] = {}` (line 1177)
- **Single process**: No multi-worker configuration
- **No session persistence**: Server restart = all sessions lost
- **Memory leak risk**: Unbounded session dictionary

#### Required for 100-200 Users:
```python
# Distributed session storage with Redis
import redis.asyncio as redis

class InterviewerService:
    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            max_connections=200,
            decode_responses=False
        )
        # Store sessions in Redis with TTL
        # Use pickle/msgpack for serialization
```

**Action Items:**
1. Replace in-memory dict with Redis for session storage
2. Configure Gunicorn/Uvicorn with 4-8 workers
3. Add session TTL (1 hour) to prevent memory leaks
4. Implement session recovery on worker restart

---

### 2. **Database Layer** 🟡 PARTIALLY READY

#### MongoDB (Questions) ✅ GOOD
```python
# backend/data/mongo_repository.py
self.client = AsyncIOMotorClient(
    connection_uri,
    maxPoolSize=50,      # ✅ Good for 100-200 users
    minPoolSize=10,      # ✅ Maintains warm connections
    serverSelectionTimeoutMS=5000
)
```

**Capacity:** 50 connections can handle ~150-200 concurrent queries (assuming 3-4 queries per session)

#### Neon Postgres (Session Data) ❌ NOT READY
```python
# backend/agent/interviewer.py - Line 1069
async def _get_connection(self):
    return await asyncpg.connect(self.dsn)  # ❌ No pooling!
```

**Issues:**
- Creates new connection per query
- No connection pooling
- Will exhaust Postgres connections at ~20-30 concurrent users

#### Required Fix:
```python
class NeonDatabase:
    def __init__(self):
        self.pool = None
    
    async def init_pool(self):
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=10,
            max_size=50,
            command_timeout=5.0
        )
    
    async def _get_connection(self):
        return await self.pool.acquire()
```

**Action Items:**
1. Implement asyncpg connection pool (10-50 connections)
2. Add connection health checks
3. Configure Neon for 100 max connections
4. Add query timeout (5s) to prevent hanging connections

---

### 3. **Real-Time Communication** 🔴 CRITICAL GAP

#### Stream WebRTC Integration ❌ INCOMPLETE

**Frontend (InterviewScreen.tsx):**
```typescript
// Line 45-60: Stream SDK is imported but not fully wired
const { useParticipants } = useCallStateHooks();
const participants = useParticipants();

// ✅ Call joining logic exists
await call.join({ create: true });

// ❌ But agent voice is using browser speechSynthesis as fallback
speakText(openingLine);  // Line 280
```

**Backend (interviewer.py):**
```python
# Line 150-180: InterviewerAgent has Vision Agents integration
async def join_session_call(self, call_id: str):
    await self.create_user()
    call = await self.create_call(call_type, call_id)
    # ✅ Agent joins call
    # ✅ Listens to transcripts
    # ✅ Processes video frames
```

**Status:** Backend is ready, frontend is in "demo mode"

#### SSE (Server-Sent Events) ✅ IMPLEMENTED
```python
# backend/main.py - Line 145
@app.get("/session/{session_id}/events")
async def session_events(session_id: str):
    async def event_generator():
        queue = asyncio.Queue()
        await service.register_listener(session_id, queue)
        # Broadcasts: transcript, agent_message, vision
```

**Capacity:** SSE can handle 100-200 connections per worker (with proper timeouts)

**Action Items:**
1. Remove speechSynthesis fallback in frontend
2. Wire Stream audio tracks to UI
3. Add connection recovery for dropped SSE connections
4. Configure nginx/load balancer for SSE sticky sessions

---

### 4. **Rate Limiting** ✅ PRODUCTION READY

```python
# backend/rate_limit.py
class RateLimiter:
    def __init__(self, max_calls: int = 8, window_seconds: int = 60):
        self.redis = Redis(url=redis_url, token=redis_token)
        # ✅ Uses Upstash Redis (distributed)
        # ✅ Falls back to local memory if Redis fails
```

**Capacity:** Upstash free tier = 10k commands/day
- 100 users × 8 sessions/day × 10 API calls/session = 8,000 commands/day ✅
- 200 users = 16,000 commands/day ❌ (need paid tier)

**Action Items:**
1. Upgrade Upstash to paid tier for 200 users ($10/month)
2. Add rate limit headers (X-RateLimit-Remaining)
3. Implement exponential backoff on client side

---

### 5. **AI/LLM Layer** 🟡 COST CONCERN

#### Vision Agents (Gemini Realtime) 🔴 COST RISK
```python
# backend/agent/interviewer.py - Line 90
llm = gemini.Realtime(fps=3)  # 3 frames per second
```

**Cost Calculation:**
- Gemini Realtime: ~$0.05/minute (video + audio)
- 100 concurrent users × 30 min/session = 3,000 minutes/hour
- **Cost: $150/hour = $3,600/day** 🔴

**Mitigation:**
1. Reduce FPS to 1 (only for emotion detection)
2. Use Gemini Flash for decision engine (cheaper)
3. Batch video processing (every 5 seconds instead of real-time)
4. Cache emotion states (don't reprocess similar frames)

#### Claude (Decision Engine) ✅ REASONABLE
```python
# backend/agent/interviewer.py - Line 920
self._llm = ClaudeLLM(model="claude-3-5-sonnet-latest")
```

**Cost:** ~$0.015/1k tokens
- 8 questions × 500 tokens/decision = 4k tokens/session
- 100 sessions/hour = 400k tokens = $6/hour ✅

---

### 6. **Caching Strategy** ❌ MISSING

**Current:** No caching layer

**Required for 100-200 Users:**
```python
# Add Redis caching for:
# 1. Question bank queries (1 hour TTL)
# 2. User memory context (5 min TTL)
# 3. LLM responses for common answers (1 day TTL)

class CachedQuestionBank:
    async def fetch_questions(self, role, topics, difficulty, n):
        cache_key = f"questions:{role}:{topics}:{difficulty}:{n}"
        cached = await self.redis.get(cache_key)
        if cached:
            return pickle.loads(cached)
        
        questions = await self._fetch_from_db(...)
        await self.redis.setex(cache_key, 3600, pickle.dumps(questions))
        return questions
```

**Impact:** Reduces MongoDB queries by 80%, saves ~$50/month

---

### 7. **Monitoring & Observability** ❌ MISSING

**Current:** Basic logging only

**Required for Production:**
1. **Metrics** (Prometheus + Grafana):
   - Active sessions count
   - API latency (p50, p95, p99)
   - Database connection pool usage
   - Redis hit rate
   - LLM API costs

2. **Tracing** (OpenTelemetry):
   - Request flow through services
   - Slow query detection
   - Error tracking

3. **Alerting** (PagerDuty/Opsgenie):
   - High error rate (>5%)
   - Database connection exhaustion
   - Memory usage >80%
   - API latency >1s

---

## Infrastructure Requirements

### Current (Development):
```
1 × Railway instance (512MB RAM, 0.5 vCPU)
1 × Vercel frontend
1 × MongoDB Atlas (M0 free tier)
1 × Neon Postgres (free tier)
1 × Upstash Redis (free tier)
```

### Required for 100-200 Users:

#### Backend (Railway/AWS):
```
4 × FastAPI workers (2GB RAM, 1 vCPU each)
1 × Redis instance (1GB RAM) - for sessions + cache
1 × Load balancer (nginx/AWS ALB)
```

#### Database:
```
MongoDB Atlas: M10 tier ($57/month)
- 2GB RAM, 10GB storage
- 100 connections
- Auto-scaling

Neon Postgres: Scale tier ($19/month)
- 4GB RAM
- 100 max connections
- Auto-suspend disabled
```

#### CDN/Edge:
```
Vercel Pro ($20/month)
- Edge functions for auth
- Global CDN
- DDoS protection
```

**Total Infrastructure Cost:** ~$150-200/month

---

## Performance Benchmarks

### Current (Estimated):
- **Concurrent users:** 10-15 (before memory exhaustion)
- **API latency:** 200-500ms (no load)
- **Session creation:** 1-2s (Pinecone + MongoDB + LLM)
- **Database queries:** 50-100ms (MongoDB), 100-200ms (Postgres)

### Target for 100-200 Users:
- **Concurrent users:** 200 (with headroom)
- **API latency:** <500ms (p95)
- **Session creation:** <2s (with caching)
- **Database queries:** <100ms (p95)

---

## Migration Roadmap

### Phase 1: Critical Fixes (Week 1) 🔴
**Goal:** Support 50 concurrent users

1. **Implement Redis session storage**
   - Replace in-memory dict
   - Add session serialization
   - Configure TTL (1 hour)

2. **Add Postgres connection pooling**
   - asyncpg.create_pool()
   - 10-50 connections
   - Health checks

3. **Configure multi-worker deployment**
   - Gunicorn with 4 workers
   - Sticky sessions for SSE
   - Graceful shutdown

**Estimated Effort:** 3-4 days

### Phase 2: Scaling Infrastructure (Week 2) 🟡
**Goal:** Support 100 concurrent users

1. **Upgrade database tiers**
   - MongoDB M10
   - Neon Scale
   - Upstash paid

2. **Add caching layer**
   - Redis for questions
   - LLM response cache
   - User context cache

3. **Implement load balancer**
   - nginx/AWS ALB
   - Health checks
   - SSL termination

**Estimated Effort:** 4-5 days

### Phase 3: Production Readiness (Week 3) 🟢
**Goal:** Support 200 concurrent users + monitoring

1. **Complete Stream WebRTC integration**
   - Remove speechSynthesis fallback
   - Wire audio tracks
   - Connection recovery

2. **Add monitoring stack**
   - Prometheus + Grafana
   - OpenTelemetry tracing
   - Error tracking (Sentry)

3. **Load testing**
   - Locust/k6 tests
   - 200 concurrent sessions
   - Identify bottlenecks

**Estimated Effort:** 5-6 days

### Phase 4: Cost Optimization (Week 4) 🟢
**Goal:** Reduce LLM costs by 50%

1. **Optimize Vision Agents**
   - Reduce FPS to 1
   - Batch processing
   - Frame similarity detection

2. **Implement LLM caching**
   - Cache common responses
   - Use cheaper models for hints
   - Fallback to heuristics

3. **Add usage analytics**
   - Cost per session
   - User behavior tracking
   - A/B testing framework

**Estimated Effort:** 4-5 days

---

## Risk Assessment

### High Risk 🔴
1. **In-memory sessions** - Will crash at 20-30 users
2. **No Postgres pooling** - Connection exhaustion at 30 users
3. **Gemini Realtime costs** - $3,600/day unsustainable

### Medium Risk 🟡
1. **Stream WebRTC incomplete** - Fallback to browser TTS
2. **No caching** - High database load
3. **No monitoring** - Blind to production issues

### Low Risk 🟢
1. **MongoDB capacity** - 50 connections sufficient
2. **Rate limiting** - Upstash handles load
3. **Authentication** - JWT + Neon Auth solid

---

## Conclusion

### Can RoundZero handle 100-200 users today?
**No.** Current implementation will fail at 20-30 concurrent users due to:
1. In-memory session storage
2. No Postgres connection pooling
3. Single-process deployment

### What's needed to get there?
**3-4 weeks of focused work** on:
1. Distributed session storage (Redis)
2. Database connection pooling
3. Multi-worker deployment
4. Cost optimization (Gemini Realtime)
5. Monitoring and observability

### Estimated Total Cost at 200 Users:
- **Infrastructure:** $150-200/month
- **LLM APIs:** $500-1,000/month (with optimization)
- **Total:** $650-1,200/month

### Recommended Next Steps:
1. **Immediate:** Implement Redis session storage (2 days)
2. **Week 1:** Add Postgres pooling + multi-worker (3 days)
3. **Week 2:** Upgrade database tiers + caching (5 days)
4. **Week 3:** Complete WebRTC + monitoring (5 days)
5. **Week 4:** Load test + optimize costs (5 days)

---

**Status:** Ready for hackathon demo (10-15 users), NOT ready for production (100-200 users)
