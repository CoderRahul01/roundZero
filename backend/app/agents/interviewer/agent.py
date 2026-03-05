from __future__ import annotations

from typing import List, Optional

from google import adk
from app.agents.interviewer.prompts import INTERVIEW_PERSONAS, DEFAULT_SYSTEM_INSTRUCTION
from app.agents.interviewer.tools import get_interviewer_tools
from app.core.settings import get_settings

class InterviewerAgent(adk.Agent):
    """
    RoundZero Interviewer Agent powered by Gemini 2.0 Flash Live.
    Handles multimodal (audio/video) interview sessions.
    """
    
    def __init__(
        self, 
        mode: str = "behavioral", 
        user_profile: Optional[dict] = None, 
        memory_context: str = "",
        role: str = "Software Engineer",
        topics: List[str] = None,
        difficulty: str = "Medium",
        **kwargs
    ):
        settings = get_settings()
        
        # Select persona prompt
        persona_instruction = INTERVIEW_PERSONAS.get(mode, INTERVIEW_PERSONAS["behavioral"])
        
        # Build core instruction
        full_instruction = f"{DEFAULT_SYSTEM_INSTRUCTION}\n\n"
        full_instruction += f"--- INTERVIEW CONTEXT ---\n"
        full_instruction += f"Mode: {mode}\n"
        full_instruction += f"Target Role: {role}\n"
        full_instruction += f"Topics: {', '.join(topics) if topics else 'N/A'}\n"
        full_instruction += f"Difficulty: {difficulty}\n"
        full_instruction += f"-------------------------\n\n"
        full_instruction += f"PERSONA: {persona_instruction}"
        
        # Ingest user profile metadata for personalization
        if user_profile:
            profile_context = "\n\n--- CANDIDATE PROFILE ---\n"
            profile_context += f"Name: {user_profile.get('full_name') or user_profile.get('name', 'Not provided')}\n"
            profile_context += f"Bio: {user_profile.get('bio', 'Not provided')}\n"
            profile_context += f"Experience Level: {user_profile.get('experience_level', 'Not provided')}\n"
            if user_profile.get("skills"):
                profile_context += f"Skills: {', '.join(user_profile.get('skills', [])) if isinstance(user_profile.get('skills'), list) else user_profile.get('skills')}\n"
            profile_context += "-------------------------\n"
            full_instruction += profile_context
            
        # Add past interview memory if available
        if memory_context:
            full_instruction += f"\n\n--- PAST INTERVIEW MEMORY ---\n{memory_context}\n-----------------------------\n"

        # ADK Agent: pass the model as a string ID (per ADK quickstart).
        # speech_config and response_modalities are set in RunConfig (websocket.py),
        # not here — setting them in both causes conflicts.
        # ADK reads GOOGLE_API_KEY and GOOGLE_GENAI_USE_VERTEXAI directly from env.
        super().__init__(
            name="interviewer",
            model=settings.gemini_model,   # e.g. "gemini-2.5-flash-native-audio-latest"
            instruction=full_instruction,
            tools=get_interviewer_tools(),
        )
        
    async def on_user_event(self, event: adk.UserEvent):
        """Handler for specific user events if needed beyond standard bidi flow."""
        # Custom logic for explicit triggers could go here
        pass

# Factory for creating agents
async def create_interviewer(
    mode: str = "behavioral", 
    user_profile: Optional[dict] = None,
    role: str = "Software Engineer",
    topics: List[str] = None,
    difficulty: str = "Medium"
) -> InterviewerAgent:
    from app.services.supermemory_service import SupermemoryService
    
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
        difficulty=difficulty
    )
