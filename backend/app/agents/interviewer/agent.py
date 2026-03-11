from __future__ import annotations

from typing import List, Optional
import json

from google import adk
from app.agents.interviewer.super_prompt import get_full_prompt
from app.agents.interviewer.tools import get_interviewer_tools
from app.core.settings import get_settings


class InterviewerAgent(adk.Agent):
    """
    Aria — RoundZero's AI interviewer powered by Gemini 2.x Flash Live.
    Strategic answer evaluation is handled by Claude (via the evaluate_answer tool).
    """

    def __init__(
        self,
        mode: str = "buddy",
        user_profile: Optional[dict] = None,
        role: str = "Software Engineer",
        topics: List[str] = None,
        difficulty: str = "Medium",
        question_bank: List[dict] = None,
        session_id: str = "N/A",
        memory_context: str = "",
        **kwargs,
    ):
        settings = get_settings()

        instruction = get_full_prompt(mode=mode)

        instruction += "\n\n--- SESSION CONTEXT ---\n"
        instruction += f"Target Role : {role}\n"
        instruction += f"Topics      : {', '.join(topics) if topics else 'General'}\n"
        instruction += f"Difficulty  : {difficulty}\n"
        instruction += f"Session ID  : {session_id}\n"

        if question_bank:
            instruction += f"\n--- QUESTION BANK (use these, do not improvise) ---\n{json.dumps(question_bank, indent=2)}\n"

        if user_profile:
            name = user_profile.get("full_name") or user_profile.get("name", "the candidate")
            instruction += f"\n--- CANDIDATE PROFILE ---\nName: {name}\n"

        if memory_context:
            instruction += f"\n--- CANDIDATE MEMORY (past sessions) ---\n{memory_context}\n"

        super().__init__(
            name="interviewer",
            model=settings.gemini_model,
            instruction=instruction,
            tools=get_interviewer_tools(),
        )


async def create_interviewer(
    mode: str = "buddy",
    user_profile: Optional[dict] = None,
    role: str = "Software Engineer",
    topics: List[str] = None,
    difficulty: str = "Medium",
    question_bank: List[dict] = None,
    session_id: str = "N/A",
) -> InterviewerAgent:
    from app.services.supermemory_service import SupermemoryService

    memory_context = ""
    if user_profile and user_profile.get("id"):
        memory_context = await SupermemoryService.get_user_memory(user_profile["id"])

    return InterviewerAgent(
        mode=mode,
        user_profile=user_profile,
        memory_context=memory_context,
        role=role,
        topics=topics,
        difficulty=difficulty,
        question_bank=question_bank,
        session_id=session_id,
    )
