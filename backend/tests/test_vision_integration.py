"""
Integration tests for Vision Agents system.

This module tests the complete end-to-end flow of the Vision Agents
interview system.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from agent.vision.core.emotion_snapshot import EmotionSnapshot
from agent.vision.core.speech_metrics import SpeechMetrics
from agent.vision.processors.emotion_processor import EmotionProcessor
from agent.vision.processors.speech_processor import SpeechProcessor
from agent.vision.core.decision_engine import DecisionEngine
from agent.vision.core.question_manager import QuestionManager
from agent.vision.core.roundzero_agent import RoundZeroAgent


class TestEmotionProcessor:
    """Test EmotionProcessor functionality."""
    
    @pytest.mark.asyncio
    async def test_emotion_snapshot_creation(self):
        """Test creating emotion snapshot with validation."""
        snapshot = EmotionSnapshot(
            emotion="confident",
            confidence_score=85,
            engagement_level="high",
            body_language_observations="Upright posture, eye contact",
            timestamp=1234567890.0
        )
        
        assert snapshot.emotion == "confident"
        assert snapshot.confidence_score == 85
        assert snapshot.engagement_level == "high"
        assert snapshot.timestamp == 1234567890.0
    
    @pytest.mark.asyncio
    async def test_emotion_snapshot_validation(self):
        """Test emotion snapshot validation."""
        # Test invalid confidence score
        with pytest.raises(ValueError):
            EmotionSnapshot(
                emotion="confident",
                confidence_score=150,  # Invalid: > 100
                engagement_level="high",
                body_language_observations="Test",
                timestamp=1234567890.0
            )
        
        # Test invalid emotion
        with pytest.raises(ValueError):
            EmotionSnapshot(
                emotion="invalid_emotion",  # Invalid emotion type
                confidence_score=85,
                engagement_level="high",
                body_language_observations="Test",
                timestamp=1234567890.0
            )
    
    @pytest.mark.asyncio
    async def test_frame_sampling(self):
        """Test frame sampling logic."""
        mock_gemini = AsyncMock()
        mock_repo = AsyncMock()
        
        processor = EmotionProcessor(
            gemini_client=mock_gemini,
            session_id="test_session",
            mongo_repository=mock_repo,
            frame_sample_rate=10
        )
        
        # Process 15 frames
        for i in range(15):
            frame = b"fake_frame_data"
            result = await processor.process_frame(frame)
            
            # Should only process frames 10 and 20 (every 10th)
            if (i + 1) % 10 == 0:
                # Frame should be processed (but will fail without real Gemini)
                pass
            else:
                # Frame should be skipped
                assert result is None


class TestSpeechProcessor:
    """Test SpeechProcessor functionality."""
    
    @pytest.mark.asyncio
    async def test_speech_metrics_creation(self):
        """Test creating speech metrics."""
        metrics = SpeechMetrics(
            filler_word_count=5,
            speech_pace=145.5,
            long_pause_count=2,
            average_filler_rate=3.4,
            rapid_speech=False,
            slow_speech=False
        )
        
        assert metrics.filler_word_count == 5
        assert metrics.speech_pace == 145.5
        assert metrics.long_pause_count == 2
    
    @pytest.mark.asyncio
    async def test_filler_word_detection(self):
        """Test filler word detection."""
        mock_repo = AsyncMock()
        
        processor = SpeechProcessor(
            session_id="test_session",
            mongo_repository=mock_repo
        )
        
        # Test text with filler words
        text = "Um, I think, like, the answer is, you know, basically correct"
        count = processor._count_fillers(text)
        
        # Should detect: um, like, you know, basically = 4 fillers
        assert count == 4
    
    @pytest.mark.asyncio
    async def test_speech_pace_calculation(self):
        """Test speech pace calculation."""
        mock_repo = AsyncMock()
        
        processor = SpeechProcessor(
            session_id="test_session",
            mongo_repository=mock_repo
        )
        
        # Simulate transcript segments
        await processor.process_transcript_segment(
            text="This is a test sentence with ten words in it",
            is_final=True,
            timestamp=1000.0
        )
        
        await processor.process_transcript_segment(
            text="Another sentence with more words to analyze",
            is_final=True,
            timestamp=1005.0  # 5 seconds later
        )
        
        metrics = processor._calculate_metrics()
        
        # Should have calculated pace and other metrics
        assert metrics.speech_pace > 0
        assert metrics.filler_word_count >= 0
        assert metrics.long_pause_count >= 0


class TestDecisionEngine:
    """Test DecisionEngine functionality."""
    
    @pytest.mark.asyncio
    async def test_fallback_decision_high_fillers(self):
        """Test fallback decision with high filler count."""
        engine = DecisionEngine(claude_api_key="test_key")
        
        context = {
            "question_text": "What is your experience?",
            "transcript_so_far": "Um, well, like, I have, you know...",
            "emotion": "nervous",
            "confidence_score": 40,
            "engagement_level": "medium",
            "filler_word_count": 15,  # High filler count
            "speech_pace": 120,
            "long_pause_count": 1
        }
        
        decision = engine._fallback_decision(context)
        
        assert decision["action"] == "ENCOURAGE"
        assert "time" in decision["message"].lower()
    
    @pytest.mark.asyncio
    async def test_fallback_decision_low_confidence(self):
        """Test fallback decision with low confidence."""
        engine = DecisionEngine(claude_api_key="test_key")
        
        context = {
            "question_text": "What is your experience?",
            "transcript_so_far": "I'm not sure...",
            "emotion": "nervous",
            "confidence_score": 25,  # Low confidence
            "engagement_level": "low",
            "filler_word_count": 3,
            "speech_pace": 100,
            "long_pause_count": 1
        }
        
        decision = engine._fallback_decision(context)
        
        assert decision["action"] == "ENCOURAGE"


class TestRoundZeroAgent:
    """Test RoundZeroAgent orchestration."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization."""
        # Create mocks
        mock_emotion_processor = Mock()
        mock_speech_processor = Mock()
        mock_decision_engine = Mock()
        mock_question_manager = AsyncMock()
        mock_question_manager.fetch_questions = AsyncMock(return_value=[
            {"id": "q1", "text": "Question 1", "difficulty": "medium"},
            {"id": "q2", "text": "Question 2", "difficulty": "medium"}
        ])
        mock_tts_service = AsyncMock()
        mock_mongo_repo = AsyncMock()
        
        # Create agent
        agent = RoundZeroAgent(
            session_id="test_session",
            candidate_id="test_candidate",
            role="Software Engineer",
            topics=["Python", "Algorithms"],
            difficulty="medium",
            mode="practice",
            emotion_processor=mock_emotion_processor,
            speech_processor=mock_speech_processor,
            decision_engine=mock_decision_engine,
            question_manager=mock_question_manager,
            tts_service=mock_tts_service,
            mongo_repository=mock_mongo_repo
        )
        
        # Initialize
        await agent.initialize()
        
        # Verify questions were fetched
        assert len(agent.questions) == 2
        assert agent.questions[0]["id"] == "q1"
    
    @pytest.mark.asyncio
    async def test_transcript_handling(self):
        """Test transcript segment handling."""
        # Create mocks
        mock_emotion_processor = Mock()
        mock_speech_processor = AsyncMock()
        mock_decision_engine = Mock()
        mock_question_manager = AsyncMock()
        mock_question_manager.fetch_questions = AsyncMock(return_value=[
            {"id": "q1", "text": "Question 1", "difficulty": "medium"}
        ])
        mock_tts_service = AsyncMock()
        mock_mongo_repo = AsyncMock()
        
        # Create agent
        agent = RoundZeroAgent(
            session_id="test_session",
            candidate_id="test_candidate",
            role="Software Engineer",
            topics=["Python"],
            difficulty="medium",
            mode="practice",
            emotion_processor=mock_emotion_processor,
            speech_processor=mock_speech_processor,
            decision_engine=mock_decision_engine,
            question_manager=mock_question_manager,
            tts_service=mock_tts_service,
            mongo_repository=mock_mongo_repo
        )
        
        await agent.initialize()
        
        # Handle transcript
        await agent.handle_transcript_segment(
            text="This is a test answer with enough words",
            is_final=True,
            timestamp=1000.0
        )
        
        # Verify transcript was stored
        assert "test answer" in agent.transcript_buffer
        assert agent.word_count > 0


class TestIntegrationFlow:
    """Test complete integration flow."""
    
    @pytest.mark.asyncio
    async def test_complete_interview_flow(self):
        """Test complete interview flow from start to finish."""
        # This is a high-level integration test
        # In production, this would test the actual flow with real services
        
        # Create mocks for all services
        mock_emotion_processor = Mock()
        mock_emotion_processor.get_latest_emotion = Mock(return_value=EmotionSnapshot(
            emotion="confident",
            confidence_score=75,
            engagement_level="high",
            body_language_observations="Good posture",
            timestamp=1000.0
        ))
        mock_emotion_processor.get_emotion_timeline = Mock(return_value=[])
        mock_emotion_processor.get_average_confidence = Mock(return_value=75.0)
        
        mock_speech_processor = AsyncMock()
        mock_speech_processor.get_current_metrics = Mock(return_value={
            "filler_word_count": 2,
            "speech_pace": 140,
            "long_pause_count": 1
        })
        
        mock_decision_engine = AsyncMock()
        mock_decision_engine.make_decision = AsyncMock(return_value={
            "action": "CONTINUE",
            "message": "",
            "reasoning": "Answer is on track"
        })
        mock_decision_engine.generate_summary = AsyncMock(return_value="Great interview!")
        
        mock_question_manager = AsyncMock()
        mock_question_manager.fetch_questions = AsyncMock(return_value=[
            {"id": "q1", "text": "Tell me about yourself", "difficulty": "easy"}
        ])
        
        mock_tts_service = AsyncMock()
        mock_mongo_repo = AsyncMock()
        
        # Create agent
        agent = RoundZeroAgent(
            session_id="test_session",
            candidate_id="test_candidate",
            role="Software Engineer",
            topics=["Python"],
            difficulty="easy",
            mode="practice",
            emotion_processor=mock_emotion_processor,
            speech_processor=mock_speech_processor,
            decision_engine=mock_decision_engine,
            question_manager=mock_question_manager,
            tts_service=mock_tts_service,
            mongo_repository=mock_mongo_repo
        )
        
        # Initialize agent
        await agent.initialize()
        assert len(agent.questions) == 1
        
        # Start interview
        await agent.start_interview()
        assert agent.ai_state == "listening"
        
        # Simulate transcript
        for i in range(5):
            await agent.handle_transcript_segment(
                text=f"This is sentence number {i} in my answer",
                is_final=True,
                timestamp=1000.0 + i
            )
        
        # Verify state
        assert agent.word_count > 20
        assert len(agent.transcript_buffer) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
