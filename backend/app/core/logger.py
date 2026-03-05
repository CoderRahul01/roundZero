import logging
import sys
from app.core.settings import get_settings

def setup_logger():
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    
    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.INFO)

    return logging.getLogger("roundzero")

logger = setup_logger()
