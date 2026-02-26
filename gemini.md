# roundZero — AI Interview Coach (Vision Agents Hackathon)

> Real-time AI mock interviewer with video/audio analysis, RAG question bank, and persistent memory.

---

## 1. Project Overview

**roundZero** is a mock interview coaching platform powered by the **Vision Agents** framework. The agent watches the candidate via webcam, listens to speech, dynamically selects interview questions from a semantic vector store, and uses an AI model (Claude) to decide in real-time whether to continue listening, interrupt, hint, or encourage.

### What the product does

- Live video + audio session via Stream's WebRTC edge
- Real-time emotion & confidence detection from face frames (`EmotionProcessor`)
- Filler-word and speech-rate detection from transcripts (`SpeechProcessor`)
- Semantic question selection from a Pinecone vector store (seeded from Kaggle/LeetCode/SWE datasets)
- Claude AI acts as the "brain" — decides `CONTINUE | INTERRUPT | NEXT | HINT | ENCOURAGE`
- Persistent cross-session memory via Supermemory AI (knows your past weaknesses)
- Session data (scores, emotion logs, filler counts) saved to Neon (PostgreSQL)
- Post-session report dashboard

---

## 2. Architecture (3 Layers)

```
USER FRONTEND (React + Stream WebRTC SDK)
  └── Start Session → Setup Form → Live Session UI → WebRTC Client → Report Dashboard

BACKEND FASTAPI (main.py)
  └── JWT Middleware → Session Manager → Question Engine → Rate Limiter → Report Generator

AI LAYER (vision_agents framework)
  └── Vision Agents ──► EmotionProcessor (FER)
                    ──► SpeechProcessor (Whisper/transcript)
                    ──► Claude Decision Engine → INTERRUPT | NEXT | HINT | ENCOURAGE

DATA LAYER
  └── Kaggle Datasets → Embedding Pipeline → Pinecone (Question Vector Store)
                                          → Neon Auth (User Accounts, Session History, Scores)
                                          → Supermemory AI (User Memory / cross-session context)
```

### Key Data Flows

| Flow              | Description                                                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Kaggle → Pinecone | CSVs (SWE, HR, LeetCode) normalized → OpenAI embeddings → Pinecone `interview-questions` index                                            |
| Session Start     | React → `POST /session/start` → fetch questions (Pinecone) + user memory (Supermemory) → create Neon session row                          |
| Live Session      | WebRTC frames → `EmotionProcessor.process(frame)` → confidence score; audio → `SpeechProcessor.process(audio, transcript)` → filler count |
| Claude Decision   | Per-utterance: build `decision_prompt` with question + answer buffer + emotion + fillers → Claude → JSON `{action, message}`              |
| Session End       | All `question_results` → avg score → save to Supermemory → update Neon session → speak report                                             |

---

## 3. Tech Stack

| Layer             | Technology                                                               |
| ----------------- | ------------------------------------------------------------------------ |
| Agent Framework   | `vision-agents` (PyPI) — `Agent`, `AudioProcessor`, `VideoProcessor`     |
| LLM (Decision)    | Anthropic Claude (via `self.claude(prompt)`)                             |
| Embeddings        | OpenAI `text-embedding-3-small`                                          |
| Vector Store      | Pinecone — index `interview-questions` (dim 1536, cosine, AWS us-east-1) |
| User Memory       | Supermemory AI                                                           |
| Database          | Neon (Postgres + Managed Auth)                                           |
| WebRTC Transport  | Stream.io (GetStream)                                                    |
| Backend Framework | FastAPI (Python 3.13)                                                    |
| Frontend          | React 19 + TypeScript + `@stream-io/video-react-sdk`                     |
| Package Manager   | `uv` (Python), `npm` (frontend)                                          |

---

## 4. File Map

```
roundZero/
├── .env                          # All API keys (see §6)
├── SKILL.md                      # Vision Agents framework skill reference
├── Architecture_Design.png       # High-level component diagram
├── System_Design.png             # Full 4-layer system flow diagram
├── Software Questions.csv        # Raw SWE interview questions dataset
├── leetcode_dataset - lc.csv     # LeetCode questions dataset
├── hr_interview_questions_dataset.json  # HR questions dataset
│
├── backend/
│   ├── main.py                   # FastAPI app — /session/start, /session/{id}/report
│   ├── pyproject.toml            # Python deps (vision-agents[deepgram,elevenlabs,gemini,getstream])
│   ├── agent/
│   │   └── interviewer.py        # CORE: InterviewerAgent, EmotionProcessor, SpeechProcessor
│   └── data/
│       ├── prepare_datasets.py   # Normalize CSVs → questions_normalized.json
│       └── index_to_pinecone.py  # Batch embed + upsert to Pinecone
│
└── frontend/
    ├── package.json              # React 19 + @stream-io/video-react-sdk + axios + @neon/auth-react
    └── src/
        ├── App.tsx               # Root component (boilerplate — needs implementation)
        └── index.tsx             # Entry point
```

---

## 5. Core Agent Logic (`backend/agent/interviewer.py`)

### `InterviewerAgent` lifecycle

1. **`on_session_start()`** — fetch 12 relevant questions from Pinecone, get user memory from Supermemory, create Supabase session row, build system prompt with role/tone/past context, ask first question.
2. **`on_user_speech(transcript, audio_chunk)`** — accumulate answer buffer, get latest emotion + speech state, call `self.claude(decision_prompt)` → parse JSON action:
   - `CONTINUE` → do nothing (user still talking)
   - `INTERRUPT` → speak clarifying question
   - `NEXT` → speak feedback, save `question_results` row, advance question index
   - `HINT` / `ENCOURAGE` → speak supportive message
3. **`end_session()`** → aggregate scores, save memory to Supermemory, update Supabase session, speak summary.

### `EmotionProcessor(VideoProcessor)`

- `process(frame)` → calls `analyze_emotion(frame)` (TODO: wire in FER model) + `estimate_confidence(emotion)`
- Confidence mapping: `happy=80, neutral=65, confused=40, fear=30, sad=35, surprise=60`

### `SpeechProcessor(AudioProcessor)`

- `process(audio_chunk, transcript)` → count filler words (`um, uh, like, you know, basically, literally`)
- Returns `{filler_words, total_fillers}`

### `fetch_questions(role, topics, difficulty, n=12)`

- Builds query string → OpenAI embedding → Pinecone `query()` with difficulty filter → returns metadata list

---

## 6. Environment Variables (`.env`)

| Variable               | Service        | Purpose                            |
| ---------------------- | -------------- | ---------------------------------- |
| `ANTHROPIC_API_KEY`    | Anthropic      | Claude decision engine             |
| `PINECONE_API_KEY`     | Pinecone       | Question vector store              |
| `PINECONE_INDEX`       | Pinecone       | Index name (`interview-questions`) |
| `DATABASE_URL`         | Neon           | Postgres connection string (Neon)  |
| `NEON_AUTH_PROJECT_ID` | Neon Auth      | Auth project identifier            |
| `SUPERMEMORY_API_KEY`  | Supermemory AI | User cross-session memory          |
| `STREAM_API_KEY`       | GetStream      | WebRTC edge transport              |
| `STREAM_API_SECRET`    | GetStream      | WebRTC auth secret                 |

> **Note:** `OPENAI_API_KEY` is also needed for embeddings but is not yet in `.env`. The `openai_client = OpenAI()` in `interviewer.py` will auto-read `OPENAI_API_KEY` from environment.

---

## 7. Neon Schema (Expected)

```sql
-- sessions table
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  role TEXT,
  topics TEXT[],
  difficulty TEXT,
  mode TEXT DEFAULT 'buddy',
  overall_score INT,
  confidence_avg INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  ended_at TIMESTAMPTZ
);

-- question_results table
CREATE TABLE question_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id),
  question_text TEXT,
  user_answer TEXT,
  ideal_answer TEXT,
  score INT,
  emotion_log JSONB,
  filler_word_count INT
);
```

---

## 8. Running Locally

### Step 1: Backend

```bash
cd backend
cp ../.env .env  # env already at root
uv run main.py   # or: uvicorn main:app --reload --port 8000
```

Run in Vision Agents console mode (single agent test):

```bash
uv run main.py run
```

Run as HTTP server (multi-session):

```bash
uv run main.py serve --host 0.0.0.0 --port 8000
```

### Step 2: Data Pipeline (run once)

```bash
cd backend/data
python prepare_datasets.py    # → questions_normalized.json
python index_to_pinecone.py   # → upsert to Pinecone
```

### Step 3: Frontend

```bash
cd frontend
npm install
npm start  # → http://localhost:3000
```

---

## 9. API Endpoints

| Method | Path                           | Description                                                               |
| ------ | ------------------------------ | ------------------------------------------------------------------------- |
| `POST` | `/session/start`               | Create agent session. Body: `{user_id, role, topics[], difficulty, mode}` |
| `GET`  | `/session/{session_id}/report` | Fetch session report from Neon                                            |
| `GET`  | `/health`                      | Vision Agents liveness check (server mode)                                |
| `GET`  | `/ready`                       | Vision Agents readiness check (server mode)                               |
| `GET`  | `/sessions/{id}/metrics`       | Performance metrics (server mode)                                         |

### Session Start Request

```json
{
  "user_id": "user_abc123",
  "role": "Software Engineer",
  "topics": ["system design", "algorithms"],
  "difficulty": "medium",
  "mode": "buddy"
}
```

---

## 10. What's NOT Yet Implemented (TODO)

| Item                       | Location                             | Notes                                                                            |
| -------------------------- | ------------------------------------ | -------------------------------------------------------------------------------- |
| FER emotion model          | `EmotionProcessor.analyze_emotion()` | Wire in actual FER2013-trained model                                             |
| JWT auth middleware        | `backend/main.py`                    | JWT Middleware shown in System_Design                                            |
| React frontend             | `frontend/src/App.tsx`               | Setup Form, Live Session UI, WebRTC Client, Report Dashboard                     |
| Rate limiter               | Backend                              | Shown in System_Design, not coded                                                |
| Report generator           | Backend                              | `GET /session/{id}/report` returns `...` (not implemented)                       |
| `OPENAI_API_KEY` in `.env` | `.env`                               | Needed for embeddings in both `interviewer.py` and data scripts                  |
| `visionagents` import fix  | `interviewer.py`                     | Imported as `visionagents` but package is `vision_agents` — check correct import |

---

## 11. Key Gotchas & Notes

- **Import discrepancy**: `interviewer.py` imports `from visionagents import Agent, AudioProcessor, VideoProcessor` but `pyproject.toml` installs `vision-agents`. Correct import is likely `from vision_agents.core import Agent` and processors differ — verify with `uv run python -c "import vision_agents; print(dir(vision_agents))"`.
- **Claude vs Gemini**: The system prompt and `self.claude()` calls use Anthropic Claude, but `pyproject.toml` installs `vision-agents[gemini]`. The `.env` has `ANTHROPIC_API_KEY`. Clarify the LLM strategy — if using Gemini as the LLM plugin, update `InterviewerAgent` constructor.
- **Async patterns**: All `@agent.events.subscribe` handlers MUST be `async def`. `supabase` client calls in `interviewer.py` are currently synchronous — consider wrapping in `asyncio.to_thread()` for production.
- **Session affinity**: Multiple server replicas require sticky sessions (agents are stateful per session).
- **Data files location**: `prepare_datasets.py` reads `swe_questions.csv`, `hr_questions.csv`, `leetcode.csv` from CWD. Actual files in root are `Software Questions.csv` and `leetcode_dataset - lc.csv` — filenames must match or be updated.

---

## 12. Interview Modes

| Mode     | Tone                   | Use Case                               |
| -------- | ---------------------- | -------------------------------------- |
| `buddy`  | Friendly but thorough  | Default — supportive coaching          |
| `strict` | Formal and challenging | Simulates real high-pressure interview |

---

## 13. Vision Agents Framework Quick Reference

Install plugins:

```bash
uv add "vision-agents[gemini,deepgram,elevenlabs,getstream]"
```

Agent skeleton:

```python
from vision_agents.core import Agent, AgentLauncher, Runner, User
from vision_agents.plugins import gemini, deepgram, elevenlabs, getstream

async def create_agent(**kwargs) -> Agent:
    return Agent(
        edge=getstream.Edge(),
        agent_user=User(name="Interviewer", id="agent"),
        instructions="...",
        llm=gemini.LLM("gemini-2.5-flash"),
        stt=deepgram.STT(),
        tts=elevenlabs.TTS(),
    )
```

CLI:

```bash
uv run main.py run     # console dev mode
uv run main.py serve   # HTTP production mode
```

Full framework docs: https://visionagents.ai/llms.txt
