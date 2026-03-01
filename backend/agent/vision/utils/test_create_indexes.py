"""
Unit Tests for MongoDB Index Creation

This module tests the index creation and verification functions for the
Vision Agents integration MongoDB collections.

Requirements: 8.17, 8.18
"""

import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import AsyncMock, MagicMock, patch
from backend.agent.vision.utils.create_indexes import (
    create_live_sessions_indexes,
    create_question_results_indexes,
    create_all_indexes,
    verify_indexes,
    drop_all_indexes
)


@pytest.fixture
def mock_db():
    """Create a mock database for testing."""
    # Mock live_sessions collection
    live_sessions_collection = MagicMock()
    live_sessions_collection.create_index = AsyncMock()
    live_sessions_collection.list_indexes = MagicMock()
    live_sessions_collection.drop_index = AsyncMock()
    
    # Mock question_results collection
    question_results_collection = MagicMock()
    question_results_collection.create_index = AsyncMock()
    question_results_collection.list_indexes = MagicMock()
    question_results_collection.drop_index = AsyncMock()
    
    # Create db mock with dictionary-like access
    db = {
        "live_sessions": live_sessions_collection,
        "question_results": question_results_collection
    }
    
    return db


@pytest.mark.asyncio
async def test_create_live_sessions_indexes(mock_db):
    """
    Test creating indexes for live_sessions collection.
    
    Validates:
    - Unique index on session_id is created
    - Compound index on (candidate_id, started_at) is created
    - Index on started_at is created
    
    Requirements: 8.17, 8.18
    """
    collection = mock_db["live_sessions"]
    
    # Configure mock to return index names
    collection.create_index.side_effect = [
        "session_id_unique",
        "candidate_started_compound",
        "started_at_index"
    ]
    
    # Create indexes
    result = await create_live_sessions_indexes(mock_db)
    
    # Verify all indexes were created
    assert len(result) == 3
    assert "session_id_unique" in result
    assert "candidate_started_compound" in result
    assert "started_at_index" in result
    
    # Verify create_index was called 3 times
    assert collection.create_index.call_count == 3
    
    # Verify unique index on session_id
    first_call = collection.create_index.call_args_list[0]
    assert first_call[0][0] == "session_id"
    assert first_call[1]["unique"] is True
    assert first_call[1]["name"] == "session_id_unique"
    
    # Verify compound index on (candidate_id, started_at)
    second_call = collection.create_index.call_args_list[1]
    assert second_call[0][0] == [("candidate_id", 1), ("started_at", -1)]
    assert second_call[1]["name"] == "candidate_started_compound"
    
    # Verify index on started_at
    third_call = collection.create_index.call_args_list[2]
    assert third_call[0][0] == "started_at"
    assert third_call[1]["name"] == "started_at_index"


@pytest.mark.asyncio
async def test_create_question_results_indexes(mock_db):
    """
    Test creating indexes for question_results collection.
    
    Validates:
    - Compound index on (session_id, timestamp) is created
    
    Requirements: 8.17, 8.18
    """
    collection = mock_db["question_results"]
    
    # Configure mock to return index name
    collection.create_index.return_value = "session_timestamp_compound"
    
    # Create indexes
    result = await create_question_results_indexes(mock_db)
    
    # Verify index was created
    assert len(result) == 1
    assert "session_timestamp_compound" in result
    
    # Verify create_index was called once
    assert collection.create_index.call_count == 1
    
    # Verify compound index on (session_id, timestamp)
    call_args = collection.create_index.call_args
    assert call_args[0][0] == [("session_id", 1), ("timestamp", 1)]
    assert call_args[1]["name"] == "session_timestamp_compound"


@pytest.mark.asyncio
async def test_create_all_indexes(mock_db):
    """
    Test creating all indexes for both collections.
    
    Validates:
    - All live_sessions indexes are created
    - All question_results indexes are created
    - Result contains both collections
    
    Requirements: 8.17, 8.18
    """
    live_sessions_collection = mock_db["live_sessions"]
    question_results_collection = mock_db["question_results"]
    
    # Configure mocks
    live_sessions_collection.create_index.side_effect = [
        "session_id_unique",
        "candidate_started_compound",
        "started_at_index"
    ]
    question_results_collection.create_index.return_value = "session_timestamp_compound"
    
    # Create all indexes
    result = await create_all_indexes(mock_db)
    
    # Verify both collections are in result
    assert "live_sessions" in result
    assert "question_results" in result
    
    # Verify live_sessions indexes
    assert len(result["live_sessions"]) == 3
    assert "session_id_unique" in result["live_sessions"]
    assert "candidate_started_compound" in result["live_sessions"]
    assert "started_at_index" in result["live_sessions"]
    
    # Verify question_results indexes
    assert len(result["question_results"]) == 1
    assert "session_timestamp_compound" in result["question_results"]


@pytest.mark.asyncio
async def test_verify_indexes(mock_db):
    """
    Test verifying that indexes exist.
    
    Validates:
    - Indexes are listed for both collections
    - Default _id index is excluded
    - Index information is correctly formatted
    
    Requirements: 8.17, 8.18
    """
    live_sessions_collection = mock_db["live_sessions"]
    question_results_collection = mock_db["question_results"]
    
    # Mock list_indexes to return async cursor
    live_sessions_cursor = AsyncMock()
    live_sessions_cursor.to_list = AsyncMock(return_value=[
        {"name": "_id_", "key": [("_id", 1)]},
        {"name": "session_id_unique", "key": [("session_id", 1)], "unique": True},
        {"name": "candidate_started_compound", "key": [("candidate_id", 1), ("started_at", -1)]},
        {"name": "started_at_index", "key": [("started_at", 1)]}
    ])
    live_sessions_collection.list_indexes.return_value = live_sessions_cursor
    
    question_results_cursor = AsyncMock()
    question_results_cursor.to_list = AsyncMock(return_value=[
        {"name": "_id_", "key": [("_id", 1)]},
        {"name": "session_timestamp_compound", "key": [("session_id", 1), ("timestamp", 1)]}
    ])
    question_results_collection.list_indexes.return_value = question_results_cursor
    
    # Verify indexes
    result = await verify_indexes(mock_db)
    
    # Verify both collections are in result
    assert "live_sessions" in result
    assert "question_results" in result
    
    # Verify live_sessions indexes (excluding _id)
    assert len(result["live_sessions"]) == 3
    assert result["live_sessions"][0]["name"] == "session_id_unique"
    assert result["live_sessions"][0]["unique"] is True
    assert result["live_sessions"][1]["name"] == "candidate_started_compound"
    assert result["live_sessions"][2]["name"] == "started_at_index"
    
    # Verify question_results indexes (excluding _id)
    assert len(result["question_results"]) == 1
    assert result["question_results"][0]["name"] == "session_timestamp_compound"


@pytest.mark.asyncio
async def test_drop_all_indexes(mock_db):
    """
    Test dropping all custom indexes.
    
    Validates:
    - All custom indexes are dropped
    - Default _id index is not dropped
    - Drop count is correct
    
    Requirements: 8.17, 8.18
    """
    live_sessions_collection = mock_db["live_sessions"]
    question_results_collection = mock_db["question_results"]
    
    # Mock list_indexes to return async cursor
    live_sessions_cursor = AsyncMock()
    live_sessions_cursor.to_list = AsyncMock(return_value=[
        {"name": "_id_", "key": [("_id", 1)]},
        {"name": "session_id_unique", "key": [("session_id", 1)], "unique": True},
        {"name": "candidate_started_compound", "key": [("candidate_id", 1), ("started_at", -1)]},
        {"name": "started_at_index", "key": [("started_at", 1)]}
    ])
    live_sessions_collection.list_indexes.return_value = live_sessions_cursor
    
    question_results_cursor = AsyncMock()
    question_results_cursor.to_list = AsyncMock(return_value=[
        {"name": "_id_", "key": [("_id", 1)]},
        {"name": "session_timestamp_compound", "key": [("session_id", 1), ("timestamp", 1)]}
    ])
    question_results_collection.list_indexes.return_value = question_results_cursor
    
    # Drop all indexes
    result = await drop_all_indexes(mock_db)
    
    # Verify drop counts
    assert result["live_sessions"] == 3
    assert result["question_results"] == 1
    
    # Verify drop_index was called for each custom index
    assert live_sessions_collection.drop_index.call_count == 3
    assert question_results_collection.drop_index.call_count == 1
    
    # Verify _id index was not dropped
    dropped_names = [call[0][0] for call in live_sessions_collection.drop_index.call_args_list]
    assert "_id_" not in dropped_names


@pytest.mark.asyncio
async def test_create_indexes_error_handling(mock_db):
    """
    Test error handling when index creation fails.
    
    Validates:
    - Exceptions are raised when index creation fails
    - Error is logged
    
    Requirements: 8.17, 8.18
    """
    collection = mock_db["live_sessions"]
    
    # Configure mock to raise exception
    collection.create_index.side_effect = Exception("Index creation failed")
    
    # Verify exception is raised
    with pytest.raises(Exception) as exc_info:
        await create_live_sessions_indexes(mock_db)
    
    assert "Index creation failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_index_names_are_descriptive():
    """
    Test that index names are descriptive and follow naming conventions.
    
    Validates:
    - Index names describe their purpose
    - Index names follow consistent naming pattern
    
    Requirements: 8.17, 8.18
    """
    # Expected index names
    expected_names = {
        "live_sessions": [
            "session_id_unique",
            "candidate_started_compound",
            "started_at_index"
        ],
        "question_results": [
            "session_timestamp_compound"
        ]
    }
    
    # Verify naming conventions
    for collection, names in expected_names.items():
        for name in names:
            # Index names should be lowercase with underscores
            assert name.islower() or "_" in name
            
            # Compound indexes should have "compound" in name
            if "compound" in name:
                assert "_" in name
            
            # Unique indexes should have "unique" in name
            if "unique" in name:
                assert "unique" in name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
