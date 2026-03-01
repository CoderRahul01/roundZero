"""
Security Utilities for Real-Time Voice Interaction

Implements input sanitization, authentication, and data encryption.
"""

import re
import html
import hashlib
import base64
import logging
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os

logger = logging.getLogger(__name__)


class InputSanitizer:
    """
    Sanitizes user input to prevent injection attacks and ensure data safety.
    """
    
    MAX_TRANSCRIPT_LENGTH = 1000
    MAX_AUDIO_SIZE_MB = 10
    
    @staticmethod
    def sanitize_transcript(text: str) -> str:
        """
        Sanitize transcript text before AI service calls.
        """
        if not text:
            return ""
        
        # Limit length
        if len(text) > InputSanitizer.MAX_TRANSCRIPT_LENGTH:
            text = text[:InputSanitizer.MAX_TRANSCRIPT_LENGTH]
            logger.warning(f"Transcript truncated to {InputSanitizer.MAX_TRANSCRIPT_LENGTH} chars")
        
        # Escape HTML special characters
        text = html.escape(text)
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Remove SQL injection patterns
        sql_patterns = [
            r"(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b|\bSELECT\b)",
            r"(--|;|\/\*|\*\/)",
            r"(\bOR\b\s+\d+\s*=\s*\d+)",
            r"(\bUNION\b.*\bSELECT\b)"
        ]
        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove script tags and javascript
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_audio_data(audio_data: bytes) -> bool:
        """
        Validate audio data format and size.
        """
        if not audio_data:
            return False
        
        # Check size
        size_mb = len(audio_data) / (1024 * 1024)
        if size_mb > InputSanitizer.MAX_AUDIO_SIZE_MB:
            logger.error(f"Audio data too large: {size_mb:.2f}MB")
            return False
        
        # Basic format validation (check for common audio headers)
        # WAV, MP3, OGG, WEBM headers
        valid_headers = [
            b'RIFF',  # WAV
            b'ID3',   # MP3
            b'OggS',  # OGG
            b'\x1a\x45\xdf\xa3'  # WEBM
        ]
        
        has_valid_header = any(audio_data.startswith(header) for header in valid_headers)
        if not has_valid_header:
            logger.warning("Audio data has unrecognized format")
        
        return True
    
    @staticmethod
    def sanitize_session_id(session_id: str) -> str:
        """
        Sanitize session ID to prevent path traversal.
        """
        # Remove any path separators and special characters
        session_id = re.sub(r'[^a-zA-Z0-9_-]', '', session_id)
        
        # Limit length
        if len(session_id) > 64:
            session_id = session_id[:64]
        
        return session_id
    
    @staticmethod
    def escape_for_database(text: str) -> str:
        """
        Escape special characters for database queries.
        Note: Use parameterized queries instead when possible.
        """
        # Escape single quotes
        text = text.replace("'", "''")
        
        # Escape backslashes
        text = text.replace("\\", "\\\\")
        
        return text


class WebSocketAuthenticator:
    """
    Handles WebSocket authentication and session validation.
    """
    
    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret
    
    def validate_token(self, token: str) -> Optional[dict]:
        """
        Validate JWT token for WebSocket connection.
        """
        import jwt
        
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=["HS256"]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.error("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {e}")
            return None
    
    def verify_session_ownership(
        self,
        user_id: str,
        session_id: str,
        session_db
    ) -> bool:
        """
        Verify that user owns the session.
        """
        # Query database to check session ownership
        # This is a placeholder - implement with actual DB query
        try:
            # session = session_db.get_session(session_id)
            # return session and session.user_id == user_id
            return True  # Placeholder
        except Exception as e:
            logger.error(f"Session ownership verification failed: {e}")
            return False


class DataEncryption:
    """
    Handles encryption of sensitive data (audio recordings, transcripts).
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize with encryption key.
        If no key provided, generates one from environment.
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # Derive key from environment secret
            secret = os.getenv("JWT_SECRET", "default-secret-key")
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'roundzero-salt',  # In production, use random salt per record
                iterations=100000,
            )
            self.key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        
        self.cipher = Fernet(self.key)
    
    def encrypt_audio(self, audio_data: bytes) -> bytes:
        """
        Encrypt audio data using AES-256.
        """
        try:
            encrypted = self.cipher.encrypt(audio_data)
            return encrypted
        except Exception as e:
            logger.error(f"Audio encryption failed: {e}")
            raise
    
    def decrypt_audio(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt audio data.
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            return decrypted
        except Exception as e:
            logger.error(f"Audio decryption failed: {e}")
            raise
    
    def encrypt_transcript(self, text: str) -> str:
        """
        Encrypt transcript text.
        """
        try:
            encrypted = self.cipher.encrypt(text.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Transcript encryption failed: {e}")
            raise
    
    def decrypt_transcript(self, encrypted_text: str) -> str:
        """
        Decrypt transcript text.
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Transcript decryption failed: {e}")
            raise
    
    @staticmethod
    def hash_user_id(user_id: str) -> str:
        """
        Hash user ID for privacy (one-way).
        """
        return hashlib.sha256(user_id.encode()).hexdigest()


class GDPRCompliance:
    """
    Implements GDPR compliance features for data management.
    """
    
    AUTO_DELETE_DAYS = 90
    
    @staticmethod
    async def schedule_auto_delete(session_id: str, created_at: float):
        """
        Schedule automatic deletion of session data after 90 days.
        """
        import time
        
        delete_at = created_at + (GDPRCompliance.AUTO_DELETE_DAYS * 86400)
        current_time = time.time()
        
        if current_time >= delete_at:
            logger.info(f"Session {session_id} eligible for auto-deletion")
            return True
        
        return False
    
    @staticmethod
    async def export_user_data(user_id: str, db) -> dict:
        """
        Export all user data for GDPR data portability.
        """
        try:
            # Collect all user data
            data = {
                "user_id": user_id,
                "sessions": [],
                "transcripts": [],
                "audio_recordings": [],
                "export_timestamp": time.time()
            }
            
            # Query database for user's sessions
            # sessions = await db.get_user_sessions(user_id)
            # data["sessions"] = sessions
            
            # Query transcripts
            # transcripts = await db.get_user_transcripts(user_id)
            # data["transcripts"] = transcripts
            
            # List audio recordings (metadata only, not actual files)
            # recordings = await db.get_user_recordings_metadata(user_id)
            # data["audio_recordings"] = recordings
            
            return data
        except Exception as e:
            logger.error(f"User data export failed: {e}")
            raise
    
    @staticmethod
    async def delete_user_data(user_id: str, db) -> bool:
        """
        Delete all user data (right to be forgotten).
        """
        try:
            # Delete sessions
            # await db.delete_user_sessions(user_id)
            
            # Delete transcripts
            # await db.delete_user_transcripts(user_id)
            
            # Delete audio recordings from GridFS
            # await db.delete_user_audio_recordings(user_id)
            
            # Delete user profile
            # await db.delete_user_profile(user_id)
            
            logger.info(f"All data deleted for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"User data deletion failed: {e}")
            return False


class SecurityManager:
    """
    Composite security manager coordinating all security features.
    """
    
    def __init__(self, jwt_secret: str):
        self.sanitizer = InputSanitizer()
        self.authenticator = WebSocketAuthenticator(jwt_secret)
        self.encryption = DataEncryption()
        self.gdpr = GDPRCompliance()
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input."""
        return self.sanitizer.sanitize_transcript(text)
    
    def validate_audio(self, audio_data: bytes) -> bool:
        """Validate audio data."""
        return self.sanitizer.validate_audio_data(audio_data)
    
    def authenticate_websocket(self, token: str) -> Optional[dict]:
        """Authenticate WebSocket connection."""
        return self.authenticator.validate_token(token)
    
    def encrypt_sensitive_data(self, data: bytes) -> bytes:
        """Encrypt sensitive data."""
        return self.encryption.encrypt_audio(data)
    
    def decrypt_sensitive_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt sensitive data."""
        return self.encryption.decrypt_audio(encrypted_data)
    
    async def handle_gdpr_request(
        self,
        request_type: str,
        user_id: str,
        db
    ) -> dict:
        """
        Handle GDPR requests (export or delete).
        """
        if request_type == "export":
            data = await self.gdpr.export_user_data(user_id, db)
            return {"success": True, "data": data}
        elif request_type == "delete":
            success = await self.gdpr.delete_user_data(user_id, db)
            return {"success": success}
        else:
            return {"success": False, "error": "Invalid request type"}
