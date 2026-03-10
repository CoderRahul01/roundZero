import logging
import json
import sys
import os
from datetime import datetime
from app.core.settings import get_settings

class GCPStructuredFormatter(logging.Formatter):
    """
    Formats logs as single-line JSON strings compatible with Google Cloud Logging.
    This ensures Cloud Run / GCP Logs Explorer parses severity and metadata correctly.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Map Python log levels to GCP Severities
        severity_map = {
            'DEBUG': 'DEBUG',
            'INFO': 'INFO',
            'WARNING': 'WARNING',
            'ERROR': 'ERROR',
            'CRITICAL': 'CRITICAL'
        }
        
        log_entry = {
            'severity': severity_map.get(record.levelname, 'DEFAULT'),
            'message': record.getMessage(),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'logging.googleapis.com/labels': {
                'module': record.module,
                'logger': record.name
            }
        }
        
        if record.exc_info:
            log_entry['exceptions'] = self.formatException(record.exc_info)
            
        # Include custom extra fields if provided
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)
            
        return json.dumps(log_entry)

def setup_gcp_logger(name: str = "app") -> logging.Logger:
    """
    Configures and returns a logger that outputs GCP-compatible structured JSON.
    Only enables JSON formatting if running in a Cloud Run environment 
    (detected via K_SERVICE env var) to keep local dev logs readable.
    """
    logger = logging.getLogger(name)
    settings = get_settings()
    
    # Do not reconfigure if handlers already exist
    if not logger.handlers:
        logger.setLevel(settings.log_level.upper())
        handler = logging.StreamHandler(sys.stdout)
        
        # If running in Google Cloud Run (K_SERVICE is populated by GCP)
        if os.getenv('K_SERVICE'):
            handler.setFormatter(GCPStructuredFormatter())
        else:
            # Local development fallback
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
        logger.addHandler(handler)
        
    return logger

# Global default GCP logger instance
gcp_logger = setup_gcp_logger()
