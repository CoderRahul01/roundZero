# Voice Agent Performance Optimizations

## Overview
Optimizations implemented to ensure the voice agent is fast and all data is properly saved.

## Speed Optimizations

### 1. TTS Caching (Multi-Layer)
- **Memory Cache**: Ultra-fast in-memory cache for repeated phrases
- **Redis Cache**: Persistent cache across server restarts
- **Preloading**: Common phrases preloaded at startup
- **Impact**: 10-100x faster for cached phrases

**Files Modified:**
- `backend/services/tts_service.py` - Memory + Redis caching
- `backend/services/tts_cache_service.py` - Redis cache management
- `backend/main.py` - Startup preloading

### 2. Parallel Processing
- **Concurrent Analysis**: Claude + Gemini embeddings run in parallel
- **Batch TTS**: Multiple phrases synthesized concurrently
- **Async Operations**: All I/O operations are non-blocking

**Files Created:**
- `backend/agent/performance_optimizer.py` - Parallel processing utilities

### 3. Timeouts & Rate Limiting
- **Analysis Timeout**: 2.5-3 second timeout to prevent blocking
- **Rate Limiting**: Analysis runs max every 5 seconds
- **Graceful Degradation**: Timeouts don't break the flow

**Files Modified:**
- `backend/agent/answer_analyzer.py` - Timeout handling
- `backend/agent/voice_flow_controller.py` - Analysis timeout

### 4. Connection Pooling
- **MongoDB**: Motor async driver with connection pooling
- **Redis**: Upstash Redis with persistent connections
- **HTTP**: Async clients reuse connections

## Data Persistence

### 1. Voice Session Repository
Complete data persistence for all voice interactions:
- **Sessions**: Session metadata and configuration
- **Transcripts**: All speech-to-text results (interim + final)
- **Interruptions**: All interruption events with context
- **Analyses**: All relevance analysis results

**Files Created:**
- `backend/data/voice_session_repository.py` - Complete persistence layer

### 2. Async Saving
- **Non-blocking**: All database writes are async
- **Fire-and-forget**: Saves don't block the voice flow
- **Reliable**: Uses asyncio.create_task for background saves

**Files Modified:**
- `backend/agent/voice_flow_controller.py` - Integrated repository

### 3. Data Tracking
- **Question IDs**: Each question gets unique ID for tracking
- **Timestamps**: All events timestamped
- **Session Summary**: Complete session data retrieval

## Performance Metrics

### Expected Latencies
- **TTS (cached)**: < 10ms
- **TTS (uncached)**: 500-1500ms
- **Analysis**: < 2500ms (with timeout)
- **Transcript save**: < 50ms (async)
- **Total response time**: < 3000ms

### Cache Hit Rates
- **Common phrases**: ~90% hit rate
- **Questions**: ~50% hit rate (repeated questions)
- **Overall TTS**: ~70% hit rate expected

## Configuration

### Environment Variables Required
```bash
# AI Services
ANTHROPIC_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
GEMINI_API_KEY=your_key

# Storage
MONGODB_URI=your_mongodb_uri
UPSTASH_REDIS_REST_URL=your_redis_url
UPSTASH_REDIS_REST_TOKEN=your_redis_token

# Speech Services
DEEPGRAM_API_KEY=your_key
```

### Tunable Parameters

**TTS Cache:**
- `TTL_HOURS`: Cache expiration (default: 24h)
- `MAX_CACHE_SIZE_MB`: Max cache size (default: 50MB)

**Analysis:**
- `ANALYSIS_INTERVAL`: Min time between analyses (default: 5s)
- `ANALYSIS_TIMEOUT`: Max analysis time (default: 2.5s)
- `RELEVANCE_THRESHOLD`: Semantic similarity threshold (default: 0.3)

## Monitoring

### Performance Metrics Endpoint
```bash
GET /session/{session_id}/voice/realtime/status
```

Returns:
- Current state
- Speech buffer word count
- Interruption count
- Silence duration
- Performance metrics

### Cache Stats
```python
# TTS cache stats
cache_service.get_cache_stats()

# Performance optimizer metrics
optimizer.get_metrics()
```

## Best Practices

### For Speed
1. Preload common phrases at startup
2. Use cached TTS whenever possible
3. Keep analysis intervals reasonable (5s+)
4. Use timeouts to prevent blocking

### For Reliability
1. Always save data asynchronously
2. Use fire-and-forget for non-critical saves
3. Handle timeouts gracefully
4. Log all errors but don't break flow

### For Scale
1. Use connection pooling
2. Implement rate limiting
3. Monitor cache hit rates
4. Clean up old sessions

## Testing

### Speed Test
```bash
# Test TTS cache performance
curl -X POST http://localhost:8000/session/{id}/voice/realtime/start

# Monitor response times
curl http://localhost:8000/session/{id}/voice/realtime/status
```

### Data Persistence Test
```python
# Check session data
repository = VoiceSessionRepository(mongodb_uri)
summary = await repository.get_session_summary(session_id)
print(f"Transcripts: {len(summary['transcripts'])}")
print(f"Interruptions: {len(summary['interruptions'])}")
print(f"Analyses: {len(summary['analyses'])}")
```

## Future Optimizations

### Potential Improvements
1. **Streaming TTS**: Stream audio as it's generated
2. **Predictive Caching**: Preload likely next questions
3. **Edge Caching**: CDN for static audio
4. **Batch Embeddings**: Batch multiple embedding requests
5. **WebSocket Compression**: Compress WebSocket messages

### Monitoring Additions
1. **Latency Tracking**: P50, P95, P99 latencies
2. **Error Rates**: Track failure rates per component
3. **Cache Analytics**: Hit rates, eviction rates
4. **Resource Usage**: CPU, memory, network

## Troubleshooting

### Slow Responses
1. Check cache hit rates
2. Verify Redis connection
3. Check Claude API latency
4. Monitor network latency

### Missing Data
1. Verify MongoDB connection
2. Check async task completion
3. Review error logs
4. Verify session IDs match

### High Memory Usage
1. Clear TTS memory cache periodically
2. Reduce cache size limits
3. Monitor cache growth
4. Implement LRU eviction
