"""
Comprehensive test script for real-time voice interaction system.
Tests all components, integration, and performance.
"""

import asyncio
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_test(name: str, status: str, message: str = ""):
    """Log test result."""
    symbol = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    print(f"{symbol} {name}: {message}")
    
    if status == "pass":
        test_results["passed"].append(name)
    elif status == "fail":
        test_results["failed"].append(name)
    else:
        test_results["warnings"].append(name)


async def test_imports():
    """Test 1: Verify all imports work."""
    print("\n🔍 Test 1: Checking imports...")
    
    try:
        from agent.realtime_models import (
            ConversationState, VoiceFlowState, SilenceEvent,
            PresenceCheckResult, AnalysisResult
        )
        log_test("Import realtime_models", "pass", "All models imported")
    except Exception as e:
        log_test("Import realtime_models", "fail", str(e))
        return False
    
    try:
        from agent.silence_detector import SilenceDetector
        log_test("Import SilenceDetector", "pass")
    except Exception as e:
        log_test("Import SilenceDetector", "fail", str(e))
        return False
    
    try:
        from agent.speech_buffer import SpeechBuffer
        log_test("Import SpeechBuffer", "pass")
    except Exception as e:
        log_test("Import SpeechBuffer", "fail", str(e))
        return False
    
    try:
        from agent.context_tracker import ContextTracker
        log_test("Import ContextTracker", "pass")
    except Exception as e:
        log_test("Import ContextTracker", "fail", str(e))
        return False
    
    try:
        from agent.gemini_embedding_service import GeminiEmbeddingService
        log_test("Import GeminiEmbeddingService", "pass")
    except Exception as e:
        log_test("Import GeminiEmbeddingService", "fail", str(e))
        return False
    
    try:
        from agent.answer_analyzer import AnswerAnalyzer
        log_test("Import AnswerAnalyzer", "pass")
    except Exception as e:
        log_test("Import AnswerAnalyzer", "fail", str(e))
        return False
    
    try:
        from agent.interruption_engine import InterruptionEngine
        log_test("Import InterruptionEngine", "pass")
    except Exception as e:
        log_test("Import InterruptionEngine", "fail", str(e))
        return False
    
    try:
        from agent.presence_verifier import PresenceVerifier
        log_test("Import PresenceVerifier", "pass")
    except Exception as e:
        log_test("Import PresenceVerifier", "fail", str(e))
        return False
    
    try:
        from agent.voice_flow_controller import VoiceFlowController
        log_test("Import VoiceFlowController", "pass")
    except Exception as e:
        log_test("Import VoiceFlowController", "fail", str(e))
        return False
    
    try:
        from agent.error_handlers import CompositeErrorHandler
        log_test("Import ErrorHandlers", "pass")
    except Exception as e:
        log_test("Import ErrorHandlers", "fail", str(e))
        return False
    
    try:
        from agent.security import SecurityManager
        log_test("Import SecurityManager", "pass")
    except Exception as e:
        log_test("Import SecurityManager", "fail", str(e))
        return False
    
    try:
        from services.tts_cache_service import TTSCacheService
        log_test("Import TTSCacheService", "pass")
    except Exception as e:
        log_test("Import TTSCacheService", "fail", str(e))
        return False
    
    try:
        from agent.performance_monitor import PerformanceMonitor
        log_test("Import PerformanceMonitor", "pass")
    except Exception as e:
        log_test("Import PerformanceMonitor", "fail", str(e))
        return False
    
    try:
        from routes.realtime_voice import router
        log_test("Import API Router", "pass")
    except Exception as e:
        log_test("Import API Router", "fail", str(e))
        return False
    
    return True


async def test_component_initialization():
    """Test 2: Verify components can be initialized."""
    print("\n🔍 Test 2: Testing component initialization...")
    
    try:
        from agent.silence_detector import SilenceDetector
        detector = SilenceDetector()
        log_test("Initialize SilenceDetector", "pass", f"Threshold: {detector.silence_threshold_db}dB")
    except Exception as e:
        log_test("Initialize SilenceDetector", "fail", str(e))
    
    try:
        from agent.speech_buffer import SpeechBuffer
        buffer = SpeechBuffer()
        log_test("Initialize SpeechBuffer", "pass", f"Threshold: {buffer.analysis_word_threshold} words")
    except Exception as e:
        log_test("Initialize SpeechBuffer", "fail", str(e))
    
    try:
        from agent.interruption_engine import InterruptionEngine
        engine = InterruptionEngine()
        log_test("Initialize InterruptionEngine", "pass", f"Max interruptions: {engine.max_interruptions_per_question}")
    except Exception as e:
        log_test("Initialize InterruptionEngine", "fail", str(e))
    
    try:
        from agent.gemini_embedding_service import GeminiEmbeddingService
        if os.getenv("GEMINI_API_KEY"):
            service = GeminiEmbeddingService()
            log_test("Initialize GeminiEmbeddingService", "pass", "API key found")
        else:
            log_test("Initialize GeminiEmbeddingService", "warn", "GEMINI_API_KEY not set")
    except Exception as e:
        log_test("Initialize GeminiEmbeddingService", "fail", str(e))
    
    try:
        from agent.performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor()
        log_test("Initialize PerformanceMonitor", "pass", f"History size: {monitor.history_size}")
    except Exception as e:
        log_test("Initialize PerformanceMonitor", "fail", str(e))
    
    try:
        from services.tts_cache_service import TTSCacheService
        cache = TTSCacheService()
        log_test("Initialize TTSCacheService", "pass", f"Enabled: {cache.enabled}")
    except Exception as e:
        log_test("Initialize TTSCacheService", "fail", str(e))
    
    try:
        from agent.security import SecurityManager
        jwt_secret = os.getenv("JWT_SECRET", "test-secret")
        security = SecurityManager(jwt_secret)
        log_test("Initialize SecurityManager", "pass")
    except Exception as e:
        log_test("Initialize SecurityManager", "fail", str(e))
    
    try:
        from agent.error_handlers import CompositeErrorHandler
        handler = CompositeErrorHandler()
        log_test("Initialize ErrorHandler", "pass")
    except Exception as e:
        log_test("Initialize ErrorHandler", "fail", str(e))


async def test_speech_buffer_functionality():
    """Test 3: Test SpeechBuffer operations."""
    print("\n🔍 Test 3: Testing SpeechBuffer functionality...")
    
    try:
        from agent.speech_buffer import SpeechBuffer
        
        buffer = SpeechBuffer(analysis_word_threshold=5)
        
        # Test adding segments
        buffer.add_final_segment("Hello world", confidence=0.95)
        buffer.add_final_segment("This is a test", confidence=0.90)
        
        # Test word count
        word_count = buffer.word_count()
        if word_count == 6:
            log_test("SpeechBuffer word count", "pass", f"Counted {word_count} words")
        else:
            log_test("SpeechBuffer word count", "fail", f"Expected 6, got {word_count}")
        
        # Test accumulated text
        text = buffer.get_accumulated_text()
        if "Hello world" in text and "This is a test" in text:
            log_test("SpeechBuffer accumulation", "pass", "Text accumulated correctly")
        else:
            log_test("SpeechBuffer accumulation", "fail", f"Got: {text}")
        
        # Test analysis trigger
        if buffer.should_trigger_analysis():
            log_test("SpeechBuffer analysis trigger", "pass", "Triggered at 6 words (threshold: 5)")
        else:
            log_test("SpeechBuffer analysis trigger", "fail", "Should have triggered")
        
        # Test clear
        buffer.clear()
        if buffer.word_count() == 0:
            log_test("SpeechBuffer clear", "pass", "Buffer cleared successfully")
        else:
            log_test("SpeechBuffer clear", "fail", f"Word count: {buffer.word_count()}")
        
    except Exception as e:
        log_test("SpeechBuffer functionality", "fail", str(e))


async def test_interruption_engine():
    """Test 4: Test InterruptionEngine logic."""
    print("\n🔍 Test 4: Testing InterruptionEngine...")
    
    try:
        from agent.interruption_engine import InterruptionEngine
        from agent.realtime_models import InterruptionContext
        import time
        
        engine = InterruptionEngine(max_interruptions_per_question=2)
        
        # Test can_interrupt
        if engine.can_interrupt():
            log_test("InterruptionEngine can_interrupt", "pass", "Initially allows interruptions")
        else:
            log_test("InterruptionEngine can_interrupt", "fail", "Should allow interruptions")
        
        # Test first interruption
        context = InterruptionContext(
            question_topic="the mathematical calculation",
            off_topic_content="I have interviewed people",
            attempt_number=1,
            previous_interruptions=[],
            timestamp=time.time()
        )
        
        message1 = engine.generate_interruption(context)
        if message1 and "Wait, I asked about" in message1:
            log_test("InterruptionEngine first message", "pass", f"Generated: {message1[:50]}...")
        else:
            log_test("InterruptionEngine first message", "fail", f"Got: {message1}")
        
        # Test second interruption
        context.attempt_number = 2
        message2 = engine.generate_interruption(context)
        if message2 and "Let me stop you there" in message2:
            log_test("InterruptionEngine second message", "pass", f"Generated: {message2[:50]}...")
        else:
            log_test("InterruptionEngine second message", "fail", f"Got: {message2}")
        
        # Test max interruptions
        context.attempt_number = 3
        message3 = engine.generate_interruption(context)
        if message3 is None:
            log_test("InterruptionEngine max limit", "pass", "Correctly blocked 3rd interruption")
        else:
            log_test("InterruptionEngine max limit", "fail", "Should have blocked 3rd interruption")
        
        # Test reset
        engine.reset_for_new_question()
        if engine.get_interruption_count() == 0:
            log_test("InterruptionEngine reset", "pass", "Counter reset successfully")
        else:
            log_test("InterruptionEngine reset", "fail", f"Count: {engine.get_interruption_count()}")
        
    except Exception as e:
        log_test("InterruptionEngine functionality", "fail", str(e))


async def test_security_sanitization():
    """Test 5: Test security input sanitization."""
    print("\n🔍 Test 5: Testing security sanitization...")
    
    try:
        from agent.security import InputSanitizer
        
        sanitizer = InputSanitizer()
        
        # Test SQL injection prevention
        malicious_sql = "Hello'; DROP TABLE users; --"
        sanitized = sanitizer.sanitize_transcript(malicious_sql)
        if "DROP" not in sanitized:
            log_test("Security SQL injection", "pass", "SQL keywords removed")
        else:
            log_test("Security SQL injection", "fail", f"Got: {sanitized}")
        
        # Test XSS prevention
        xss_input = "<script>alert('xss')</script>Hello"
        sanitized = sanitizer.sanitize_transcript(xss_input)
        if "<script>" not in sanitized:
            log_test("Security XSS prevention", "pass", "Script tags removed")
        else:
            log_test("Security XSS prevention", "fail", f"Got: {sanitized}")
        
        # Test length limiting
        long_text = "word " * 300  # 300 words
        sanitized = sanitizer.sanitize_transcript(long_text)
        if len(sanitized) <= InputSanitizer.MAX_TRANSCRIPT_LENGTH:
            log_test("Security length limit", "pass", f"Truncated to {len(sanitized)} chars")
        else:
            log_test("Security length limit", "fail", f"Length: {len(sanitized)}")
        
        # Test session ID sanitization
        malicious_id = "../../../etc/passwd"
        sanitized_id = sanitizer.sanitize_session_id(malicious_id)
        if "/" not in sanitized_id and "." not in sanitized_id:
            log_test("Security session ID", "pass", f"Sanitized: {sanitized_id}")
        else:
            log_test("Security session ID", "fail", f"Got: {sanitized_id}")
        
    except Exception as e:
        log_test("Security sanitization", "fail", str(e))


async def test_performance_monitor():
    """Test 6: Test performance monitoring."""
    print("\n🔍 Test 6: Testing performance monitoring...")
    
    try:
        from agent.performance_monitor import PerformanceMonitor, track_latency
        
        monitor = PerformanceMonitor()
        
        # Test latency recording
        monitor.record_latency("stt", "transcribe", 450.5, success=True)
        monitor.record_latency("claude", "analyze", 1800.0, success=True)
        monitor.record_latency("gemini", "embed", 950.0, success=True)
        
        # Test average calculation
        avg_stt = monitor.get_average_latency("stt")
        if avg_stt == 450.5:
            log_test("PerformanceMonitor average", "pass", f"STT avg: {avg_stt}ms")
        else:
            log_test("PerformanceMonitor average", "fail", f"Expected 450.5, got {avg_stt}")
        
        # Test error recording
        monitor.record_error("claude")
        if monitor.get_error_count("claude") == 1:
            log_test("PerformanceMonitor errors", "pass", "Error count tracked")
        else:
            log_test("PerformanceMonitor errors", "fail", f"Count: {monitor.get_error_count('claude')}")
        
        # Test cache metrics
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        hit_rate = monitor.get_cache_hit_rate()
        if abs(hit_rate - 0.667) < 0.01:
            log_test("PerformanceMonitor cache", "pass", f"Hit rate: {hit_rate:.3f}")
        else:
            log_test("PerformanceMonitor cache", "fail", f"Expected ~0.667, got {hit_rate}")
        
        # Test snapshot
        snapshot = monitor.get_performance_snapshot()
        if snapshot.stt_latency_ms == 450.5:
            log_test("PerformanceMonitor snapshot", "pass", "Snapshot generated")
        else:
            log_test("PerformanceMonitor snapshot", "fail", "Snapshot data incorrect")
        
    except Exception as e:
        log_test("PerformanceMonitor functionality", "fail", str(e))


async def test_api_endpoints():
    """Test 7: Verify API endpoints are registered."""
    print("\n🔍 Test 7: Testing API endpoint registration...")
    
    try:
        from main import app
        
        routes = [route.path for route in app.routes]
        
        # Check if realtime voice endpoints exist
        expected_endpoints = [
            "/session/{session_id}/voice/realtime/start",
            "/session/{session_id}/voice/realtime/stream",
            "/session/{session_id}/voice/realtime/interrupt",
            "/session/{session_id}/voice/realtime/status"
        ]
        
        for endpoint in expected_endpoints:
            if endpoint in routes:
                log_test(f"API endpoint {endpoint}", "pass", "Registered")
            else:
                log_test(f"API endpoint {endpoint}", "fail", "Not found in routes")
        
    except Exception as e:
        log_test("API endpoint registration", "fail", str(e))


async def test_environment_variables():
    """Test 8: Check required environment variables."""
    print("\n🔍 Test 8: Checking environment variables...")
    
    required_vars = {
        "ANTHROPIC_API_KEY": "Claude API",
        "GEMINI_API_KEY": "Gemini embeddings",
        "JWT_SECRET": "Authentication",
        "UPSTASH_REDIS_REST_URL": "TTS caching",
        "UPSTASH_REDIS_REST_TOKEN": "TTS caching"
    }
    
    for var, purpose in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            log_test(f"ENV {var}", "pass", f"{purpose} ({masked})")
        else:
            log_test(f"ENV {var}", "warn", f"{purpose} not set")


async def test_performance_benchmarks():
    """Test 9: Run performance benchmarks."""
    print("\n🔍 Test 9: Running performance benchmarks...")
    
    try:
        from agent.speech_buffer import SpeechBuffer
        from agent.interruption_engine import InterruptionEngine
        from agent.realtime_models import InterruptionContext
        import time
        
        # Benchmark SpeechBuffer operations
        buffer = SpeechBuffer()
        start = time.perf_counter()
        for i in range(1000):
            buffer.add_final_segment(f"Test segment {i}")
        duration_ms = (time.perf_counter() - start) * 1000
        
        if duration_ms < 100:  # Should be very fast
            log_test("Performance SpeechBuffer", "pass", f"{duration_ms:.2f}ms for 1000 ops")
        else:
            log_test("Performance SpeechBuffer", "warn", f"{duration_ms:.2f}ms (slow)")
        
        # Benchmark InterruptionEngine
        engine = InterruptionEngine()
        context = InterruptionContext(
            question_topic="test",
            off_topic_content="test",
            attempt_number=1,
            previous_interruptions=[],
            timestamp=time.time()
        )
        
        start = time.perf_counter()
        for i in range(1000):
            engine._generate_first_interruption(context)
        duration_ms = (time.perf_counter() - start) * 1000
        
        if duration_ms < 10:  # Should be instant
            log_test("Performance InterruptionEngine", "pass", f"{duration_ms:.2f}ms for 1000 ops")
        else:
            log_test("Performance InterruptionEngine", "warn", f"{duration_ms:.2f}ms")
        
    except Exception as e:
        log_test("Performance benchmarks", "fail", str(e))


async def main():
    """Run all tests."""
    print("=" * 70)
    print("🚀 Real-Time Voice Interaction System - Comprehensive Test Suite")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run all tests
    await test_imports()
    await test_component_initialization()
    await test_speech_buffer_functionality()
    await test_interruption_engine()
    await test_security_sanitization()
    await test_performance_monitor()
    await test_api_endpoints()
    await test_environment_variables()
    await test_performance_benchmarks()
    
    # Print summary
    duration = time.time() - start_time
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"✅ Passed: {len(test_results['passed'])}")
    print(f"❌ Failed: {len(test_results['failed'])}")
    print(f"⚠️  Warnings: {len(test_results['warnings'])}")
    print(f"⏱️  Duration: {duration:.2f}s")
    print("=" * 70)
    
    if test_results['failed']:
        print("\n❌ Failed tests:")
        for test in test_results['failed']:
            print(f"  - {test}")
        sys.exit(1)
    else:
        print("\n✅ All critical tests passed!")
        if test_results['warnings']:
            print("\n⚠️  Warnings (non-critical):")
            for test in test_results['warnings']:
                print(f"  - {test}")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
