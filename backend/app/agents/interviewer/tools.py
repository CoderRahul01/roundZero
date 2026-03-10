print("  Importing typing...", flush=True)
from typing import List, Dict, Any, Optional
print("  Importing uuid...", flush=True)
import uuid
print("  Importing app.core.logger...", flush=True)
from app.core.logger import logger
print("  Importing app.core.settings...", flush=True)
from app.core.settings import get_settings
print("  Importing google.genai...", flush=True)
from google import genai
print("  Importing google.genai.types...", flush=True)
from google.genai import types
print("  Importing app.services.question_service...", flush=True)
from app.services.session_service import SessionService

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
    Tool to record the candidate's score for a question or follow-up.
    The interviewer MUST call this after every single answer.
    """
    logger.info(f"Score recorded: Q{question_number} = {score}/{max_score} (Follow-up: {is_followup})")
    return f"Score of {score} recorded for question {question_number}."

async def get_score_table() -> str:
    """
    Retrieve the current score table to review before giving closing summary.
    Call this ONCE during the closing phase, before your verbal summary.
    """
    return "Score table retrieved. Review candidate performance before final summary."

async def signal_interview_end(
    total_score: int,
    max_possible_score: int,
    overall_feedback: str,
    strengths: List[str],
    areas_for_improvement: List[str],
) -> str:
    """
    Signal that the interview is complete and provide the final report card.
    Call this ONCE at the very end, after your verbal closing summary.
    """
    logger.info(f"Interview ended. Final Score: {total_score}/{max_possible_score}")
    return "Interview complete signal sent."

async def request_screen_share() -> str:
    """
    Tool to request screen sharing for coding questions.
    """
    logger.info("Screen share requested by agent.")
    return "Screen share request sent to candidate."

async def stop_screen_share() -> str:
    """
    Tool to signal that screen share is no longer needed.
    """
    logger.info("Screen share stop requested by agent.")
    return "Screen share stopped."

def get_interviewer_tools() -> List[Any]:
    """Wraps tools for ADK consumption."""
    return [
        record_score,
        get_score_table,
        signal_interview_end,
        request_screen_share,
        stop_screen_share,
    ]
