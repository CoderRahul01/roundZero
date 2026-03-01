"""
Environment validation utility for Vision Agents integration.

This module validates that all required environment variables are present
on application startup and logs clear error messages for missing variables.
"""

import logging
import os
import sys
from typing import Dict, List, Tuple

logger = logging.getLogger("roundzero.env_validator")


class EnvironmentValidationError(Exception):
    """Raised when required environment variables are missing."""
    pass


def validate_environment() -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate all required environment variables for Vision Agents integration.
    
    Returns:
        Tuple[bool, Dict[str, List[str]]]: 
            - Success status (True if all required vars present)
            - Dictionary with 'missing' and 'optional_missing' lists
    
    Raises:
        EnvironmentValidationError: If critical environment variables are missing
    """
    # Core required variables
    core_required = [
        "DATABASE_URL",
        "MONGODB_URI",
        "JWT_SECRET",
    ]
    
    # Vision Agents required variables
    vision_required = [
        "STREAM_APP_ID",
        "STREAM_API_KEY",
        "STREAM_API_SECRET",
        "GEMINI_API_KEY",
        "DEEPGRAM_API_KEY",
        "ELEVENLABS_API_KEY",
    ]
    
    # At least one decision engine required
    decision_engines = ["ANTHROPIC_API_KEY", "GROQ_API_KEY"]
    
    # Optional but recommended variables
    optional_vars = [
        "PINECONE_API_KEY",
        "SUPERMEMORY_API_KEY",
        "UPSTASH_REDIS_REST_URL",
        "UPSTASH_REDIS_REST_TOKEN",
    ]
    
    # Check core required variables
    missing_core = [var for var in core_required if not os.getenv(var)]
    
    # Check Vision Agents required variables
    missing_vision = [var for var in vision_required if not os.getenv(var)]
    
    # Check decision engine (at least one required)
    has_decision_engine = any(os.getenv(var) for var in decision_engines)
    missing_decision = [] if has_decision_engine else decision_engines
    
    # Check optional variables
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    
    # Combine all missing required variables
    all_missing_required = missing_core + missing_vision + missing_decision
    
    # Log results
    if all_missing_required:
        logger.error("=" * 80)
        logger.error("ENVIRONMENT VALIDATION FAILED")
        logger.error("=" * 80)
        logger.error("")
        logger.error("The following REQUIRED environment variables are missing:")
        logger.error("")
        
        if missing_core:
            logger.error("Core Configuration:")
            for var in missing_core:
                logger.error(f"  ❌ {var}")
            logger.error("")
        
        if missing_vision:
            logger.error("Vision Agents Integration:")
            for var in missing_vision:
                logger.error(f"  ❌ {var}")
            logger.error("")
        
        if missing_decision:
            logger.error("Decision Engine (at least one required):")
            for var in missing_decision:
                logger.error(f"  ❌ {var}")
            logger.error("")
        
        logger.error("Please set these variables in your .env file or environment.")
        logger.error("See backend/ENVIRONMENT_VARIABLES.md for detailed documentation.")
        logger.error("See backend/.env.example for template.")
        logger.error("")
        logger.error("=" * 80)
        
        return False, {
            "missing": all_missing_required,
            "optional_missing": missing_optional
        }
    
    # Log success
    logger.info("✅ Environment validation passed - all required variables present")
    
    # Log optional missing variables as warnings
    if missing_optional:
        logger.warning("Optional environment variables not set (features may be limited):")
        for var in missing_optional:
            logger.warning(f"  ⚠️  {var}")
    
    return True, {
        "missing": [],
        "optional_missing": missing_optional
    }


def validate_and_exit_on_failure() -> None:
    """
    Validate environment and exit application if validation fails.
    
    This function should be called during application startup to ensure
    all required environment variables are present before proceeding.
    """
    success, result = validate_environment()
    
    if not success:
        logger.error("Application cannot start with missing required environment variables.")
        logger.error("Exiting...")
        sys.exit(1)
    
    logger.info("Environment validation successful - application starting...")
