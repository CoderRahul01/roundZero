# RoundZero 🎯

> **Your AI interviewer. Practice before the real thing.**

RoundZero is a real-time AI mock interview simulator that watches your face, listens to your answers, tracks your confidence, and interrupts you — just like a real interviewer would. Built for students and developers preparing for technical and behavioral interviews at any level.

---

## ✨ What Makes It Different

Most mock interview tools give you a static list of questions and grade your answer after. **RoundZero is dynamic.** It reacts to *how* you're answering, not just *what* you answer.

- 🎙️ **Talks back** — AI interviewer speaks questions aloud and gives real-time verbal feedback
- 👁️ **Watches you** — Detects emotion and confidence from your webcam in real time
- ⚡ **Interrupts** — Cuts in mid-answer when you go off track, just like a real interviewer
- 🧠 **Remembers** — Knows you struggled with recursion last Tuesday and adjusts today's session
- 📊 **Reports** — Post-session breakdown with emotion timeline, filler word count, per-question scores

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **AI Agent** | [Vision Agents](https://visionagents.ai) | Real-time voice + video pipeline |
| **LLM Brain** | Claude (Anthropic) | Interview logic, interruptions, feedback |
| **Question Bank** | Pinecone | Semantic vector search across 5000+ questions |
| **User Memory** | Supermemory AI | Cross-session learning & personalization |
| **Database** | Supabase (Postgres) | Sessions, scores, reports, auth |
| **Video/Audio** | Stream WebRTC | <500ms latency, edge network |
| **STT** | Deepgram | Real-time transcription with turn detection |
| **TTS** | ElevenLabs | Expressive AI voice |
| **Frontend** | React + TypeScript | Setup wizard, live session, report dashboard |
| **Backend** | FastAPI (Python) | API server, agent orchestration |
| **Rate Limiting** | Upstash Redis | Abuse prevention, API cost control |
| **Datasets** | Kaggle | 5000+ real interview questions (SWE, HR, LeetCode) |

---

## 📁 Project Structure

```
roundZero/
├── backend/
│   ├── agent/
│   │   └── interviewer.py        # Vision Agents pipeline — core AI logic
│   ├── data/
│   │   ├── prepare_datasets.py   # Normalize Kaggle datasets
│   │   ├── index_to_pinecone.py  # Embed + push to Pinecone (run once)
│   │   ├── Software Questions.csv
│   │   ├── hr_interview_questions_dataset.json
│   │   └── leetcode_dataset - lc.csv
│   ├── main.py                   # FastAPI server
│   ├── pyproject.toml
│   └── .env
├── frontend/
│   └── src/
│       ├── App.tsx               # Root router
│       ├── theme.ts              # Design tokens
│       ├── components/
│       │   └── UI.tsx            # Shared components
│       └── screens/
│           ├── SetupScreen.tsx   # 3-step setup wizard
│           ├── InterviewScreen.tsx # Live interview UI
│           └── ReportScreen.tsx  # Post-session report
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.12 with CPython
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) package manager
- Accounts on: Supabase, Pinecone, Supermemory, Stream, Anthropic, Deepgram, ElevenLabs

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/roundzero.git
cd roundzero
```

Create `backend/.env`:

```env
# Core
ANTHROPIC_API_KEY=
STREAM_API_KEY=
STREAM_API_SECRET=

# Data
PINECONE_API_KEY=
PINECONE_INDEX=interview-questions
OPENAI_API_KEY=           # only for embeddings (one-time cost)

# Storage
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPERMEMORY_API_KEY=

# Speech
DEEPGRAM_API_KEY=
ELEVENLABS_API_KEY=

# Rate limiting
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```

Create `frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://localhost:8000
REACT_APP_NEON_AUTH_URL=
REACT_APP_ALLOW_LEGACY_DEV_AUTH=false
```

### 2. Set Up Supabase

Run this SQL in your Supabase dashboard → SQL Editor:

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text,
  created_at timestamptz default now()
);

create table sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  role text, topics text[], difficulty text, mode text,
  state text default 'init',
  started_at timestamptz default now(),
  ended_at timestamptz,
  overall_score int, confidence_avg int,
  stream_call_id text
);

create table question_results (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references sessions(id) on delete cascade,
  question_index int, question_text text,
  user_answer text, ideal_answer text,
  score int, emotion_log jsonb,
  filler_count int default 0,
  interruptions int default 0,
  time_taken_sec int
);

alter table sessions        enable row level security;
alter table question_results enable row level security;

create policy "own sessions" on sessions
  for all using (auth.uid() = user_id);

create policy "own results" on question_results
  for all using (
    session_id in (select id from sessions where user_id = auth.uid())
  );
```

### 3. Prepare & Index the Question Bank

```bash
cd backend

# Install dependencies
uv add "vision-agents[getstream,anthropic,deepgram,elevenlabs]" \
  pinecone-client supabase supermemory openai \
  fastapi uvicorn upstash-redis python-dotenv pandas

# Place your Kaggle datasets in backend/data/
# - Software Questions.csv
# - hr_interview_questions_dataset.json
# - leetcode_dataset - lc.csv

# Normalize all datasets into unified schema
python data/prepare_datasets.py

# Embed + push to Pinecone (one-time, ~10 mins for 5000 questions)
python data/index_to_pinecone.py
```

### 4. Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# → { "status": "ok", "pinecone": "connected", "supabase": "connected" }
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm start
# → opens http://localhost:3000
```

---

## 🗺️ How It Works

```
User Browser
  │
  ├─[1] Login → Neon Auth → JWT token
  │
  ├─[2] Setup form → POST /session/start (FastAPI)
  │       ├── Pinecone: semantic query → 12 personalized questions
  │       └── Supermemory: fetch past context (struggles, strengths)
  │
  ├─[3] Join call → Stream WebRTC (audio+video never stored on your server)
  │       ├── Video frames → EmotionProcessor → { emotion, confidence }
  │       ├── Audio chunks → SpeechProcessor  → { fillers, pauses, WPM }
  │       └── Transcript   → Claude           → { action, message }
  │                                                 ↓
  │                                    INTERRUPT / NEXT / HINT / ENCOURAGE
  │
  ├─[4] Per-answer → Supabase question_results (score + emotion log)
  │
  └─[5] Session end → Supermemory updated → Report generated
```

---

## 🔒 Security

| Threat | Mitigation |
|---|---|
| Stolen JWT | Stored in memory only (never localStorage). 1hr expiry + silent refresh. |
| Brute force | Magic link login only — no password to brute force. |
| Cross-user data access | Supabase Row Level Security — enforced at DB level, not app level. |
| Video privacy | Frames are never stored. Only derived labels (emotion: string, confidence: int) written to DB. |
| API key exposure | All secret keys backend-only. Frontend only holds Supabase anon key (safe by design). |
| Prompt injection | User answers injected as XML-tagged data fields, never as raw instructions to Claude. |
| API cost abuse | Upstash Redis rate limiter: 3 sessions/day per user. |

---

## 📊 Kaggle Datasets Used

| Dataset | Source | Questions |
|---|---|---|
| Software Engineering Interview Questions | `syedmharis/software-engineering-interview-questions-dataset` | ~200 |
| HR Interview Questions & Ideal Answers | `aryan208/hr-interview-questions-and-ideal-answers` | ~1000 |
| LeetCode Problems | `gzipchrist/leetcode-problem-dataset` | ~2500 |

All datasets are normalized into a unified schema and embedded with `text-embedding-3-small` before being indexed into Pinecone for semantic retrieval.

---

## 💚 Zero-Cost Infrastructure

| Service | Free Tier | Usage |
|---|---|---|
| Supabase | 500MB DB, 50k MAU | Auth + structured data |
| Pinecone | 100k vectors | Question bank (5k vectors used) |
| Supermemory | Free tier | User memory |
| Stream | 333k participant minutes/mo | WebRTC infrastructure |
| Railway | $5 credit/mo | Backend hosting |
| Vercel | Unlimited | Frontend hosting |
| Upstash Redis | 10k cmds/day | Rate limiting |

**Total launch cost: ~$5–10** (Claude API tokens for testing only)

---

## 🚀 Deployment

### Backend → Railway

```bash
cd backend
railway login
railway init --name roundzero-backend
railway up
# Set all env vars in Railway dashboard
```

### Frontend → Vercel

```bash
cd frontend
vercel --prod
# Set REACT_APP_BACKEND_URL to your Railway URL
```

---

## 🔌 Wiring Up Real Vision Agents

The frontend ships with demo/simulation mode. To connect real Vision Agents:

**1. Replace fake video feed in `InterviewScreen.tsx`:**
```tsx
// Remove <VideoFeed> component and replace with:
import { ParticipantView, useCallStateHooks } from '@stream-io/video-react-sdk';
const { useParticipants } = useCallStateHooks();
```

**2. Replace simulated emotion in `InterviewScreen.tsx`:**
```tsx
// Remove the setInterval simulation
// Add WebSocket listener from your backend that pushes
// { emotion, confidence } from Vision Agents EmotionProcessor
```

**3. Replace mock report in `ReportScreen.tsx`:**
```tsx
useEffect(() => {
  fetch(`${process.env.REACT_APP_BACKEND_URL}/session/${config.sessionId}/report`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then(r => r.json()).then(setReport);
}, []);
```

---

## 🗺️ Roadmap

- [ ] Real Stream WebRTC integration (replace demo mode)
- [ ] FER model fine-tuned on Kaggle facial emotion dataset
- [ ] Company-specific question packs (Google, Amazon, Meta)
- [ ] Pair interview mode (practice with a friend)
- [ ] Mobile app (React Native with Stream SDK)
- [ ] Resume parsing — auto-detect role and topics

---

## 👨‍💻 Built With

- [Vision Agents](https://visionagents.ai) — Real-time voice + video AI pipeline
- [Anthropic Claude](https://anthropic.com) — Interview intelligence
- [Pinecone](https://pinecone.io) — Vector search
- [Supermemory](https://supermemory.ai) — Long-term user memory
- [Supabase](https://supabase.com) — Database + Auth
- [Stream](https://getstream.io) — WebRTC infrastructure

---

## 📄 License

MIT — build on it, fork it, ship it.

---

<p align="center">Built for the Vision Agents Hackathon 2025 · <strong>RoundZero</strong> — Practice before the real thing.</p>
