import logging
from typing import Optional
from app.core.settings import get_settings
from app.core.logger import logger
import asyncpg

class UserService:
    """Service for managing user profiles in Postgres."""
    
    @staticmethod
    async def get_profile(user_id: str) -> Optional[dict]:
        """Fetch user profile from Neon."""
        settings = get_settings()
        if not settings.database_url:
            logger.error("DATABASE_URL not configured")
            return None
            
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                row = await conn.fetchrow(
                    "SELECT id, full_name, bio, resume_url, skills, experience_level FROM user_profiles WHERE id = $1",
                    user_id
                )
                if row:
                    return dict(row)
                return None
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return None

    @staticmethod
    async def upsert_user_profile(user_id: str, profile_data: dict) -> bool:
        """Create or update user profile."""
        settings = get_settings()
        try:
            conn = await asyncpg.connect(settings.database_url)
            try:
                await conn.execute(
                    """
                    INSERT INTO user_profiles (id, full_name, bio, resume_url, skills, experience_level, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, now())
                    ON CONFLICT (id) DO UPDATE SET
                        full_name = EXCLUDED.full_name,
                        bio = EXCLUDED.bio,
                        resume_url = EXCLUDED.resume_url,
                        skills = EXCLUDED.skills,
                        experience_level = EXCLUDED.experience_level,
                        updated_at = now()
                    """,
                    user_id,
                    profile_data.get("full_name"),
                    profile_data.get("bio"),
                    profile_data.get("resume_url"),
                    profile_data.get("skills"),
                    profile_data.get("experience_level")
                )
                return await UserService.get_profile(user_id)
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error upserting user profile: {e}")
            return False
