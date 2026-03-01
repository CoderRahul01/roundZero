"""
Unit tests for MongoDB Question Repository.

Tests connection handling, query methods, and GridFS operations.
"""

import pytest
import pytest_asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.mongo_repository import MongoQuestionRepository, Question
from settings import get_settings


@pytest_asyncio.fixture
async def mongo_repo():
    """Fixture to create and cleanup MongoDB repository."""
    settings = get_settings()
    
    if not settings.mongodb_uri:
        pytest.skip("MongoDB URI not configured")
    
    repo = MongoQuestionRepository(
        connection_uri=settings.mongodb_uri,
        database_name="RoundZero_Test"  # Use test database
    )
    
    yield repo
    
    # Cleanup
    await repo.close()


@pytest.mark.asyncio
async def test_mongo_connection(mongo_repo):
    """Test MongoDB connection with ping."""
    is_connected = await mongo_repo.ping()
    assert is_connected is True, "MongoDB connection failed"


@pytest.mark.asyncio
async def test_get_by_id_not_found(mongo_repo):
    """Test getting a question by ID that doesn't exist."""
    question = await mongo_repo.get_by_id("nonexistent_id", category="software")
    assert question is None, "Should return None for non-existent question"


@pytest.mark.asyncio
async def test_get_all_empty(mongo_repo):
    """Test getting all questions from empty collection."""
    questions = await mongo_repo.get_all(category="software", limit=10)
    assert isinstance(questions, list), "Should return a list"
    # Note: May be empty if no data migrated yet


@pytest.mark.asyncio
async def test_get_questions_by_category(mongo_repo):
    """Test getting questions by category and difficulty."""
    questions = await mongo_repo.get_questions_by_category(
        category="software",
        difficulty="medium",
        limit=5
    )
    assert isinstance(questions, list), "Should return a list"
    
    # Validate question structure if any returned
    for question in questions:
        assert isinstance(question, Question), "Should return Question objects"
        assert question.difficulty == "medium", "Should match difficulty filter"


@pytest.mark.asyncio
async def test_get_questions_by_topics(mongo_repo):
    """Test getting questions by topics."""
    questions = await mongo_repo.get_questions_by_topics(
        topics=["python", "algorithms"],
        difficulty="medium",
        limit=5
    )
    assert isinstance(questions, list), "Should return a list"
    
    # Validate question structure if any returned
    for question in questions:
        assert isinstance(question, Question), "Should return Question objects"
        assert any(topic in question.topics for topic in ["python", "algorithms"]), \
            "Should match at least one topic"


@pytest.mark.asyncio
async def test_search_questions(mongo_repo):
    """Test full-text search across questions."""
    questions = await mongo_repo.search_questions(
        query="algorithm",
        limit=5
    )
    assert isinstance(questions, list), "Should return a list"
    
    # Validate question structure if any returned
    for question in questions:
        assert isinstance(question, Question), "Should return Question objects"


@pytest.mark.asyncio
async def test_create_indexes(mongo_repo):
    """Test index creation on collections."""
    # Should not raise any exceptions
    await mongo_repo.create_indexes()


@pytest.mark.asyncio
async def test_audio_storage_and_retrieval(mongo_repo):
    """Test storing and retrieving audio from GridFS."""
    # Create test audio data
    test_audio = b"fake_audio_data_for_testing"
    filename = "test_audio.wav"
    metadata = {
        "session_id": "test_session_123",
        "question_index": 1,
        "duration": 5.5,
        "timestamp": "2025-01-01T00:00:00Z"
    }
    
    # Store audio
    file_id = await mongo_repo.store_audio_recording(
        audio_data=test_audio,
        filename=filename,
        metadata=metadata
    )
    
    assert file_id is not None, "Should return file_id"
    assert isinstance(file_id, str), "file_id should be a string"
    
    # Retrieve audio
    retrieved_audio = await mongo_repo.get_audio_recording(file_id)
    assert retrieved_audio == test_audio, "Retrieved audio should match original"
    
    # Cleanup - delete audio
    await mongo_repo.delete_audio_recording(file_id)


@pytest.mark.asyncio
async def test_audio_streaming(mongo_repo):
    """Test streaming audio from GridFS."""
    # Create test audio data
    test_audio = b"fake_audio_data_for_streaming_test"
    filename = "test_stream_audio.wav"
    metadata = {
        "session_id": "test_session_456",
        "question_index": 2,
        "duration": 3.2,
        "timestamp": "2025-01-01T00:00:00Z"
    }
    
    # Store audio
    file_id = await mongo_repo.store_audio_recording(
        audio_data=test_audio,
        filename=filename,
        metadata=metadata
    )
    
    # Stream audio
    chunks = []
    async for chunk in mongo_repo.stream_audio_recording(file_id):
        chunks.append(chunk)
    
    # Verify streamed data matches original
    streamed_audio = b"".join(chunks)
    assert streamed_audio == test_audio, "Streamed audio should match original"
    
    # Cleanup
    await mongo_repo.delete_audio_recording(file_id)


@pytest.mark.asyncio
async def test_connection_pooling(mongo_repo):
    """Test that connection pooling is configured correctly."""
    # Verify client configuration
    assert mongo_repo.client.options.pool_options.max_pool_size == 50
    assert mongo_repo.client.options.pool_options.min_pool_size == 10
    assert mongo_repo.client.options.server_selection_timeout == 5.0
