from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()
from settings import Settings, get_settings
settings = get_settings()
logger = logging.getLogger("roundzero.agent")

Action = Literal["CONTINUE", "NEXT", "HINT", "ENCOURAGE"]

try:
    from google import genai
except ImportError:
    genai = None

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

try:
    from supermemory import Supermemory
except ImportError:
    Supermemory = None

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    from vision_agents.core import Agent, User
    from vision_agents.plugins import gemini, deepgram, elevenlabs, getstream
    from vision_agents.plugins.anthropic import LLM as ClaudeLLM
    from vision_agents.core.llm.events import VLMInferenceCompletedEvent
    # No longer needed for Realtime mode as it's speech-to-speech
    # from vision_agents.core.stt.events import STTTranscriptEvent 
except ImportError as e:
    print(f"[WARN] Vision Agents import error: {e}")
    Agent = None
    User = None
    gemini = None
    deepgram = None
    elevenlabs = None
    getstream = None
    ClaudeLLM = None
    VLMInferenceCompletedEvent = None

# Fallback base class to avoid import-time crashes when vision_agents isn't installed.
if Agent is None:  # pragma: no cover - optional dependency path
    class Agent:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise RuntimeError("vision-agents is not installed; set USE_VISION=false or install the package.")


class InterviewerAgent(Agent):
    """
    Real-time AI Interviewer using the Vision Agents framework.
    Orchestrates STT, TTS, LLM, and Video processing.
    """
    def __init__(self, session_id: str, config: SessionConfig, service: InterviewerService):
        missing = []
        if Agent is None: missing.append("Agent")
        if User is None: missing.append("User")
        if gemini is None: missing.append("gemini")
        if deepgram is None: missing.append("deepgram")
        if elevenlabs is None: missing.append("elevenlabs")
        if getstream is None: missing.append("getstream")
        
        if missing:
            raise RuntimeError(f"Vision Agents dependencies are missing ({', '.join(missing)}); install vision-agents extras.")
        self.session_id = session_id
        self.session_config = config
        self.service = service
        self.last_vid_stats = {"emotion": "neutral", "confidence": 65}
        self.last_transcript_time = time.time()
        self.is_speaking = False

        # Initialize framework components
        # Use Gemini Realtime for low-latency speech-to-speech
        llm = gemini.Realtime()

        # Vision Processor
        self.emotion_processor = VisionEmotionProcessor()

        super().__init__(
            edge=getstream.Edge(),
            agent_user=User(name="Interviewer", id="agent"),
            instructions=service.decision_engine.system_prompt,
            llm=llm,
            stt=deepgram.STT(),
            tts=elevenlabs.TTS(),
            processors=[self.emotion_processor]
        )
        self.is_processing_decision = False

        # Register agent with the session state for cross-module access
        session = self.service.sessions.get(self.session_id)
        if session:
            session.agent = self

        @self.events.subscribe
        async def on_transcript(event: Any):
            """Listen to transcripts to update state and broadcast to UI."""
            # vision-agents events often have 'text' and 'participant_id' or 'response'
            # We normalize to handle both speech-to-speech and custom STT events
            text = getattr(event, "text", "")
            if not text:
                return

            # Check if it's the agent speaking
            if getattr(event, "participant_id", None) == self.agent_user.id:
                self.is_speaking = True
                await self.service.broadcast(self.session_id, {
                    "type": "agent_transcript",
                    "text": text
                })
                return
            
            self.last_transcript_time = time.time()
            self.is_speaking = False
            
            session = self.service.sessions.get(self.session_id)
            if not session:
                return

            # Accumulate transcript into session buffer
            session.answer_buffer += f" {text}"
            
            # Broadcast user's transcript to frontend
            await self.service.broadcast(self.session_id, {
                "type": "transcript",
                "text": text,
                "is_final": True
            })

            # Real-time filler analysis
            fillers = self.service.speech.analyze(text)
            session.total_fillers += fillers

        @self.events.subscribe
        async def on_vision_result(event: VLMInferenceCompletedEvent):
            """Update local video stats when processor emits results."""
            # VLM events use plugin_name to identify the source
            if event.plugin_name == self.emotion_processor.name:
                # For VLM inference, the result is in the text field
                # In this mock, we'd need to parse it or have it pre-formatted
                # For now, let's just log it
                logger.info(f"👁️ Vision analysis: {event.text}")
                # Update last_vid_stats and broadcast
                # In a real scenario, we'd parse event.text
                await self.service.broadcast(self.session_id, {
                    "type": "vision",
                    "stats": self.last_vid_stats
                })

    async def simple_response(self, text: str, participant: Any = None) -> None:
        """Override simple_response to broadcast agent messages."""
        # Detect if this is a new question being asked by looking for typical patterns
        is_question = "?" in text or "Next question" in text or "Question" in text
        
        # Broadcast the intent/message before or as it's spoken
        event_data = {
            "type": "agent_message",
            "text": text,
            "is_question": is_question
        }
        
        # If it's a question, try to find the index if possible
        session = self.service.sessions.get(self.session_id)
        if session and is_question:
            event_data["question_index"] = session.current_q_idx

        await self.service.broadcast(self.session_id, event_data)
        
        # Use say() to speak the text using the agent's TTS
        await self.say(text)
        self.is_speaking = False # Reset flag after speaking

    async def join_session_call(self, call_id: str, call_type: str = "default"):
        """Join the Stream call as an agent participant."""
        try:
            # 1. Create agent user if not exists (required for server-side auth)
            await self.create_user()

            # 2. Create the call - this will get or create it on Stream
            call = await self.create_call(call_type, call_id)
            # We run this in a background task so it doesn't block the caller
            asyncio.create_task(self._run_agent_loop(call))
            # Start the proactive checker
            asyncio.create_task(self._proactive_monitor(call))

        except Exception as e:
            print(f"[ERROR] Agent failed to join call {call_id}: {e}")

    async def _proactive_monitor(self, call: Any):
        """Monitor for silence and trigger decisions or encouragement."""
        while not self.is_closed:
            await asyncio.sleep(2) # Granular check every 2 seconds
            now = time.time()
            silence_duration = now - self.last_transcript_time
            
            # 1. Trigger full decision if there's enough silence and an answer buffer
            if silence_duration > 6 and not self.is_speaking and not self.is_processing_decision:
                session = self.service.sessions.get(self.session_id)
                if session and len(session.answer_buffer.strip()) > 10 and not session.completed:
                    self.is_processing_decision = True
                    print(f"[PROACTIVE] Silence detected ({silence_duration:.1f}s). Triggering decision for {self.session_id}")
                    try:
                        # Directly call submit_answer with empty transcript to process buffer
                        # We pass an empty string because the buffer is already in session.answer_buffer
                        # and submit_answer will append it.
                        await self.service.submit_answer(self.session_id, transcript="")
                        # Reset transcript time so we don't trigger again immediately
                        self.last_transcript_time = time.time()
                    except Exception as e:
                        print(f"[ERROR] Proactive decision failed: {e}")
                    finally:
                        self.is_processing_decision = False
            
            # 2. Trigger encouragement if there's even longer silence and no buffer
            elif silence_duration > 20 and not self.is_speaking and not self.is_processing_decision:
                session = self.service.sessions.get(self.session_id)
                if session and not session.completed:
                    print(f"[PROACTIVE] Long silence detected ({silence_duration:.1f}s). Encouraging candidate.")
                    self.is_processing_decision = True
                    try:
                        await self.simple_response(
                            "I'm still here. Whenever you're ready, please share your thoughts on the question."
                        )
                        self.last_transcript_time = time.time()
                    finally:
                        self.is_processing_decision = False


    async def _run_agent_loop(self, call: Any):
        async with self.join(call):
            # The agent is now active in the call
            print(f"[INFO] Agent {self.agent_user.id} joined call {call.id}")
            
            # Speak the first question now that we are fully joined in the call
            session = self.service.sessions.get(self.session_id)
            if session and session.questions:
                first_q = session.questions[0].question
                greeting = f"Hello! I'm your {self.session_config.mode} interview coach. Let's get started. {first_q}"
                await self.simple_response(greeting)

            # The agent will now process transcripts and video frames via event handlers
            await self.finish()
            print(f"[INFO] Agent {self.agent_user.id} finished call {call.id}")


QUESTION_STORE_PATH = Path(__file__).resolve().parents[1] / "questions_normalized.json"


@dataclass(slots=True)
class SessionConfig:
    user_id: str
    role: str
    topics: list[str]
    difficulty: str
    mode: Literal["buddy", "strict"] = "buddy"


@dataclass(slots=True)
class Question:
    id: str
    question: str
    ideal_answer: str = ""
    category: str = "General"
    difficulty: str = "medium"
    source: str = "Local"


@dataclass(slots=True)
class QuestionResult:
    question_id: str
    question_text: str
    user_answer: str
    score: int
    confidence: int
    emotion: str
    fillers: int
    feedback: str
    created_at: float


@dataclass(slots=True)
class SessionState:
    id: str
    config: SessionConfig
    questions: list[Question]
    memory_context: str
    started_at: float
    current_q_idx: int = 0
    answer_buffer: str = ""
    question_results: list[QuestionResult] = field(default_factory=list)
    total_fillers: int = 0
    completed: bool = False
    completed_at: float | None = None
    agent: InterviewerAgent | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


class SpeechAnalyzer:
    FILLERS = {"um", "uh", "like", "basically", "literally"}
    FILLER_PHRASES = {"you know"}

    def analyze(self, transcript: str) -> int:
        text = transcript.lower()
        words = re.findall(r"[a-z']+", text)
        filler_words = sum(1 for token in words if token in self.FILLERS)
        filler_phrases = sum(text.count(phrase) for phrase in self.FILLER_PHRASES)
        return filler_words + filler_phrases


class EmotionAnalyzer:
    SIGNALS = {
        "nervous": {"nervous", "not sure", "maybe", "guess", "anxious"},
        "confused": {"confused", "unclear", "forget", "stuck", "hmm"},
        "focused": {"approach", "tradeoff", "complexity", "because", "first"},
        "confident": {"definitely", "clearly", "i would", "optimal", "guarantee"},
    }

    def infer_emotion(self, transcript: str, fallback: str | None = None) -> str:
        if fallback:
            return fallback
        text = transcript.lower()
        for emotion, keywords in self.SIGNALS.items():
            if any(keyword in text for keyword in keywords):
                return emotion
        return "neutral"

    def infer_confidence(self, transcript: str, filler_count: int, fallback: int | None = None) -> int:
        if fallback is not None:
            return _clamp(fallback, 10, 99)

        words = re.findall(r"[a-z']+", transcript.lower())
        if not words:
            return 50

        base = 62
        if len(words) > 35:
            base += 8
        if any(token in {"tradeoff", "complexity", "scale", "latency"} for token in words):
            base += 8
        base -= min(20, filler_count * 3)
        return _clamp(base, 25, 95)

try:
    from vision_agents.core.processors import VideoProcessor
except ImportError:  # pragma: no cover
    class VideoProcessor:  # type: ignore
        def __init__(self, *args, **kwargs):
            raise RuntimeError("vision-agents processor module missing")

class VisionEmotionProcessor(VideoProcessor):
    """Processes video frames to detect emotion and confidence."""
    @property
    def name(self) -> str:
        return "vision_emotion_processor"

    def __init__(self):
        super().__init__()
        # In a real app, you'd load a model here (e.g., Mediapipe, DeepFace, etc.)
        self.last_emotion = "neutral"
        self.last_confidence = 65

    async def close(self) -> None:
        pass

    async def stop_processing(self) -> None:
        pass

    async def process_video(
        self,
        track: Any,
        participant_id: str | None,
        shared_forwarder: Any | None = None,
    ) -> None:
        # In production, this would be updated by real vision triggers or background tasks.
        pass

    async def process(self, frame_chunk: Any) -> dict[str, Any]:
        """Returns the current emotion and confidence state."""
        return {
            "emotion": self.last_emotion,
            "confidence": self.last_confidence
        }

    def infer_confidence(self, transcript: str, filler_count: int, fallback: int | None = None) -> int:
        if fallback is not None:
            return _clamp(fallback, 10, 99)
        words = re.findall(r"[a-z']+", transcript.lower())
        if not words:
            return 50
        base = 62
        if len(words) > 35:
            base += 8
        if any(token in {"tradeoff", "complexity", "scale", "latency"} for token in words):
            base += 8
        base -= min(20, filler_count * 3)
        return _clamp(base, 25, 95)


class QuestionBank:
    def __init__(self) -> None:
        self._questions = self._load_local_questions()
        self._pinecone_index = None
        self._llm_client = None
        self._genai_client = None
        self._try_enable_gemini()
        self._try_enable_pinecone()

    def _load_local_questions(self) -> list[Question]:
        if not QUESTION_STORE_PATH.exists():
            return [
                Question(
                    id="fallback_1",
                    question="Explain how you would design a scalable notification service.",
                    category="System Design",
                    difficulty="medium",
                    source="Fallback",
                ),
                Question(
                    id="fallback_2",
                    question="Walk through a hash map implementation from scratch.",
                    category="Data Structures",
                    difficulty="medium",
                    source="Fallback",
                ),
                Question(
                    id="fallback_3",
                    question="Tell me about a time you handled conflict in a project team.",
                    category="Behavioral",
                    difficulty="easy",
                    source="Fallback",
                ),
            ]

        try:
            raw = json.loads(QUESTION_STORE_PATH.read_text())
            questions: list[Question] = []
            for item in raw:
                question_text = str(item.get("question", "")).strip()
                if not question_text:
                    continue
                questions.append(
                    Question(
                        id=str(item.get("id") or f"q_{len(questions)+1}"),
                        question=question_text,
                        ideal_answer=str(item.get("ideal_answer") or ""),
                        category=str(item.get("category") or "General"),
                        difficulty=str(item.get("difficulty") or "medium").lower(),
                        source=str(item.get("source") or "Local"),
                    )
                )
            return questions
        except Exception:
            return []

    def _try_enable_pinecone(self) -> None:
        if not settings.use_pinecone:
            return
        if Pinecone is None or genai is None:
            return

        pinecone_key = settings.pinecone_api_key
        index_name = settings.pinecone_index
        if not pinecone_key:
            return

        try:
            pc = Pinecone(api_key=pinecone_key)
            self._pinecone_index = pc.Index(index_name)
            self._genai_client = self._llm_client
        except Exception:
            self._pinecone_index = None
            self._genai_client = None

    def _try_enable_gemini(self) -> None:
        if genai is None:
            return
        gemini_key = settings.gemini_api_key
        if not gemini_key:
            return
        try:
            self._llm_client = genai.Client(api_key=gemini_key)
        except Exception:
            self._llm_client = None

    async def upsert_session_vector(
        self,
        user_id: str,
        session_id: str,
        text: str,
        kind: str,
    ) -> None:
        """Store embeddings for personalization (answers, summaries)."""
        if self._pinecone_index is None or self._genai_client is None or not text.strip():
            return

        def _embed_and_upsert() -> None:
            embed = self._genai_client.models.embed_content(model="models/gemini-embedding-001", contents=text)
            vector = embed.embeddings[0].values
            self._pinecone_index.upsert(
                vectors=[
                    {
                        "id": f"{session_id}:{kind}",
                        "values": vector,
                        "metadata": {"user_id": user_id, "session_id": session_id, "kind": kind, "text": text[:2000]},
                    }
                ]
            )

        try:
            await asyncio.to_thread(_embed_and_upsert)
        except Exception:
            return

    async def fetch_session_vectors(self, user_id: str, limit: int = 5) -> list[str]:
        """Fetch past answer texts for a user from Pinecone."""
        if self._pinecone_index is None:
            return []

        def _query() -> list[str]:
            # Use a zero vector of the correct dimensionality (3072 for Gemini Embedding v1)
            # to retrieve metadata by filtering on user_id.
            query_vector = [0.0] * 768 # models/gemini-embedding-001 is 768 dims, text-embedding-004 is 768-3072
            # Checking dimension from prepare_datasets.py logic (it used 1536 for Pinecone usually, 
            # but let's check index_to_pinecone.py)
            # Actually, Gemini embedding-001 is 768. 
            result = self._pinecone_index.query(
                vector=[0.0] * 768, 
                top_k=limit,
                filter={"user_id": user_id},
                include_metadata=True,
            )
            matches = getattr(result, "matches", None) or result.get("matches", [])
            past_answers = []
            for m in matches:
                md = getattr(m, "metadata", None) or m.get("metadata", {})
                text = md.get("text")
                if text:
                    past_answers.append(str(text))
            return past_answers

        try:
            return await asyncio.to_thread(_query)
        except Exception:
            return []

    async def fetch_questions(
        self, role: str, topics: list[str], difficulty: str, n: int = 8
    ) -> list[Question]:
        generated = await self._generate_dynamic_questions(role, topics, difficulty, n)
        if generated:
            return generated

        if self._pinecone_index is not None and self._genai_client is not None:
            remote = await self._fetch_from_pinecone(role, topics, difficulty, n)
            if remote:
                return remote

        return self._fetch_from_local(role, topics, difficulty, n)

    async def _generate_dynamic_questions(
        self, role: str, topics: list[str], difficulty: str, n: int
    ) -> list[Question]:
        if self._llm_client is None:
            return []

        topic_text = ", ".join(topics) if topics else "general technical interview"
        prompt = (
            "Generate a personalized mock interview question set as JSON only. "
            "Return an array with exactly "
            f"{n}"
            " items. Each item must include: question, category, difficulty, ideal_answer. "
            "Difficulty progression should ramp from warm-up to challenging. "
            f"Role target: {role}. Topics: {topic_text}. Requested baseline difficulty: {difficulty}. "
            "Keep questions practical, realistic, and interviewer-grade."
        )

        def _query() -> list[Question]:
            models = [
                "models/gemini-2.5-flash-lite",
                "models/gemini-2.0-flash-lite-001",
                "models/gemini-flash-lite-latest",
                "models/gemini-2.5-flash",
            ]
            raw_text = ""
            for model in models:
                try:
                    response = self._llm_client.models.generate_content(model=model, contents=prompt)
                    raw_text = getattr(response, "text", "") or ""
                    if raw_text:
                        break
                except Exception:
                    continue

            if not raw_text:
                return []

            payload = self._parse_json_payload(raw_text)
            if isinstance(payload, dict):
                payload = payload.get("questions")
            if not isinstance(payload, list):
                return []

            generated: list[Question] = []
            seen: set[str] = set()
            for idx, item in enumerate(payload, start=1):
                if not isinstance(item, dict):
                    continue
                question_text = str(item.get("question") or "").strip()
                if not question_text or question_text in seen:
                    continue
                seen.add(question_text)
                generated.append(
                    Question(
                        id=f"dyn_{idx}_{uuid4().hex[:8]}",
                        question=question_text,
                        ideal_answer=str(item.get("ideal_answer") or ""),
                        category=str(item.get("category") or "General"),
                        difficulty=str(item.get("difficulty") or difficulty).lower(),
                        source="GeminiGenerated",
                    )
                )
                if len(generated) >= n:
                    break

            if len(generated) < n:
                fallback = self._fetch_from_local(role, topics, difficulty, n=n * 2)
                for question in fallback:
                    if question.question in seen:
                        continue
                    generated.append(question)
                    seen.add(question.question)
                    if len(generated) >= n:
                        break

            return generated[:n]

        try:
            return await asyncio.to_thread(_query)
        except Exception:
            return []

    def _parse_json_payload(self, raw_text: str) -> Any:
        text = raw_text.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", text)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    async def _fetch_from_pinecone(
        self, role: str, topics: list[str], difficulty: str, n: int
    ) -> list[Question]:
        def _query() -> list[Question]:
            query = f"{role} {' '.join(topics)} {difficulty} interview"
            embed = self._genai_client.models.embed_content(
                model="models/gemini-embedding-001", contents=query
            )
            vector = embed.embeddings[0].values
            result = self._pinecone_index.query(
                vector=vector,
                top_k=n,
                filter={"difficulty": {"$in": [difficulty, "medium"]}},
                include_metadata=True,
            )
            matches = getattr(result, "matches", None) or result.get("matches", [])
            questions: list[Question] = []
            for match in matches:
                md = getattr(match, "metadata", None) or match.get("metadata", {})
                question_text = str(md.get("question") or "").strip()
                if not question_text:
                    continue
                questions.append(
                    Question(
                        id=str(getattr(match, "id", None) or match.get("id") or uuid4()),
                        question=question_text,
                        ideal_answer=str(md.get("ideal_answer") or ""),
                        category=str(md.get("category") or "General"),
                        difficulty=str(md.get("difficulty") or difficulty),
                        source=str(md.get("source") or "Pinecone"),
                    )
                )
            return questions

        try:
            return await asyncio.to_thread(_query)
        except Exception:
            return []

    def _fetch_from_local(
        self, role: str, topics: list[str], difficulty: str, n: int
    ) -> list[Question]:
        if not self._questions:
            return []

        role_terms = {term.lower() for term in re.findall(r"[a-zA-Z]+", role)}
        topic_terms = {
            token.lower()
            for topic in topics
            for token in re.findall(r"[a-zA-Z]+", topic)
            if len(token) > 2
        }

        preferred = [difficulty, "medium"] if difficulty != "medium" else ["medium", "hard", "easy"]

        def _score(question: Question) -> tuple[int, int]:
            text = f"{question.question} {question.category}".lower()
            topic_hits = sum(1 for term in topic_terms if term in text)
            role_hits = sum(1 for term in role_terms if term in text)
            diff_bonus = 2 if question.difficulty in preferred else 0
            return (topic_hits * 4 + role_hits * 2 + diff_bonus, len(question.question))

        ranked = sorted(self._questions, key=_score, reverse=True)
        selected: list[Question] = []
        seen: set[str] = set()
        for question in ranked:
            if question.question in seen:
                continue
            selected.append(question)
            seen.add(question.question)
            if len(selected) >= n:
                break

        return selected[:n]


class MemoryProvider:
    def __init__(self) -> None:
        self._client = None
        key = settings.supermemory_api_key
        if key and Supermemory is not None and settings.use_supermemory:
            try:
                self._client = Supermemory(api_key=key)
            except Exception:
                self._client = None

    async def fetch_context(self, user_id: str, question_bank: Optional["QuestionBank"] = None) -> str:
        """Fetch unified memory context from Supermemory and Pinecone."""
        parts = []

        # 1. Supermemory Context
        if self._client is not None:
            def _search() -> str:
                result = self._client.search(query="interview strengths weaknesses", user_id=user_id)
                if not result:
                    return ""
                first = result[0]
                return str(first.get("content") or "") if isinstance(first, dict) else str(first)

            try:
                sm_context = await asyncio.to_thread(_search)
                if sm_context:
                    parts.append(f"Supermemory: {sm_context}")
            except Exception:
                pass

        # 2. Pinecone Past Answers Context
        if question_bank:
            past_answers = await question_bank.fetch_session_vectors(user_id, limit=3)
            if past_answers:
                answers_str = "\n".join(f"- {a}" for a in past_answers)
                parts.append(f"Past Answers (Pinecone):\n{answers_str}")

        if not parts:
            return "No prior memory available."
        
        return "\n\n".join(parts)

    async def save_summary(self, user_id: str, summary: str) -> None:
        if self._client is None:
            return

        def _add() -> None:
            self._client.add(summary, user_id=user_id)

        try:
            await asyncio.to_thread(_add)
        except Exception:
            return


class DecisionEngine:
    def __init__(self) -> None:
        self._llm = None
        self.system_prompt = (
            "You are an expert technical interview coach. Your goal is to guide candidates "
            "through a mock interview. Evaluate their responses based on technical depth, "
            "confidence, and communication style. Decide between CONTINUE, NEXT, HINT, or ENCOURAGE."
        )

    async def decide(
        self,
        question: str,
        answer: str,
        confidence: int,
        fillers: int,
        mode: Literal["buddy", "strict"],
        ideal_answer: str = "",
    ) -> tuple[Action, str, int | None]:
        # Lazy initialization to avoid "no running event loop" at module load
        if self._llm is None:
            key = settings.anthropic_api_key
            use_claude = settings.use_claude_decision
            if ClaudeLLM and key and use_claude:
                try:
                    model = settings.claude_model
                    logger.info(f"DecisionEngine: Initializing ClaudeLLM with model {model}")
                    self._llm = ClaudeLLM(model=model, api_key=key)
                    logger.info("DecisionEngine: ClaudeLLM initialized successfully")
                except Exception as e:
                    logger.error(f"DecisionEngine: Failed to initialize ClaudeLLM: {e}")
                    self._llm = None
            else:
                logger.info("DecisionEngine: Claude disabled or missing (heuristics mode)")

        if self._llm:
            llm_result = await self._decide_with_llm(question, answer, confidence, fillers, mode, ideal_answer)
            if llm_result is not None:
                return llm_result
        action, message = self._decide_with_heuristics(answer, confidence, fillers, mode)
        return action, message, None

    async def _decide_with_llm(
        self,
        question: str,
        answer: str,
        confidence: int,
        fillers: int,
        mode: Literal["buddy", "strict"],
        ideal_answer: str = "",
    ) -> tuple[Action, str, int | None] | None:
        prompt = (
            "You are an expert interview coach. Evaluate the candidate's answer and decide the next action. "
            "Return valid JSON: {\"action\":\"CONTINUE|NEXT|HINT|ENCOURAGE\",\"message\":\"...\",\"score\":0-100}.\n"
            f"Mode: {mode}\n"
            f"Question: {question}\n"
            f"Ideal Answer: {ideal_answer}\n"
            f"Candidate Answer: {answer}\n"
            f"Candidate Confidence: {confidence}\n"
            f"Filler Word Count: {fillers}\n"
            "If action is NEXT, provide a score from 0 to 100 based on the answer quality compared to the ideal answer. "
            "If action is CONTINUE/HINT/ENCOURAGE, score can be null or 0."
        )
        try:
            event = await self._llm.simple_response(prompt)
            text = (event.text or "").strip()
            payload = self._parse_response_payload(text)
            if payload is None:
                return None
            action = payload.get("action", "CONTINUE").upper()
            message = str(payload.get("message") or "")
            score = payload.get("score")
            if action not in {"CONTINUE", "NEXT", "HINT", "ENCOURAGE"}:
                return None
            return action, message, int(score) if score is not None else None
        except Exception:
            return None

    def _parse_response_payload(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def _decide_with_heuristics(
        self, answer: str, confidence: int, fillers: int, mode: Literal["buddy", "strict"]
    ) -> tuple[Action, str]:
        words = re.findall(r"[a-zA-Z']+", answer)
        count = len(words)

        if count < 20:
            if mode == "strict":
                return "HINT", "Too short. Clarify your architecture and trade-offs."
            return "ENCOURAGE", "Good start. Add more detail on your reasoning and trade-offs."

        if fillers >= max(3, count // 14):
            if mode == "strict":
                return "HINT", "Slow down and remove filler words. Structure the answer in clear steps."
            return "HINT", "Nice direction. Try pausing briefly to reduce filler words."

        if confidence < 45:
            return "ENCOURAGE", "You are close. Start with a high-level plan, then drill into details."

        if count >= 40:
            if mode == "strict":
                return "NEXT", "Answer accepted. Next question."
            return "NEXT", "Great explanation. Let's move to the next question."

        return "CONTINUE", "Continue your answer and include edge cases."


class NeonDatabase:
    def __init__(self) -> None:
        self.dsn = settings.database_url
        if asyncpg is None or not self.dsn:
            print("[WARN] NeonDatabase disabled: asyncpg not installed or DATABASE_URL missing.")
            self.enabled = False
        else:
            self.enabled = True

    async def _get_connection(self):
        return await asyncpg.connect(self.dsn)

    async def insert_session(self, session: SessionState) -> None:
        if not self.enabled:
            return

        query = """
        INSERT INTO sessions (id, user_id, role, topics, difficulty, mode, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (id) DO NOTHING
        """
        try:
            conn = await self._get_connection()
            try:
                await conn.execute(
                    query,
                    session.id,
                    session.config.user_id,
                    session.config.role,
                    session.config.topics,
                    session.config.difficulty,
                    session.config.mode,
                    datetime.now(timezone.utc),
                )
            finally:
                await conn.close()
        except Exception as exc:
            print(f"[WARN] Neon insert_session failed: {exc}")

    async def insert_question_result(self, session_id: str, result: QuestionResult) -> None:
        if not self.enabled:
            return

        query = """
        INSERT INTO question_results (id, session_id, question_text, user_answer, score, filler_word_count, emotion_log, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        try:
            conn = await self._get_connection()
            try:
                await conn.execute(
                    query,
                    str(uuid4()),
                    session_id,
                    result.question_text,
                    result.user_answer,
                    result.score,
                    result.fillers,
                    json.dumps({
                        "emotion": result.emotion,
                        "confidence": result.confidence,
                        "ts": result.created_at,
                    }),
                    datetime.now(timezone.utc),
                )
            finally:
                await conn.close()
        except Exception as exc:
            print(f"[WARN] Neon insert_question_result failed: {exc}")

    async def finalize_session(
        self, session_id: str, overall_score: int, confidence_avg: int, ended_at: float
    ) -> None:
        if not self.enabled:
            return

        query = """
        UPDATE sessions 
        SET overall_score = $1, confidence_avg = $2, ended_at = $3
        WHERE id = $4
        """
        try:
            conn = await self._get_connection()
            try:
                await conn.execute(
                    query,
                    overall_score,
                    confidence_avg,
                    datetime.fromtimestamp(ended_at, tz=timezone.utc),
                    session_id,
                )
            finally:
                await conn.close()
        except Exception as exc:
            print(f"[WARN] Neon finalize_session failed: {exc}")


class InterviewerService:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionState] = {}
        self.question_bank = QuestionBank()
        self.memory_provider = MemoryProvider()
        self.decision_engine = DecisionEngine()
        self.speech = SpeechAnalyzer()
        self.emotion = EmotionAnalyzer()
        self.db = NeonDatabase()
        self.listeners: dict[str, list[asyncio.Queue]] = {}

    async def register_listener(self, session_id: str, queue: asyncio.Queue) -> None:
        if session_id not in self.listeners:
            self.listeners[session_id] = []
        self.listeners[session_id].append(queue)

    async def unregister_listener(self, session_id: str, queue: asyncio.Queue) -> None:
        if session_id in self.listeners:
            self.listeners[session_id].remove(queue)
            if not self.listeners[session_id]:
                del self.listeners[session_id]

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        if session_id in self.listeners:
            for queue in self.listeners[session_id]:
                await queue.put(event)

    async def start_session(self, config: SessionConfig) -> dict[str, Any]:
        questions = await self.question_bank.fetch_questions(
            role=config.role,
            topics=config.topics,
            difficulty=config.difficulty,
            n=8,
        )
        if not questions:
            raise RuntimeError("No interview questions available.")

        session_id = str(uuid4())
        memory_context = await self.memory_provider.fetch_context(config.user_id, self.question_bank)

        session = SessionState(
            id=session_id,
            config=config,
            questions=questions,
            memory_context=memory_context,
            started_at=time.time(),
        )
        
        # Generate call_id early to share with agent and response
        call_id = f"session_{session_id[:8]}"
        # Vision agent bootstrapping is handled in backend/main.py, where failures are non-fatal.
        self.sessions[session_id] = session
        await self.db.insert_session(session)

        return {
            "session_id": session.id,
            "call_id": call_id,
            "first_question": session.questions[0].question,
            "questions": [
                {"id": q.id, "text": q.question} for q in session.questions
            ],
            "question_index": 1,
            "total_questions": len(session.questions),
            "memory_context": session.memory_context,
        }

    async def submit_answer(
        self,
        session_id: str,
        transcript: str,
        confidence: int | None = None,
        emotion: str | None = None,
    ) -> dict[str, Any]:
        session = self._get_active_session(session_id)
        clean_text = transcript.strip()
        if not clean_text:
            return {
                "action": "CONTINUE",
                "message": "Please share your answer.",
                "question": session.questions[session.current_q_idx].question,
                "question_index": session.current_q_idx + 1,
                "total_questions": len(session.questions),
                "is_finished": False,
            }

        fillers = self.speech.analyze(clean_text)
        session.total_fillers += fillers
        resolved_emotion = self.emotion.infer_emotion(clean_text, fallback=emotion)
        resolved_confidence = self.emotion.infer_confidence(
            clean_text, filler_count=fillers, fallback=confidence
        )
        session.answer_buffer = f"{session.answer_buffer} {clean_text}".strip()

        current = session.questions[session.current_q_idx]
        action, message, llm_score = await self.decision_engine.decide(
            question=current.question,
            answer=session.answer_buffer,
            confidence=resolved_confidence,
            fillers=fillers,
            mode=session.config.mode,
            ideal_answer=current.ideal_answer,
        )

        if action == "NEXT":
            return await self._advance_question(
                session=session,
                confidence=resolved_confidence,
                emotion=resolved_emotion,
                fillers=fillers,
                feedback=message,
                llm_score=llm_score,
            )

        # If an agent is active in this session, make it speak the feedback
        if session.agent and message:
            # We don't speak for CONTINUE to avoid interrupting natural flow
            if action in {"HINT", "ENCOURAGE"}:
                asyncio.create_task(session.agent.simple_response(message))

        return {
            "action": action,
            "message": message,
            "question": current.question,
            "question_index": session.current_q_idx + 1,
            "total_questions": len(session.questions),
            "is_finished": False,
            "stats": {
                "fillers": session.total_fillers,
                "confidence": resolved_confidence,
                "emotion": resolved_emotion,
            },
        }

    async def end_session(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        if session.completed:
            return {"session_id": session_id, "status": "completed"}

        if session.answer_buffer and session.current_q_idx < len(session.questions):
            filler_snapshot = self.speech.analyze(session.answer_buffer)
            confidence_snapshot = self.emotion.infer_confidence(session.answer_buffer, filler_snapshot)
            emotion_snapshot = self.emotion.infer_emotion(session.answer_buffer)
            await self._advance_question(
                session=session,
                confidence=confidence_snapshot,
                emotion=emotion_snapshot,
                fillers=filler_snapshot,
                feedback="Session ended by user.",
                force_end=True,
            )

        await self._finalize_session(session)
        return {"session_id": session_id, "status": "completed"}

    async def get_report(self, session_id: str) -> dict[str, Any]:
        session = self._get_session(session_id)
        if not session.completed:
            await self._finalize_session(session)

        duration_seconds = int((session.completed_at or time.time()) - session.started_at)
        scores = [item.score for item in session.question_results]
        confidences = [item.confidence for item in session.question_results]

        overall = round(sum(scores) / len(scores)) if scores else 0
        confidence_avg = round(sum(confidences) / len(confidences)) if confidences else 0
        strengths, weaknesses = self._extract_strengths_weaknesses(session.question_results)

        return {
            "session": {
                "id": session.id,
                "user_id": session.config.user_id,
                "role": session.config.role,
                "topics": session.config.topics,
                "difficulty": session.config.difficulty,
                "mode": session.config.mode,
                "overall_score": overall,
                "confidence_avg": confidence_avg,
                "duration_seconds": duration_seconds,
                "created_at": datetime.fromtimestamp(session.started_at, tz=timezone.utc).isoformat(),
                "ended_at": datetime.fromtimestamp(
                    session.completed_at or time.time(), tz=timezone.utc
                ).isoformat(),
            },
            "overall_score": overall,
            "confidence_avg": confidence_avg,
            "duration_seconds": duration_seconds,
            "questions_answered": len(session.question_results),
            "total_questions": len(session.questions),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "emotion_timeline": [item.confidence for item in session.question_results],
            "breakdown": [
                {
                    "question": item.question_text,
                    "score": item.score,
                    "emotion": item.emotion,
                    "fillers": item.fillers,
                    "feedback": item.feedback,
                    "user_answer": item.user_answer,
                }
                for item in session.question_results
            ],
        }

    async def _advance_question(
        self,
        session: SessionState,
        confidence: int,
        emotion: str,
        fillers: int,
        feedback: str,
        force_end: bool = False,
        llm_score: int | None = None,
    ) -> dict[str, Any]:
        question = session.questions[session.current_q_idx]
        score = llm_score if llm_score is not None else self._score_answer(
            answer=session.answer_buffer,
            confidence=confidence,
            fillers=fillers,
            mode=session.config.mode,
        )
        result = QuestionResult(
            question_id=question.id,
            question_text=question.question,
            user_answer=session.answer_buffer,
            score=score,
            confidence=confidence,
            emotion=emotion,
            fillers=fillers,
            feedback=feedback,
            created_at=time.time(),
        )
        session.question_results.append(result)
        await self.db.insert_question_result(session.id, result)
        await self.question_bank.upsert_session_vector(
            user_id=session.config.user_id,
            session_id=session.id,
            text=result.user_answer,
            kind=f"answer_{session.current_q_idx}",
        )

        session.answer_buffer = ""
        session.current_q_idx += 1

        finished = force_end or session.current_q_idx >= len(session.questions)
        
        # Make the agent speak the feedback and next question (if any)
        if session.agent:
            if finished:
                asyncio.create_task(session.agent.simple_response(f"{feedback} Interview complete. Generating your report now."))
            else:
                next_q = session.questions[session.current_q_idx].question
                asyncio.create_task(session.agent.simple_response(f"{feedback} Next question. {next_q}"))

        if finished:
            await self._finalize_session(session)
            return {
                "action": "NEXT",
                "message": "Interview complete. Generating report.",
                "question": None,
                "question_index": len(session.questions),
                "total_questions": len(session.questions),
                "is_finished": True,
                "stats": {
                    "fillers": session.total_fillers,
                    "confidence": confidence,
                    "emotion": emotion,
                },
            }

        next_question = session.questions[session.current_q_idx]
        return {
            "action": "NEXT",
            "message": feedback,
            "question": next_question.question,
            "question_index": session.current_q_idx + 1,
            "total_questions": len(session.questions),
            "is_finished": False,
            "stats": {
                "fillers": session.total_fillers,
                "confidence": confidence,
                "emotion": emotion,
            },
        }

    async def _finalize_session(self, session: SessionState) -> None:
        if session.completed:
            return
        session.completed = True
        session.completed_at = time.time()

        scores = [item.score for item in session.question_results]
        confidences = [item.confidence for item in session.question_results]

        overall = round(sum(scores) / len(scores)) if scores else 0
        confidence_avg = round(sum(confidences) / len(confidences)) if confidences else 0
        await self.db.finalize_session(
            session_id=session.id,
            overall_score=overall,
            confidence_avg=confidence_avg,
            ended_at=session.completed_at,
        )

        strengths, weaknesses = self._extract_strengths_weaknesses(session.question_results)
        summary = (
            f"Interview summary for {session.config.user_id}. "
            f"Role: {session.config.role}. Strengths: {', '.join(strengths) or 'n/a'}. "
            f"Weaknesses: {', '.join(weaknesses) or 'n/a'}."
        )
        await self.memory_provider.save_summary(session.config.user_id, summary)
        await self.question_bank.upsert_session_vector(
            user_id=session.config.user_id,
            session_id=session.id,
            text=summary,
            kind="summary",
        )

    def _score_answer(
        self,
        answer: str,
        confidence: int,
        fillers: int,
        mode: Literal["buddy", "strict"],
    ) -> int:
        words = len(re.findall(r"[a-zA-Z']+", answer))
        depth_score = min(25, words // 3)
        filler_penalty = min(18, fillers * 2)
        strict_penalty = 4 if mode == "strict" else 0
        score = confidence + depth_score - filler_penalty - strict_penalty
        return _clamp(score, 20, 98)

    @staticmethod
    def _extract_strengths_weaknesses(
        results: list[QuestionResult],
    ) -> tuple[list[str], list[str]]:
        if not results:
            return [], []

        def _short_title(text: str) -> str:
            """Extract a short label from question text (first line before ':')."""
            first_line = text.split("\n")[0].strip()
            if ":" in first_line:
                return first_line.split(":")[0].strip()
            return first_line[:80] + ("..." if len(first_line) > 80 else "")

        by_score = sorted(results, key=lambda item: item.score, reverse=True)
        strengths = [f"{_short_title(r.question_text)} (score: {r.score})" for r in by_score[:3]]
        weaknesses = [f"{_short_title(r.question_text)} (score: {r.score})" for r in by_score[-3:][::-1]]
        return strengths, weaknesses

    def _get_active_session(self, session_id: str) -> SessionState:
        session = self._get_session(session_id)
        if session.completed:
            raise ValueError("Session already completed")
        return session

    def _get_session(self, session_id: str) -> SessionState:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError("Session not found")
        return session


_SERVICE: InterviewerService | None = None


def get_interviewer_service() -> InterviewerService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = InterviewerService()
    return _SERVICE


# Vision Agents CLI Runner support
async def create_agent_factory(**kwargs) -> Agent:
    """Factory for CLI development mode."""
    service = get_interviewer_service()
    config = SessionConfig(
        user_id="test_user",
        role="Software Engineer",
        topics=["System Design", "Python"],
        difficulty="medium",
        mode="buddy"
    )
    # Start a mock session to get questions
    session_data = await service.start_session(config)
    agent = InterviewerAgent(session_id=session_data["session_id"], config=config, service=service)
    return agent

async def join_call_factory(agent: Agent, call_type: str, call_id: str, **kwargs):
    """Factory for CLI development mode."""
    if isinstance(agent, InterviewerAgent):
        await agent.join_session_call(call_id, call_type)

if __name__ == "__main__":
    from vision_agents.core import Runner, AgentLauncher
    Runner(AgentLauncher(create_agent=create_agent_factory, join_call=join_call_factory)).cli()
