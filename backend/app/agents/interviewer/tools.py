"""
Interviewer Agent Tools
=======================
Functions called by Aria (the Gemini Live agent) during the interview.

Context-variable injection
--------------------------
Before starting an ADK session, websocket.py sets two ContextVars:

  _session_id_ctx  – the current interview session ID
  _websocket_ctx   – the live FastAPI WebSocket for this connection

Python's asyncio propagates the current context to child tasks (via
asyncio.gather / asyncio.create_task), so these values are visible
inside every tool call regardless of how ADK schedules them.

This gives us a belt-and-suspenders guarantee:
  • record_score   → persists to Redis/Neon directly from the tool
  • signal_interview_end → sends the terminal WS event directly from the tool

Both also have a secondary path in process_tool_results (websocket.py) that
intercepts function-call events from the ADK event stream.  The tool-based
path fires first (ADK always calls the tool function), making persistence and
WS notification guaranteed even if the event stream doesn't expose tool calls.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-connection context variables
# Set once by websocket_endpoint() in websocket.py before running the session.
# ---------------------------------------------------------------------------

#: Current interview session ID — used by tools to persist results.
_session_id_ctx: ContextVar[str] = ContextVar("rz_session_id", default="")

#: Live WebSocket for this connection — used by signal_interview_end to push
#: the terminal event directly to the frontend without going through the
#: ADK event-stream.
_websocket_ctx: ContextVar[Any] = ContextVar("rz_websocket", default=None)


# ---------------------------------------------------------------------------
# Core strategic tool — Claude evaluates every answer, Aria acts on the result
# ---------------------------------------------------------------------------

async def evaluate_answer(
    question_number: int,
    question_text: str,
    candidate_answer: str,
    ideal_answer: str = "",
    topic: str = "General",
    difficulty: str = "Medium",
) -> str:
    """
    CALL THIS IMMEDIATELY after the candidate finishes answering any question or follow-up.
    Claude evaluates the answer quality; Gemini Embeddings scores semantic alignment.

    Pass ideal_answer when available (from the question bank) — it enables
    Gemini embedding-based semantic alignment scoring for a richer, more accurate
    score that blends qualitative (Claude) with quantitative (Gemini) signals.

    Returns a structured coaching brief with:
    - Whether the answer was correct / partial / wrong / "don't know"
    - Exactly what to say aloud (coaching_note)
    - Whether to ask a follow-up, give a hint, correct them, or move to the next question
    - The exact follow-up question to ask (if needed)
    - Whether slang was detected (and how to redirect)
    - A score 1-10 with explanation (blends Claude quality + semantic similarity)

    You MUST act on the next_action field:
    - NEXT_QUESTION          → record_score then ask the next question from the bank
    - FOLLOW_UP              → ask the follow_up_question provided
    - CORRECT_AND_FOLLOW_UP  → say the coaching_note (which corrects them), then ask the follow_up_question
    - GIVE_HINT              → say the hint naturally, then wait for their next attempt
    - REDIRECT_THEN_CONTINUE → gently redirect to the question, accept any answer, then move on
    """
    from app.services.claude_strategy import ClaudeStrategyService

    evaluation = await ClaudeStrategyService.evaluate_answer(
        question=question_text,
        candidate_answer=candidate_answer,
        topic=topic,
        difficulty=difficulty,
        question_number=question_number,
        ideal_answer=ideal_answer,
    )

    logger.info(
        f"Answer evaluated: Q{question_number} | quality={evaluation.quality} "
        f"score={evaluation.score}/10 | next={evaluation.next_action}"
    )

    brief_lines = [
        f"=== ANSWER EVALUATION: Q{question_number} ===",
        f"Quality   : {evaluation.quality} ({evaluation.correctness_percent}% correct)",
        f"Score     : {evaluation.score}/10 — {evaluation.score_explanation}",
        f"Slang     : {'YES — redirect to professional language' if evaluation.slang_detected else 'No'}",
        "",
        f"WHAT WAS RIGHT : {evaluation.what_was_right or 'N/A'}",
        f"WHAT WAS WRONG : {evaluation.what_was_wrong or 'N/A'}",
        "",
        f"=== YOUR NEXT ACTION: {evaluation.next_action} ===",
        f"SAY THIS ALOUD : {evaluation.coaching_note}",
    ]

    if evaluation.next_action in ("FOLLOW_UP", "CORRECT_AND_FOLLOW_UP"):
        brief_lines.append(f"THEN ASK THIS  : {evaluation.follow_up_question}")
    elif evaluation.next_action == "GIVE_HINT":
        brief_lines.append(f"HINT TO GIVE   : {evaluation.hint}")
    elif evaluation.next_action == "NEXT_QUESTION":
        brief_lines.append(
            "THEN           : call record_score, then move to the next question in the bank."
        )

    return "\n".join(brief_lines)


# ---------------------------------------------------------------------------
# Scoring & session lifecycle
# ---------------------------------------------------------------------------

async def record_score(
    question_number: int,
    question_text: str,
    candidate_answer_summary: str,
    score: int,
    max_score: int,
    feedback: str,
    is_followup: bool = False,
    parent_question_number: Optional[int] = None,
) -> str:
    """
    Record the candidate's score for a question or follow-up.
    Call this AFTER evaluate_answer and AFTER you have spoken the coaching note.
    Do NOT call this before speaking — the candidate hears your coaching first.
    """
    logger.info(
        f"Score recorded: Q{question_number} = {score}/{max_score} "
        f"(follow-up={is_followup})"
    )

    session_id = _session_id_ctx.get()
    if session_id:
        from app.services.session_service import SessionService

        try:
            await SessionService.append_question_result(
                session_id,
                {
                    "question_number": question_number,
                    "question_text": question_text or "",
                    "user_answer": candidate_answer_summary or "",
                    "ideal_answer": "",
                    "score": int(score) if score is not None else 0,
                    "max_score": int(max_score) if max_score is not None else 10,
                    "feedback": feedback or "",
                    "filler_word_count": 0,
                    "emotion_log": {},
                    "is_followup": bool(is_followup),
                },
            )
        except Exception as exc:
            logger.error(
                f"record_score: failed to persist Q{question_number} "
                f"for session {session_id!r}: {exc}"
            )
    else:
        logger.warning(
            "record_score called without a session context — "
            "result will NOT be persisted. Check that _session_id_ctx is set "
            "in websocket.py before starting the ADK session."
        )

    return f"Score {score}/{max_score} recorded for question {question_number}."


async def get_score_table() -> str:
    """
    Retrieve the running score summary before delivering your closing verbal summary.
    Call this ONCE at the very end, just before signal_interview_end.
    """
    return "Score table retrieved. Use it to inform your closing verbal summary."


async def signal_interview_end(
    total_score: int,
    max_possible_score: int,
    overall_feedback: str,
    strengths: List[str],
    areas_for_improvement: List[str],
) -> str:
    """
    Signal that the interview is complete. Call this ONCE after your verbal closing summary.
    This triggers the report card screen for the candidate.
    """
    logger.info(
        f"Interview ended. Final score: {total_score}/{max_possible_score}"
    )

    ws = _websocket_ctx.get()
    if ws is not None:
        try:
            await ws.send_json(
                {
                    "type": "interview_end",
                    "data": {
                        "total_score": int(total_score) if total_score is not None else 0,
                        "max_possible_score": (
                            int(max_possible_score)
                            if max_possible_score is not None
                            else 0
                        ),
                        "overall_feedback": overall_feedback or "",
                        "strengths": list(strengths or []),
                        "areas_for_improvement": list(areas_for_improvement or []),
                    },
                }
            )
            logger.info("interview_end event dispatched to frontend via tool context")
        except Exception as exc:
            # The WS may already be closing — non-fatal, the event-stream
            # path in process_tool_results serves as the secondary attempt.
            logger.warning(
                f"signal_interview_end: WS send failed (connection may be closing): {exc}"
            )
    else:
        logger.warning(
            "signal_interview_end: WebSocket context not set — "
            "interview_end will be sent by process_tool_results fallback only."
        )

    return "Interview complete. Report card will be shown to the candidate."


async def request_screen_share() -> str:
    """
    Ask the candidate to share their screen (use before coding questions only).
    Say: 'For this one, go ahead and share your screen so I can follow along.'
    """
    logger.info("Screen share requested.")
    return "Screen share request sent to candidate."


async def stop_screen_share() -> str:
    """
    Stop screen sharing after a coding question + follow-up is complete.
    """
    logger.info("Screen share stopped.")
    return "Screen share stopped."


def get_interviewer_tools() -> List[Any]:
    return [
        evaluate_answer,
        record_score,
        get_score_table,
        signal_interview_end,
        request_screen_share,
        stop_screen_share,
    ]
