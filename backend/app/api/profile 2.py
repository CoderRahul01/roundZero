from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas import UserProfileSchema
from app.services.user_service import UserService
from app.core.middleware import get_current_user
from app.core.logger import logger

router = APIRouter(prefix="/profile", tags=["Profile"])

@router.get("/", response_model=UserProfileSchema)
async def get_profile(user_id: str = Depends(get_current_user)):
    """
    Fetches the profile for the authenticated user.
    """
    try:
        profile = await UserService.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", response_model=UserProfileSchema)
async def update_profile(profile_data: UserProfileSchema, user_id: str = Depends(get_current_user)):
    """
    Updates or creates a profile for the authenticated user.
    """
    try:
        # Convert schema to dict for service
        data = profile_data.dict(exclude_unset=True)
        updated_profile = await UserService.upsert_user_profile(user_id, data)
        return updated_profile
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
