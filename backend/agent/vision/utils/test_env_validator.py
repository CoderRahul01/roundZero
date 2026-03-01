"""
Unit tests for environment validation utility.
"""

import os
import pytest
from unittest.mock import patch
from agent.vision.utils.env_validator import validate_environment, EnvironmentValidationError


class TestEnvironmentValidation:
    """Test suite for environment validation."""
    
    def test_validate_with_all_required_vars(self):
        """Test validation passes when all required variables are present."""
        env_vars = {
            # Core required
            "DATABASE_URL": "postgresql://test",
            "MONGODB_URI": "mongodb://test",
            "JWT_SECRET": "test-secret",
            # Vision Agents required
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_KEY": "test-api-key",
            "STREAM_API_SECRET": "test-api-secret",
            "GEMINI_API_KEY": "test-gemini-key",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            # Decision engine (at least one)
            "ANTHROPIC_API_KEY": "test-anthropic-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is True
            assert result["missing"] == []
    
    def test_validate_with_missing_core_vars(self):
        """Test validation fails when core variables are missing."""
        env_vars = {
            # Missing DATABASE_URL and MONGODB_URI
            "JWT_SECRET": "test-secret",
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_KEY": "test-api-key",
            "STREAM_API_SECRET": "test-api-secret",
            "GEMINI_API_KEY": "test-gemini-key",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is False
            assert "DATABASE_URL" in result["missing"]
            assert "MONGODB_URI" in result["missing"]
    
    def test_validate_with_missing_vision_vars(self):
        """Test validation fails when Vision Agents variables are missing."""
        env_vars = {
            "DATABASE_URL": "postgresql://test",
            "MONGODB_URI": "mongodb://test",
            "JWT_SECRET": "test-secret",
            # Missing STREAM_API_KEY and GEMINI_API_KEY
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_SECRET": "test-api-secret",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is False
            assert "STREAM_API_KEY" in result["missing"]
            assert "GEMINI_API_KEY" in result["missing"]
    
    def test_validate_with_missing_decision_engine(self):
        """Test validation fails when no decision engine is configured."""
        env_vars = {
            "DATABASE_URL": "postgresql://test",
            "MONGODB_URI": "mongodb://test",
            "JWT_SECRET": "test-secret",
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_KEY": "test-api-key",
            "STREAM_API_SECRET": "test-api-secret",
            "GEMINI_API_KEY": "test-gemini-key",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            # Missing both ANTHROPIC_API_KEY and GROQ_API_KEY
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is False
            assert "ANTHROPIC_API_KEY" in result["missing"] or "GROQ_API_KEY" in result["missing"]
    
    def test_validate_with_groq_as_decision_engine(self):
        """Test validation passes with GROQ_API_KEY instead of ANTHROPIC_API_KEY."""
        env_vars = {
            "DATABASE_URL": "postgresql://test",
            "MONGODB_URI": "mongodb://test",
            "JWT_SECRET": "test-secret",
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_KEY": "test-api-key",
            "STREAM_API_SECRET": "test-api-secret",
            "GEMINI_API_KEY": "test-gemini-key",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            # Using GROQ instead of ANTHROPIC
            "GROQ_API_KEY": "test-groq-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is True
            assert result["missing"] == []
    
    def test_validate_tracks_optional_missing_vars(self):
        """Test validation tracks missing optional variables."""
        env_vars = {
            # All required vars
            "DATABASE_URL": "postgresql://test",
            "MONGODB_URI": "mongodb://test",
            "JWT_SECRET": "test-secret",
            "STREAM_APP_ID": "test-app-id",
            "STREAM_API_KEY": "test-api-key",
            "STREAM_API_SECRET": "test-api-secret",
            "GEMINI_API_KEY": "test-gemini-key",
            "DEEPGRAM_API_KEY": "test-deepgram-key",
            "ELEVENLABS_API_KEY": "test-elevenlabs-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            # Missing optional vars
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            success, result = validate_environment()
            
            assert success is True
            assert "PINECONE_API_KEY" in result["optional_missing"]
            assert "SUPERMEMORY_API_KEY" in result["optional_missing"]
            assert "UPSTASH_REDIS_REST_URL" in result["optional_missing"]
