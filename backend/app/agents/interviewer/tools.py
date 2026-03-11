import logging
from typing import List, Any, Optional

from app.core.logger import logger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core strategic tool — Claude evaluates every answer, Aria acts on the result
# ---------------------------------------------------------------------------

async def evaluate_answer(
    question_number: int,
    question_text: str,
    candidate_answer: str,
    topic: str = "General",
    difficulty: str = "Medium",
) -> str:
    """
    CALL THIS IMMEDIATELY after the candidate finishes answering any question or follow-up.
    Claude will evaluate the answer and tell you exactly what to do next.

    Returns a structured coaching brief with:
    - Whether the answer was correct / partial / wrong / "don't know"
    - Exactly what to say aloud (coaching_note)
    - Whether to ask a follow-up, give a hint, correct them, or move to the next question
    - The exact follow-up question to ask (if needed)
    - Whether slang was detected (and how to redirect)
    - A score 1-10 with explanation

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
    )

    logger.info(
        f"Answer evaluated: Q{question_number} | quality={evaluation.quality} "
        f"score={evaluation.score}/10 | next={evaluation.next_action}"
    )

    # Build a clear brief for Aria to act on
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
        brief_lines.append("THEN           : call record_score, then move to the next question in the bank.")

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
    logger.info(f"Score recorded: Q{question_number} = {score}/{max_score} (follow-up={is_followup})")
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
    logger.info(f"Interview ended. Final score: {total_score}/{max_possible_score}")
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
