from fastapi import APIRouter, HTTPException, Request
from app.api.schemas import UserProfileSchema
from app.services.user_service import UserService
from app.core.logger import logger

router = APIRouter()

@router.get("/profile/", response_model=UserProfileSchema)
async def get_profile(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = user.get("sub") or user.get("user_id")
    try:
        profile = await UserService.get_profile(user_id)
        if not profile:
            # Return empty shell
            return UserProfileSchema(user_id=user_id)
        
        # Map database fields to schema fields
        return UserProfileSchema(
            user_id=str(profile.get("id")),
            name=profile.get("full_name"),
            bio=profile.get("bio"),
            resume_text=profile.get("resume_url"), # Mapping resume_url to resume_text as placeholder
            experience_level=profile.get("experience_level"),
            strengths=profile.get("skills"), # Mapping skills to strengths as placeholder
            weaknesses=[]
        )
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/profile/", response_model=UserProfileSchema)
async def update_profile(payload: dict, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_id = user.get("sub") or user.get("user_id")
    try:
        service = UserService()
        logger.info(f"Updating profile for user {user_id}")
        profile = await service.upsert_user_profile(user_id, payload)
        
        # Map database fields to schema fields
        return UserProfileSchema(
            user_id=str(profile.get("id")),
            name=profile.get("full_name"),
            bio=profile.get("bio"),
            resume_text=profile.get("resume_url"),
            experience_level=profile.get("experience_level"),
            strengths=profile.get("skills"),
            weaknesses=[]
        )
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
