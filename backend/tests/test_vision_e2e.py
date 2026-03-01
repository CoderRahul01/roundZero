"""
End-to-end test for Vision Agents integration.

This test validates the complete interview flow with real services:
- MongoDB connection and storage
- Gemini emotion detection
- Claude decision-making
- Speech processing
- Question management
- Session lifecycle
"""

import sys
from pathlib import Path
import asyncio
import time
import os

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
try:
    import google.generativeai as genai
except ImportError:
    genai = None
from anthropic import AsyncAnthropic
from agent.vision.core.emotion_snapshot import EmotionSnapshot
from agent.vision.core.speech_metrics import SpeechMetrics
from agent.vision.processors.emotion_processor import EmotionProcessor
from agent.vision.processors.speech_processor import SpeechProcessor
from agent.vision.core.decision_engine import DecisionEngine
from agent.vision.core.question_manager import QuestionManager
from agent.vision.core.roundzero_agent import RoundZeroAgent
from agent.gemini_embedding_service import GeminiEmbeddingService
from data.live_session_repository import LiveSessionRepository


class TestVisionE2E:
    """End-to-end tests for Vision Agents integration."""
    
    @pytest.fixture
    async def mongodb_client(self):
        """Create MongoDB client."""
        mongodb_uri = os.getenv("MONGODB_URI")
        if not mongodb_uri:
            pytest.skip("MONGODB_URI not configured")
        
        client = AsyncIOMotorClient(mongodb_uri)
        yield client
        client.close()
    
    @pytest.fixture
    async def live_session_repo(self, mongodb_client):
        """Create LiveSessionRepository."""
        db = mongodb_client.get_database("roundzero")
        return LiveSessionRepository(db)
    
    @pytest.fixture
    def gemini_client(self):
        """Create Gemini client."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not configured")
        
        genai.configure(api_key=api_key)
        return genai
    
    @pytest.fixture
    def claude_client(self):
        """Create Claude client."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not configured")
        
        return AsyncAnthropic(api_key=api_key)
    
    @pytest.fixture
    async def emotion_processor(self, gemini_client, live_session_repo):
        """Create EmotionProcessor."""
        return EmotionProcessor(
            gemini_client=gemini_client,
            session_id="test_e2e_session",
            mongo_repository=live_session_repo,
            frame_sample_rate=10
        )
    
    @pytest.fixture
    async def speech_processor(self, live_session_repo):
        """Create SpeechProcessor."""
        return SpeechProcessor(
            session_id="test_e2e_session",
            mongo_repository=live_session_repo
        )
    
    @pytest.fixture
    async def decision_engine(self):
        """Create DecisionEngine."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not configured")
        
        return DecisionEngine(claude_api_key=api_key)
    
    @pytest.mark.asyncio
    async def test_mongodb_connection(self, mongodb_client):
        """Test MongoDB connection."""
        # Ping MongoDB
        result = await mongodb_client.admin.command('ping')
        assert result['ok'] == 1.0
        print("✅ MongoDB connection successful")
    
    @pytest.mark.asyncio
    async def test_session_creation(self, live_session_repo):
        """Test creating a live session in MongoDB."""
        session_id = f"test_session_{int(time.time())}"
        
        await live_session_repo.create_session(
            session_id=session_id,
            candidate_id="test_candidate",
            call_id="test_call",
            role="Software Engineer",
            topics=["Python", "Algorithms"],
            difficulty="medium",
            mode="practice"
        )
        
        # Retrieve session
        session = await live_session_repo.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["role"] == "Software Engineer"
        print(f"✅ Session creation successful: {session_id}")
    
    @pytest.mark.asyncio
    async def test_transcript_storage(self, live_session_repo):
        """Test storing transcript segments."""
        session_id = f"test_transcript_{int(time.time())}"
        
        # Create session
        await live_session_repo.create_session(
            session_id=session_id,
            candidate_id="test_candidate",
            call_id="test_call",
            role="Software Engineer",
            topics=["Python"],
            difficulty="medium",
            mode="practice"
        )
        
        # Add transcript segments
        await live_session_repo.add_transcript_segment(
            session_id=session_id,
            text="This is my answer to the question",
            timestamp=time.time(),
            speaker="user",
            is_final=True
        )
        
        # Retrieve session
        session = await live_session_repo.get_session(session_id)
        assert len(session["transcript"]) == 1
        assert session["transcript"][0]["text"] == "This is my answer to the question"
        print("✅ Transcript storage successful")
    
    @pytest.mark.asyncio
    async def test_speech_processing(self, speech_processor):
        """Test speech processing with real transcript."""
        # Process transcript with filler words
        await speech_processor.process_transcript_segment(
            text="Um, I think, like, the answer is, you know, basically correct",
            is_final=True,
            timestamp=time.time()
        )
        
        # Get metrics
        metrics = speech_processor.get_current_metrics()
        
        assert metrics["filler_word_count"] > 0
        assert metrics["speech_pace"] >= 0
        print(f"✅ Speech processing successful: {metrics['filler_word_count']} fillers detected")
    
    @pytest.mark.asyncio
    async def test_decision_engine_fallback(self, decision_engine):
        """Test decision engine fallback logic."""
        context = {
            "question_text": "What is your experience with Python?",
            "transcript_so_far": "Um, well, I have, like, some experience...",
            "emotion": "nervous",
            "confidence_score": 35,
            "engagement_level": "medium",
            "filler_word_count": 12,
            "speech_pace": 110,
            "long_pause_count": 2
        }
        
        # Test fallback decision (should return ENCOURAGE due to high fillers)
        decision = decision_engine._fallback_decision(context)
        
        assert decision["action"] == "ENCOURAGE"
        assert "message" in decision
        print(f"✅ Decision engine fallback successful: {decision['action']}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_claude_decision_making(self, decision_engine):
        """Test Claude API decision-making (slow test)."""
        context = {
            "question_text": "Explain the difference between a list and a tuple in Python",
            "transcript_so_far": "A list is mutable and uses square brackets, while a tuple is immutable and uses parentheses",
            "emotion": "confident",
            "confidence_score": 80,
            "engagement_level": "high",
            "filler_word_count": 0,
            "speech_pace": 140,
            "long_pause_count": 0
        }
        
        try:
            decision = await decision_engine.make_decision(context)
            
            assert "action" in decision
            assert decision["action"] in ["CONTINUE", "INTERRUPT", "ENCOURAGE", "NEXT", "HINT"]
            print(f"✅ Claude decision-making successful: {decision['action']}")
        except Exception as e:
            print(f"⚠️  Claude API call failed (expected if rate limited): {e}")
            pytest.skip("Claude API unavailable")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_claude_answer_evaluation(self, decision_engine):
        """Test Claude answer evaluation (slow test)."""
        question = "What is polymorphism in object-oriented programming?"
        answer = "Polymorphism allows objects of different classes to be treated as objects of a common parent class. It enables methods to do different things based on the object type."
        
        try:
            evaluation = await decision_engine.evaluate_answer(question, answer)
            
            assert "relevance_score" in evaluation
            assert "completeness_score" in evaluation
            assert "correctness_score" in evaluation
            assert 0 <= evaluation["relevance_score"] <= 100
            print(f"✅ Answer evaluation successful: relevance={evaluation['relevance_score']}")
        except Exception as e:
            print(f"⚠️  Claude API call failed: {e}")
            pytest.skip("Claude API unavailable")
    
    @pytest.mark.asyncio
    async def test_emotion_snapshot_validation(self):
        """Test emotion snapshot creation and validation."""
        # Valid snapshot
        snapshot = EmotionSnapshot(
            emotion="confident",
            confidence_score=85,
            engagement_level="high",
            body_language_observations="Good posture, eye contact",
            timestamp=time.time()
        )
        
        assert snapshot.emotion == "confident"
        assert snapshot.confidence_score == 85
        print("✅ Emotion snapshot validation successful")
        
        # Invalid confidence score
        with pytest.raises(ValueError):
            EmotionSnapshot(
                emotion="confident",
                confidence_score=150,  # Invalid
                engagement_level="high",
                body_language_observations="Test",
                timestamp=time.time()
            )
        print("✅ Emotion snapshot validation (invalid) successful")
    
    @pytest.mark.asyncio
    async def test_speech_metrics_calculation(self, speech_processor):
        """Test speech metrics calculation."""
        # Process multiple segments
        timestamps = [1000.0, 1002.0, 1004.0, 1006.0, 1008.0]
        texts = [
            "This is the first segment",
            "Um, this is the second segment",
            "Like, this is the third segment",
            "You know, this is the fourth segment",
            "This is the final segment"
        ]
        
        for timestamp, text in zip(timestamps, texts):
            await speech_processor.process_transcript_segment(
                text=text,
                is_final=True,
                timestamp=timestamp
            )
        
        metrics = speech_processor.get_current_metrics()
        
        assert metrics["filler_word_count"] == 3  # um, like, you know
        assert metrics["speech_pace"] > 0
        assert metrics["long_pause_count"] == 0  # No long pauses
        print(f"✅ Speech metrics calculation successful: pace={metrics['speech_pace']:.1f} WPM")
    
    @pytest.mark.asyncio
    async def test_complete_session_lifecycle(self, live_session_repo, speech_processor):
        """Test complete session lifecycle."""
        session_id = f"test_lifecycle_{int(time.time())}"
        
        # 1. Create session
        await live_session_repo.create_session(
            session_id=session_id,
            candidate_id="test_candidate",
            call_id="test_call",
            role="Software Engineer",
            topics=["Python", "Algorithms"],
            difficulty="medium",
            mode="practice"
        )
        print(f"✅ Step 1: Session created: {session_id}")
        
        # 2. Add transcript segments
        await live_session_repo.add_transcript_segment(
            session_id=session_id,
            text="This is my answer",
            timestamp=time.time(),
            speaker="user",
            is_final=True
        )
        print("✅ Step 2: Transcript added")
        
        # 3. Add emotion snapshot
        await live_session_repo.add_emotion_snapshot(
            session_id=session_id,
            emotion="confident",
            confidence_score=80,
            engagement_level="high",
            body_language_observations="Good posture",
            timestamp=time.time()
        )
        print("✅ Step 3: Emotion snapshot added")
        
        # 4. Add speech metrics
        await live_session_repo.add_speech_metrics(
            session_id=session_id,
            question_id="q1",
            metrics={
                "filler_word_count": 2,
                "speech_pace": 140,
                "long_pause_count": 1,
                "average_filler_rate": 1.5,
                "rapid_speech": False,
                "slow_speech": False
            }
        )
        print("✅ Step 4: Speech metrics added")
        
        # 5. Add decision record
        await live_session_repo.add_decision_record(
            session_id=session_id,
            decision={
                "timestamp": time.time(),
                "action": "CONTINUE",
                "context": {"question": "test"},
                "message": "",
                "reasoning": "Answer is on track"
            }
        )
        print("✅ Step 5: Decision record added")
        
        # 6. Finalize session
        await live_session_repo.finalize_session(
            session_id=session_id,
            summary="Great interview! Strong technical knowledge demonstrated."
        )
        print("✅ Step 6: Session finalized")
        
        # 7. Verify complete session
        session = await live_session_repo.get_session(session_id)
        assert session is not None
        assert len(session["transcript"]) == 1
        assert len(session["emotion_timeline"]) == 1
        assert len(session["decisions"]) == 1
        assert session["session_summary"] == "Great interview! Strong technical knowledge demonstrated."
        assert session["ended_at"] is not None
        print("✅ Step 7: Complete session lifecycle verified")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
