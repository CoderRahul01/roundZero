from pydantic import BaseModel
from typing import List, Optional

class StartSessionPayload(BaseModel):
    user_id: Optional[str] = None
    role: str
    topics: List[str]
    difficulty: str
    mode: str = "buddy"

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
    user_id: str
    name: Optional[str] = None
    bio: Optional[str] = None
    resume_text: Optional[str] = None
    experience_level: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
