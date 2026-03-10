from __future__ import annotations

from typing import List, Optional
import json

from google import adk
from google.adk.agents import LlmAgent
from app.agents.interviewer.prompts import INTERVIEW_PERSONAS, DEFAULT_SYSTEM_INSTRUCTION
from app.agents.interviewer.tools import get_interviewer_tools
from app.core.settings import get_settings

from app.agents.interviewer.super_prompt import get_full_prompt

class InterviewerAgent(adk.Agent):
    """
    RoundZero Interviewer Agent powered by Gemini 2.0 Flash Live.
    Handles multimodal (audio/video) interview sessions.
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
        **kwargs
    ):
        settings = get_settings()
        
        # Get modular prompt from super_prompt.py
        full_instruction = get_full_prompt(mode=mode)
        
        # Add dynamic context (role, topics, questions) to the base instruction
        full_instruction += "\n\n--- DYNAMIC CONTEXT ---\n"
        full_instruction += f"Target Role: {role}\n"
        full_instruction += f"Topics: {', '.join(topics) if topics else 'N/A'}\n"
        full_instruction += f"Difficulty: {difficulty}\n"
        full_instruction += f"Session ID: {session_id}\n"
        
        if question_bank:
            questions_text = json.dumps(question_bank, indent=2)
            full_instruction += f"\n--- QUESTION BANK ---\n{questions_text}\n"

        if user_profile:
            profile_context = f"\n--- CANDIDATE PROFILE ---\nName: {user_profile.get('full_name') or user_profile.get('name', 'N/A')}\n"
            full_instruction += profile_context

        # Create the Strategy Agent ("The Brain")
        strategy_agent = LlmAgent(
            model="gemini-2.0-flash", 
            name="strategy_agent",
            instruction="""You are the interview strategy brain. 
            Given the conversation history and candidate's response, decide:
            1. Was the answer correct/partial/wrong?
            2. Should we ask a follow-up or move on based on the question bank?
            3. What specific hint or feedback should the interviewer provide?
            """,
        )

        super().__init__(
            name="interviewer",
            model=settings.gemini_model,
            instruction=full_instruction,
            tools=get_interviewer_tools(),
            sub_agents=[strategy_agent]
        )

# Factory for creating agents
async def create_interviewer(
    mode: str = "buddy", 
    user_profile: Optional[dict] = None,
    role: str = "Software Engineer",
    topics: List[str] = None,
    difficulty: str = "Medium",
    question_bank: List[dict] = None,
    session_id: str = "N/A"
) -> InterviewerAgent:
    from app.services.supermemory_service import SupermemoryService
    import json
    
    # 1. Retrieve past memory from Supermemory if user_profile exists
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
        session_id=session_id
    )
