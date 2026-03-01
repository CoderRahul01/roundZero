# RoundZero - Zero-Cost Architecture for 100-200 Users
## Complete Free Tier Strategy

**Goal:** Support 100-200 concurrent users with $0/month operational cost

---

## Executive Summary

### Total Cost: **$0/month** 🎉

By strategically using free tiers, open-source alternatives, and smart architecture, we can run RoundZero completely free while supporting 100-200 concurrent users.

**Key Strategy:**
1. Replace expensive LLM APIs with local/open-source models
2. Use free tier limits strategically
3. Implement aggressive caching
4. Optimize resource usage
5. Self-host critical components

---

## Free Tier Infrastructure Stack

### 1. **Compute & Hosting** - FREE

#### Backend: Railway Free Tier
```yaml
Resources:
  - 512MB RAM, 0.5 vCPU (per service)
  - $5 credit/month (500 hours)
  - Up to 2 services

Strategy:
  - Deploy 2 FastAPI instances (use full $5 credit)
  - Each handles 50-100 concurrent users
  - Use nginx as reverse proxy (runs in same container)
```

**Alternative: Render.com Free Tier**
```yaml
Resources:
  - 512MB RAM
  - Unlimited services
  - Spins down after 15 min inactivity
  
Strategy:
  - Keep-alive ping every 10 minutes
  - Accept 30s cold start for first user
```

**Alternative: Fly.io Free Tier**
```yaml
Resources:
  - 3 × 256MB VMs (shared-cpu-1x)
  - 160GB bandwidth/month
  
Strategy:
  - 3 workers = better concurrency
  - Auto-scale based on load
```

#### Frontend: Vercel Free Tier ✅
```yaml
Resources:
  - Unlimited bandwidth
  - 100GB bandwidth/month
  - Edge functions
  - Global CDN

Current: Already using ✅
```

---

### 2. **Database Layer** - FREE

#### MongoDB Atlas Free Tier (M0) ✅
```yaml
Resources:
  - 512MB storage
  - Shared cluster
  - 100 connections
  - No credit card required

Capacity:
  - 5,000 questions = ~50MB
  - 10,000 sessions = ~100MB
  - Total: 150MB used / 512MB available ✅

Optimization:
  - Enable compression (saves 40%)
  - TTL indexes (auto-delete old sessions after 7 days)
  - Projection queries (fetch only needed fields)
```

#### Neon Postgres Free Tier ✅
```yaml
Resources:
  - 512MB storage
  - 1 project
  - Auto-suspend after 5 min inactivity
  - 100 hours compute/month

Capacity:
  - 10,000 sessions = ~50MB
  - 80,000 question_results = ~200MB
  - Total: 250MB used / 512MB available ✅

Optimization:
  - Aggressive auto-suspend (save compute hours)
  - Connection pooling (PgBouncer)
  - Archive old data to MongoDB
```

**Alternative: Supabase Free Tier**
```yaml
Resources:
  - 500MB database
  - 2GB bandwidth/month
  - 50,000 monthly active users
  - Pauses after 1 week inactivity

Better for:
  - Built-in auth (no Neon Auth needed)
  - Real-time subscriptions (replace SSE)
  - Row Level Security
```

---

### 3. **Caching & Session Storage** - FREE

#### Upstash Redis Free Tier ✅
```yaml
Resources:
  - 10,000 commands/day
  - 256MB storage
  - Global replication

Current Usage:
  - Rate limiting: 200 users × 10 calls = 2,000 cmds/day ✅
  
New Usage (with sessions):
  - Sessions: 200 users × 1 write = 200 cmds/day
  - Cache hits: 200 users × 20 reads = 4,000 cmds/day
  - Total: 6,200 cmds/day / 10,000 limit ✅

Optimization:
  - Cache questions for 1 hour (reduce MongoDB queries)
  - Store sessions with 1 hour TTL
  - Use Redis Streams for SSE (more efficient)
```

**Alternative: Vercel KV (Redis)**
```yaml
Resources:
  - 256MB storage
  - 30,000 commands/month
  - Edge locations

Better for:
  - Integrated with Vercel
  - Lower latency (edge)
  - More commands (30k vs 10k)
```

---

### 4. **AI/LLM Layer** - FREE (Critical Change!)

#### Replace Expensive APIs with Free Alternatives

##### Current Cost: $3,600/day 🔴
```python
# Gemini Realtime: $0.05/min × 100 users × 30 min = $150/hour
llm = gemini.Realtime(fps=3)
```

##### New Strategy: $0/day ✅

**Option 1: Ollama (Self-Hosted, Best Quality)**
```python
# Run Ollama on Railway/Fly.io
# Models: llama3.2 (3B), phi-3 (3.8B), gemma2 (2B)

from ollama import AsyncClient

class LocalDecisionEngine:
    def __init__(self):
        self.client = AsyncClient(host='http://ollama:11434')
        self.model = 'llama3.2:3b'  # Fast, good quality
    
    async def decide(self, question, answer, confidence, fillers, mode):
        prompt = f"""You are an interview coach. Evaluate this answer:
Question: {question}
Answer: {answer}
Confidence: {confidence}
Fillers: {fillers}

Return JSON: {{"action": "CONTINUE|NEXT|HINT|ENCOURAGE", "message": "...", "score": 0-100}}"""
        
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            options={'temperature': 0.3}
        )
        return self._parse_response(response['response'])

# Deployment:
# - Railway: Add Ollama service (uses $5 credit)
# - Fly.io: Deploy as separate VM (free tier)
# - Response time: 1-2s (acceptable for decision engine)
```

**Option 2: Groq API (Free Tier, Fastest)**
```python
# Groq: 14,400 requests/day FREE
# Models: llama-3.1-8b, mixtral-8x7b

from groq import AsyncGroq

class GroqDecisionEngine:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = 'llama-3.1-8b-instant'
    
    async def decide(self, question, answer, confidence, fillers, mode):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "system",
                "content": "You are an interview coach..."
            }, {
                "role": "user",
                "content": f"Question: {question}\nAnswer: {answer}"
            }],
            temperature=0.3,
            max_tokens=200
        )
        return self._parse_response(response.choices[0].message.content)

# Capacity:
# - 14,400 requests/day / 200 users = 72 requests/user/day
# - 8 questions/session × 3 decisions/question = 24 requests/session ✅
# - Can handle 600 sessions/day FREE
```

**Option 3: Together AI (Free Tier)**
```yaml
Free Tier:
  - $25 credit (lasts ~1 month)
  - llama-3.1-8b: $0.18/1M tokens
  - 138M tokens FREE

Capacity:
  - 200 users × 8 questions × 500 tokens = 800k tokens/day
  - 138M / 800k = 172 days of usage ✅
```

**Recommendation: Groq API** (fastest, truly free, no credit card)

---

### 5. **Voice & Video** - FREE

#### Replace Expensive Vision Agents Components

##### Current Cost: $3,600/day 🔴
```python
# Gemini Realtime: Video + Audio processing
llm = gemini.Realtime(fps=3)
```

##### New Strategy: $0/day ✅

**Speech-to-Text: Groq Whisper API (FREE)**
```python
# Groq Whisper: Included in 14,400 requests/day

class FreeSTTService:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
    
    async def transcribe(self, audio_chunk: bytes):
        response = await self.client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_chunk,
            language="en"
        )
        return response.text

# Alternative: Browser Web Speech API (already implemented!)
# - Free, runs in browser
# - No server cost
# - Already in InterviewScreen.tsx ✅
```

**Text-to-Speech: Browser API (FREE)**
```typescript
// Already implemented in InterviewScreen.tsx!
const utterance = new SpeechSynthesisUtterance(text);
window.speechSynthesis.speak(utterance);

// Pros:
// - Free, no API calls
// - Low latency
// - Works offline
// - Already working ✅

// Cons:
// - Robotic voice (acceptable for MVP)
```

**Alternative TTS: Coqui TTS (Self-Hosted)**
```python
# Run Coqui TTS on Railway/Fly.io
# Open-source, high quality voices

from TTS.api import TTS

class FreeTTSService:
    def __init__(self):
        self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
    
    async def synthesize(self, text: str) -> bytes:
        # Generate audio
        audio = await asyncio.to_thread(
            self.tts.tts,
            text=text
        )
        return audio

# Deployment:
# - Railway: Add TTS service (uses $5 credit)
# - Response time: 2-3s (acceptable)
```

**Video Emotion Detection: MediaPipe (FREE)**
```python
# Replace Gemini Vision with MediaPipe Face Mesh
# Runs in browser or backend

import mediapipe as mp

class FreeEmotionDetector:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
    
    def detect_emotion(self, frame: np.ndarray) -> dict:
        results = self.face_mesh.process(frame)
        if not results.multi_face_landmarks:
            return {"emotion": "neutral", "confidence": 50}
        
        # Analyze facial landmarks
        landmarks = results.multi_face_landmarks[0]
        
        # Simple heuristics:
        # - Mouth corners up = confident
        # - Eyebrows raised = confused
        # - Eyes wide = nervous
        
        emotion = self._analyze_landmarks(landmarks)
        confidence = self._calculate_confidence(landmarks)
        
        return {"emotion": emotion, "confidence": confidence}

# Deployment:
# - Run in browser (WebAssembly)
# - Or backend (lightweight, <100MB RAM)
```

**WebRTC: Stream.io Free Tier ✅**
```yaml
Resources:
  - 333,000 participant minutes/month
  - Unlimited channels
  - Edge network

Capacity:
  - 200 users × 30 min/session = 6,000 minutes/day
  - 6,000 × 30 days = 180,000 minutes/month
  - 180k / 333k = 54% usage ✅

Current: Already using ✅
```

---

### 6. **Vector Search** - FREE

#### Replace Pinecone with Free Alternatives

##### Current: Pinecone Free Tier ✅
```yaml
Resources:
  - 100,000 vectors
  - 1 index
  - 1 pod

Capacity:
  - 5,000 questions ✅
  - But: Limited to 1 index (can't separate by user)
```

##### Better Option: Qdrant Cloud Free Tier
```yaml
Resources:
  - 1GB storage
  - Unlimited vectors
  - Multiple collections
  - No credit card required

Capacity:
  - 50,000 questions with metadata
  - User-specific collections
  - Better filtering

Migration:
# Replace Pinecone client with Qdrant
from qdrant_client import AsyncQdrantClient

class FreeVectorStore:
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY')
        )
    
    async def search(self, query_vector, limit=10):
        results = await self.client.search(
            collection_name="questions",
            query_vector=query_vector,
            limit=limit
        )
        return results
```

**Alternative: Weaviate Cloud Free Tier**
```yaml
Resources:
  - 1 cluster
  - 10GB storage
  - Unlimited queries

Better for:
  - Hybrid search (vector + keyword)
  - GraphQL API
  - Built-in vectorization
```

**Alternative: Self-Hosted Qdrant**
```yaml
Deploy on Railway/Fly.io:
  - Docker image: qdrant/qdrant
  - Memory: 256MB (sufficient for 5k vectors)
  - Storage: Use Railway volume (free)

Pros:
  - No limits
  - Full control
  - Persistent storage
```

---

### 7. **Embeddings** - FREE

#### Replace OpenAI Embeddings

##### Current Cost: $0.13/1M tokens (one-time)
```python
# OpenAI text-embedding-3-small
# 5,000 questions × 100 tokens = 500k tokens = $0.065
```

##### Free Alternatives:

**Option 1: Sentence Transformers (Self-Hosted)**
```python
from sentence_transformers import SentenceTransformer

class FreeEmbeddings:
    def __init__(self):
        # all-MiniLM-L6-v2: 384 dims, fast, good quality
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

# Deployment:
# - Run on Railway (uses $5 credit)
# - Or run once locally, store in Qdrant
# - Model size: 80MB (fits in 512MB RAM)
```

**Option 2: Cohere Free Tier**
```yaml
Free Tier:
  - 100 API calls/minute
  - Unlimited usage
  - embed-english-light-v3.0 (384 dims)

Capacity:
  - 5,000 questions / 100 per min = 50 minutes (one-time)
  - Then: Cache embeddings in Qdrant ✅
```

**Option 3: Voyage AI Free Tier**
```yaml
Free Tier:
  - $25 credit
  - voyage-lite-02: $0.10/1M tokens
  - 250M tokens FREE

Capacity:
  - 5,000 questions = 500k tokens = $0.05
  - $25 / $0.05 = 500 re-indexings ✅
```

**Recommendation: Sentence Transformers** (truly free, no API limits)

---

## Complete Free Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER BROWSER                              │
│  - React Frontend (Vercel Free)                             │
│  - Web Speech API (STT - Free)                              │
│  - Speech Synthesis API (TTS - Free)                        │
│  - MediaPipe (Emotion Detection - Free)                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ HTTPS
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              LOAD BALANCER (nginx in Railway)                │
│  - Round-robin to 2 FastAPI instances                       │
│  - Sticky sessions for SSE                                  │
└─────────────────┬───────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌──────────────┐    ┌──────────────┐
│  FastAPI #1  │    │  FastAPI #2  │
│  Railway     │    │  Railway     │
│  512MB RAM   │    │  512MB RAM   │
└──────┬───────┘    └──────┬───────┘
       │                   │
       └─────────┬─────────┘
                 │
    ┌────────────┼────────────┬──────────────┐
    ▼            ▼            ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│ MongoDB │ │  Neon   │ │ Upstash  │ │  Qdrant  │
│ Atlas   │ │Postgres │ │  Redis   │ │  Cloud   │
│ M0 Free │ │  Free   │ │   Free   │ │   Free   │
└─────────┘ └─────────┘ └──────────┘ └──────────┘
                 │
                 ▼
         ┌──────────────┐
         │  Groq API    │
         │  (LLM Free)  │
         └──────────────┘
```

---

## Implementation Changes

### 1. Replace Gemini with Groq

```python
# backend/agent/interviewer.py

# OLD (Expensive):
from vision_agents.plugins import gemini
llm = gemini.Realtime(fps=3)  # $3,600/day

# NEW (Free):
from groq import AsyncGroq

class FreeInterviewerAgent:
    def __init__(self, session_id: str, config: SessionConfig, service: InterviewerService):
        self.groq = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = 'llama-3.1-8b-instant'
        # ... rest of init
    
    async def process_answer(self, transcript: str):
        # Use Groq for decision making
        response = await self.groq.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "system",
                "content": self.system_prompt
            }, {
                "role": "user",
                "content": f"Evaluate: {transcript}"
            }],
            temperature=0.3,
            max_tokens=200
        )
        return self._parse_decision(response)
```

### 2. Use Browser APIs for Voice

```typescript
// frontend/src/screens/InterviewScreen.tsx

// Already implemented! Just remove Gemini fallback
// STT: Web Speech API ✅
const recognition = new (window as any).webkitSpeechRecognition();

// TTS: Speech Synthesis API ✅
const utterance = new SpeechSynthesisUtterance(text);
window.speechSynthesis.speak(utterance);

// Emotion: Add MediaPipe
import { FaceMesh } from '@mediapipe/face_mesh';

const faceMesh = new FaceMesh({
  locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
});

faceMesh.onResults((results) => {
  const emotion = analyzeEmotion(results.multiFaceLandmarks[0]);
  setEmotion(emotion);
});
```

### 3. Replace Pinecone with Qdrant

```python
# backend/agent/interviewer.py

# OLD:
from pinecone import Pinecone
pc = Pinecone(api_key=pinecone_key)
index = pc.Index(index_name)

# NEW:
from qdrant_client import AsyncQdrantClient

class FreeQuestionBank:
    def __init__(self):
        self.qdrant = AsyncQdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY')
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def search_questions(self, query: str, limit: int = 10):
        # Embed query
        query_vector = self.embedder.encode(query).tolist()
        
        # Search Qdrant
        results = await self.qdrant.search(
            collection_name="questions",
            query_vector=query_vector,
            limit=limit
        )
        
        return [self._to_question(hit) for hit in results]
```

### 4. Add Redis Session Storage

```python
# backend/agent/interviewer.py

import redis.asyncio as redis
import pickle

class InterviewerService:
    def __init__(self):
        self.redis = redis.from_url(
            os.getenv('UPSTASH_REDIS_URL'),
            decode_responses=False
        )
        # Remove: self.sessions = {}  # In-memory dict
    
    async def get_session(self, session_id: str) -> SessionState:
        # Get from Redis
        data = await self.redis.get(f"session:{session_id}")
        if not data:
            raise KeyError("Session not found")
        return pickle.loads(data)
    
    async def save_session(self, session: SessionState):
        # Save to Redis with 1 hour TTL
        await self.redis.setex(
            f"session:{session.id}",
            3600,  # 1 hour
            pickle.dumps(session)
        )
```

### 5. Add Aggressive Caching

```python
# backend/agent/interviewer.py

class CachedQuestionBank:
    async def fetch_questions(self, role, topics, difficulty, n):
        # Check cache first
        cache_key = f"questions:{role}:{':'.join(topics)}:{difficulty}:{n}"
        cached = await self.redis.get(cache_key)
        
        if cached:
            return pickle.loads(cached)
        
        # Fetch from DB
        questions = await self._fetch_from_db(role, topics, difficulty, n)
        
        # Cache for 1 hour
        await self.redis.setex(cache_key, 3600, pickle.dumps(questions))
        
        return questions
```

---

## Free Tier Limits & Monitoring

### Daily Limits

```python
# backend/monitoring.py

FREE_TIER_LIMITS = {
    'groq_requests': 14_400,      # Groq API
    'redis_commands': 10_000,      # Upstash Redis
    'mongodb_queries': 100_000,    # MongoDB Atlas (soft limit)
    'postgres_hours': 100,         # Neon compute hours/month
    'stream_minutes': 333_000,     # Stream.io/month
}

class FreeTierMonitor:
    async def check_limits(self):
        usage = {
            'groq': await self.get_groq_usage(),
            'redis': await self.get_redis_usage(),
            'mongodb': await self.get_mongodb_usage(),
        }
        
        for service, limit in FREE_TIER_LIMITS.items():
            if usage.get(service, 0) > limit * 0.8:
                logger.warning(f"{service} at 80% of free tier limit")
        
        return usage
```

### Auto-Scaling Strategy

```python
# Scale down when approaching limits

class AdaptiveRateLimiter:
    async def allow_request(self, user_id: str) -> bool:
        # Check free tier usage
        usage = await self.monitor.check_limits()
        
        # If Groq at 90%, reduce to 6 questions/session
        if usage['groq'] > FREE_TIER_LIMITS['groq'] * 0.9:
            return await self.rate_limit(user_id, max_questions=6)
        
        # Normal: 8 questions/session
        return await self.rate_limit(user_id, max_questions=8)
```

---

## Migration Checklist

### Phase 1: Replace Expensive APIs (Day 1-2)
- [ ] Sign up for Groq API (free, no credit card)
- [ ] Replace Gemini Realtime with Groq LLM
- [ ] Test decision engine with Groq
- [ ] Remove Vision Agents dependencies (optional)
- [ ] Keep browser Speech APIs (already free)

### Phase 2: Add Redis Sessions (Day 3)
- [ ] Update InterviewerService to use Redis
- [ ] Add session serialization (pickle)
- [ ] Set TTL to 1 hour
- [ ] Test session persistence

### Phase 3: Replace Pinecone (Day 4-5)
- [ ] Sign up for Qdrant Cloud (free)
- [ ] Install sentence-transformers
- [ ] Generate embeddings locally
- [ ] Upload to Qdrant
- [ ] Update search logic

### Phase 4: Add Caching (Day 6)
- [ ] Cache questions in Redis
- [ ] Cache LLM responses
- [ ] Cache user context
- [ ] Monitor cache hit rate

### Phase 5: Deploy & Test (Day 7)
- [ ] Deploy to Railway (2 instances)
- [ ] Configure nginx load balancer
- [ ] Load test with 100 concurrent users
- [ ] Monitor free tier usage

---

## Expected Performance

### With Free Tier Architecture:

**Capacity:**
- **Concurrent users:** 100-150 (with 2 Railway instances)
- **Sessions/day:** 600 (Groq limit)
- **API latency:** 500-800ms (Groq is fast)
- **Session creation:** 2-3s (local embeddings)

**Limitations:**
- Groq: 14,400 requests/day = 600 sessions/day (24 requests/session)
- Redis: 10,000 commands/day (need caching to stay under)
- Railway: $5 credit = 500 hours/month (2 instances × 250 hours)

**Solutions:**
- Implement daily session cap (600/day = 25/hour)
- Show "peak hours" message when limit reached
- Queue users during high traffic
- Offer "premium" tier for unlimited (paid)

---

## Cost Comparison

### Before (Paid):
```
Infrastructure:     $150/month
LLM APIs:          $500/month
Total:             $650/month
```

### After (Free):
```
Infrastructure:     $0/month
LLM APIs:          $0/month
Total:             $0/month ✅
```

**Savings: $650/month = $7,800/year**

---

## Conclusion

### Is it possible to run RoundZero completely free?

**Yes!** With these changes:

1. **Replace Gemini Realtime** → Groq API (free)
2. **Keep browser Speech APIs** → Already free ✅
3. **Replace Pinecone** → Qdrant Cloud (free)
4. **Add Redis sessions** → Upstash (free tier)
5. **Deploy on Railway** → $5 credit (free)

### Trade-offs:

**Pros:**
- $0/month operational cost
- 100-150 concurrent users
- 600 sessions/day capacity
- Good quality (Llama 3.1 8B)

**Cons:**
- Daily session limit (600)
- Slightly higher latency (500-800ms vs 200-500ms)
- Robotic TTS voice (browser API)
- Need to monitor free tier limits

### Recommended Next Steps:

1. **Immediate:** Sign up for Groq API (5 minutes)
2. **Day 1-2:** Replace Gemini with Groq (4 hours)
3. **Day 3:** Add Redis sessions (4 hours)
4. **Day 4-5:** Replace Pinecone with Qdrant (8 hours)
5. **Day 6:** Add caching layer (4 hours)
6. **Day 7:** Deploy and load test (4 hours)

**Total effort:** 1 week, $0 cost

---

**Status:** Achievable in 1 week with zero operational cost! 🎉
