import pytest
from unittest.mock import AsyncMock, patch
from app.services.report_generator import ReportGenerator

@pytest.mark.asyncio
async def test_generate_report_no_results():
    """Test report generation when no results are found."""
    with patch("app.services.session_service.SessionService.get_session") as mock_get:
        mock_get.return_value = {"results": [], "role": "Engineer", "user_id": "u1"}
        
        report = await ReportGenerator.generate_report("s1")
        
        assert report["overallScore"] == 0
        assert "strengths" in report
        assert len(report["strengths"]) > 0

@pytest.mark.asyncio
async def test_generate_report_with_data():
    """Test report generation with valid session results."""
    mock_session = {
        "results": [
            {"question_text": "Q1", "score": 80, "feedback": "Good", "filler_word_count": 2},
            {"question_text": "Q2", "score": 60, "feedback": "Okay", "filler_word_count": 5}
        ],
        "role": "Frontend dev",
        "difficulty": "medium",
        "user_id": "u1"
    }
    
    with patch("app.services.session_service.SessionService.get_session", new_callable=AsyncMock) as mock_get, \
         patch("google.genai.Client") as mock_genai:
        
        mock_get.return_value = mock_session
        
        # Mock Gemini response
        mock_response = AsyncMock()
        mock_response.text = "Candidate did well but needs to reduce fillers."
        mock_genai.return_value.models.generate_content.return_value = mock_response
        
        report = await ReportGenerator.generate_report("s1")
        
        assert report["overallScore"] == 70  # (80+60)/2
        assert report["totalFillers"] == 7
        assert report["questionsAnswered"] == 2
        assert report["summary"] == "Candidate did well but needs to reduce fillers."
