import httpx
from typing import Optional, List
from app.core.settings import get_settings
from app.core.logger import logger

class SupermemoryService:
    """Service for interacting with Supermemory AI for persistent user context."""
    
    BASE_URL = "https://api.supermemory.ai/v1"
    
    @classmethod
    async def get_user_memory(cls, user_id: str) -> str:
        """Fetch past interview context/summaries for a user."""
        settings = get_settings()
        if not settings.supermemory_api_key or not settings.use_supermemory:
            return ""
            
        try:
            async with httpx.AsyncClient() as client:
                # Assuming standard Supermemory retrieval endpoint
                response = await client.get(
                    f"{cls.BASE_URL}/memory",
                    params={"user_id": user_id},
                    headers={"Authorization": f"Bearer {settings.supermemory_api_key}"}
                )
                if response.status_code == 200:
                    data = response.json()
                    # Expecting a summary string or list of items to join
                    return data.get("summary", "")
                return ""
        except Exception as e:
            logger.error(f"Error fetching from Supermemory: {e}")
            return ""

    @classmethod
    async def save_session_summary(cls, user_id: str, summary: str):
        """Save the current session summary to Supermemory."""
        settings = get_settings()
        if not settings.supermemory_api_key or not settings.use_supermemory:
            return
            
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{cls.BASE_URL}/memory",
                    json={
                        "user_id": user_id,
                        "content": summary,
                        "metadata": {"type": "interview_summary", "timestamp": "now"}
                    },
                    headers={"Authorization": f"Bearer {settings.supermemory_api_key}"}
                )
        except Exception as e:
            logger.error(f"Error saving to Supermemory: {e}")
