from typing import List, Optional
from pydantic import BaseModel
from app.api.api_types import InterviewMode, Difficulty

class StartSessionPayload(BaseModel):
    user_id: Optional[str] = None
    name: Optional[str] = None
    role: str
    topics: List[str]
    difficulty: Difficulty
    mode: InterviewMode

class StartSessionResponse(BaseModel):
    session_id: str
    user_id: str
    first_question: str
    question_index: int
    total_questions: int
    memory_context: str
    call_id: str
    token: Optional[str] = None
    backend_token: Optional[str] = None
    stream_api_key: Optional[str] = None
class UserProfileSchema(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
