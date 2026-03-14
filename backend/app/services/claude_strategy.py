"""
Claude Strategy Service
=======================
Uses claude-sonnet-4-6 to evaluate candidate answers and return precise
coaching guidance to Aria (the Gemini Live interviewer).

This keeps Gemini focused on voice/conversation while Claude handles
the "smart" analysis of whether an answer was right, wrong, partial, etc.
"""

import json
import logging
from dataclasses import dataclass
from typing import Literal

import anthropic

from app.core.settings import get_settings

logger = logging.getLogger(__name__)

AnswerQuality = Literal["EXCELLENT", "GOOD", "PARTIAL", "WRONG", "DONT_KNOW", "OFF_TOPIC"]
NextAction = Literal["NEXT_QUESTION", "FOLLOW_UP", "CORRECT_AND_FOLLOW_UP", "GIVE_HINT", "REDIRECT_THEN_CONTINUE"]


@dataclass
class AnswerEvaluation:
    quality: AnswerQuality
    next_action: NextAction
    correctness_percent: int       # 0–100
    what_was_right: str
    what_was_wrong: str
    follow_up_question: str        # populated when next_action != NEXT_QUESTION
    coaching_note: str             # what Aria should say aloud
    hint: str                      # populated for DONT_KNOW / GIVE_HINT
    slang_detected: bool
    score: int                     # 1–10
    score_explanation: str


_SYSTEM_PROMPT = """You are a senior technical interview coach. Evaluate the candidate's answer to the interview question and return ONLY a valid JSON object — no markdown, no explanation.

JSON schema (all fields required):
{
  "quality": "EXCELLENT" | "GOOD" | "PARTIAL" | "WRONG" | "DONT_KNOW" | "OFF_TOPIC",
  "next_action": "NEXT_QUESTION" | "FOLLOW_UP" | "CORRECT_AND_FOLLOW_UP" | "GIVE_HINT" | "REDIRECT_THEN_CONTINUE",
  "correctness_percent": <integer 0-100>,
  "what_was_right": "<one concise sentence, or empty string>",
  "what_was_wrong": "<one concise sentence about the gap, or empty string if fully correct>",
  "follow_up_question": "<exact follow-up question to ask next, or empty string if NEXT_QUESTION>",
  "coaching_note": "<1-2 warm, natural sentences for the interviewer to say aloud that acknowledge the answer and lead into the next action>",
  "hint": "<a helpful hint or reframed version of the question for GIVE_HINT, otherwise empty string>",
  "slang_detected": <true | false>,
  "score": <integer 1-10>,
  "score_explanation": "<one sentence>"
}

Quality rules:
- EXCELLENT  → 80-100% correct, comprehensive, well-structured
- GOOD       → 60-79% correct, mostly right with minor gaps
- PARTIAL    → 30-59% correct, some right elements but significant gaps
- WRONG      → 0-29% correct, fundamentally incorrect or irrelevant
- DONT_KNOW  → candidate explicitly said they don't know / blank / "no idea"
- OFF_TOPIC  → candidate answered a completely different question

Next action rules:
- EXCELLENT / GOOD   → NEXT_QUESTION  (move forward, don't dwell)
- PARTIAL            → FOLLOW_UP  (one targeted follow-up to fill the gap)
- WRONG              → CORRECT_AND_FOLLOW_UP  (correct the misconception, then ask a simpler follow-up)
- DONT_KNOW          → GIVE_HINT  (give a nudge, let them try again before moving on)
- OFF_TOPIC          → REDIRECT_THEN_CONTINUE  (politely bring them back, then accept whatever they say next)

Coaching note guidelines — Aria is warm, sharp, genuinely invested:
- EXCELLENT: brief genuine praise then bridge to next  ("That was really well-explained — you nailed both the concept and a real-world example.")
- GOOD: acknowledge what worked, note the gap gently  ("Solid answer. You covered the main idea well — just missing the edge case around X.")
- PARTIAL: name what was right before saying what's missing  ("Good start — you got the high-level right. Let me push on one specific piece.")
- WRONG: no shaming, just reframe clearly  ("Not quite — let me clear this up. The key thing here is X, and here's why that matters...")
- DONT_KNOW: normalise it, then give the hint  ("That's totally fine — this one trips people up. Think about it this way: ...")
- Slang detected: weave in a professional redirect naturally  ("One thing — in an actual interview, keep it professional. Instead of 'X' try 'Y'. Now, your point was...")

Always write coaching_note in first-person as if Aria is speaking it aloud right now.
"""


class ClaudeStrategyService:
    _client: anthropic.AsyncAnthropic | None = None

    @classmethod
    def _get_client(cls) -> anthropic.AsyncAnthropic:
        if cls._client is None:
            settings = get_settings()
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is not set. Add it to backend/.env")
            cls._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return cls._client

    @classmethod
    async def evaluate_answer(
        cls,
        question: str,
        candidate_answer: str,
        topic: str,
        difficulty: str,
        question_number: int,
        ideal_answer: str = "",
    ) -> AnswerEvaluation:
        """
        Evaluate the candidate's answer and return structured coaching guidance.
        Called inside the evaluate_answer ADK tool so Aria always knows what to do next.
        """
        client = cls._get_client()

        user_msg = (
            f"Topic: {topic}\n"
            f"Difficulty: {difficulty}\n"
            f"Question #{question_number}: {question}\n\n"
            f'Candidate answer: "{candidate_answer}"'
        )

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = response.content[0].text.strip()
            # Strip any accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            # Blend Gemini embedding semantic similarity into the score when an
            # ideal answer is available. 70% Claude (qualitative) + 30% embedding
            # (semantic alignment). This is best-effort — failures are silent.
            if ideal_answer:
                try:
                    from app.services.embedding_service import GeminiEmbeddingService
                    similarity = await GeminiEmbeddingService.semantic_similarity_score(
                        candidate_answer, ideal_answer
                    )
                    if similarity is not None:
                        embedding_score = similarity * 10  # 0–10 scale
                        blended = round(0.7 * data["score"] + 0.3 * embedding_score)
                        data["score"] = max(1, min(10, blended))
                        data["score_explanation"] = (
                            f"{data['score_explanation']} "
                            f"[Semantic alignment: {similarity:.0%}]"
                        )
                except Exception as emb_exc:
                    logger.debug(f"Embedding blend skipped: {emb_exc}")

            return AnswerEvaluation(
                quality=data["quality"],
                next_action=data["next_action"],
                correctness_percent=int(data.get("correctness_percent", 50)),
                what_was_right=data.get("what_was_right", ""),
                what_was_wrong=data.get("what_was_wrong", ""),
                follow_up_question=data.get("follow_up_question", ""),
                coaching_note=data.get("coaching_note", "Good effort. Let's continue."),
                hint=data.get("hint", ""),
                slang_detected=bool(data.get("slang_detected", False)),
                score=int(data.get("score", 5)),
                score_explanation=data.get("score_explanation", ""),
            )

        except Exception as e:
            logger.error(f"Claude evaluation failed: {e}")
            # Safe fallback — don't stall the interview
            return AnswerEvaluation(
                quality="PARTIAL",
                next_action="NEXT_QUESTION",
                correctness_percent=50,
                what_was_right="Some relevant points were made.",
                what_was_wrong="The answer could be more specific.",
                follow_up_question="",
                coaching_note="Interesting perspective. Let's keep moving.",
                hint="",
                slang_detected=False,
                score=5,
                score_explanation="Evaluation unavailable — partial credit assigned.",
            )
