import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.question_engine import QuestionEngine

@pytest.mark.asyncio
async def test_generate_questions_basic():
    """Test generating 5 questions for a Software Engineer role."""
    with patch("google.genai.Client") as mock_client:
        # Mock the Gemini response
        mock_response = AsyncMock()
        mock_response.text = '[{"question": "Q1", "topic": "T1", "difficulty": "medium", "expected_signals": ["S1"], "follow_ups": []}]'
        
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        questions = await QuestionEngine.generate_questions(
            role="Software Engineer",
            topics=["Python", "Cloud"],
            difficulty="medium"
        )
        
        assert len(questions) > 0
        assert "question" in questions[0]
        assert "expected_signals" in questions[0]

@pytest.mark.asyncio
async def test_generate_questions_with_memory():
    """Test that user memory is passed to the prompt."""
    with patch("google.genai.Client") as mock_client:
        mock_response = AsyncMock()
        mock_response.text = '[]'
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        await QuestionEngine.generate_questions(
            role="Data Scientist",
            topics=["ML"],
            difficulty="hard",
            user_memory="Candidate struggles with transformers."
        )
        
        # Verify the prompt contained the memory string
        call_args = mock_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs.get("contents") or call_args.args[1]
        assert "Candidate struggles with transformers" in prompt
