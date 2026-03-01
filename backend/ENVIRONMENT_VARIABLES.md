# Environment Variables Documentation

This document provides comprehensive documentation for all environment variables used in the RoundZero AI Interview Coach backend, with special focus on Vision Agents integration.

## Table of Contents

1. [Core Configuration](#core-configuration)
2. [Database Configuration](#database-configuration)
3. [Stream.io WebRTC](#streamio-webrtc)
4. [AI/LLM Services](#aillm-services)
5. [Vector Database & Memory](#vector-database--memory)
6. [Caching & Rate Limiting](#caching--rate-limiting)
7. [Voice Services](#voice-services)
8. [Vision Agents Configuration](#vision-agents-configuration)
9. [Feature Flags](#feature-flags)
10. [Environment Validation](#environment-validation)

---

## Core Configuration

### ENVIRONMENT
- **Type**: String
- **Values**: `development`, `staging`, `production`
- **Default**: `production`
- **Description**: Determines the runtime environment and affects logging, error handling, and security settings.

### LOG_LEVEL
- **Type**: String
- **Values**: `debug`, `info`, `warning`, `error`, `critical`
- **Default**: `info`
- **Description**: Controls the verbosity of application logs.

### CORS_ALLOW_ORIGINS
- **Type**: String (comma-separated URLs)
- **Example**: `http://localhost:3000,http://localhost:5173`
- **Description**: Allowed origins for Cross-Origin Resource Sharing (CORS).

### ALLOWED_HOSTS
- **Type**: String
- **Default**: `*`
- **Description**: Allowed hosts for the application. Use `*` for development, specific domains for production.

### RATE_LIMIT_MAX
- **Type**: Integer
- **Default**: `8`
- **Description**: Maximum number of requests allowed per time window.

### RATE_LIMIT_WINDOW_SECONDS
- **Type**: Integer
- **Default**: `60`
- **Description**: Time window in seconds for rate limiting.

---

## Database Configuration

### DATABASE_URL
- **Type**: String (PostgreSQL connection URL)
- **Format**: `postgresql://user:password@host:port/database?sslmode=require`
- **Required**: Yes
- **Description**: PostgreSQL database connection string for Neon database.
- **Used For**: User authentication, session metadata, legacy data storage.

### MONGODB_URI
- **Type**: String (MongoDB connection URL)
- **Format**: `mongodb+srv://username:password@cluster.mongodb.net/?appName=AppName`
- **Required**: Yes
- **Description**: MongoDB connection string for document storage.
- **Used For**: 
  - Live session transcripts
  - Emotion timeline data
  - Speech metrics per question
  - Decision records
  - Session summaries

### JWT_SECRET
- **Type**: String
- **Required**: Yes
- **Security**: Keep this secret! Never commit to version control.
- **Description**: Secret key for signing and verifying JWT authentication tokens.

### Neon Auth Configuration

#### NEON_AUTH_PROJECT_ID
- **Type**: String
- **Required**: Yes
- **Description**: Neon project identifier for authentication.

#### NEON_AUTH_URL
- **Type**: String (URL)
- **Description**: Neon authentication endpoint URL.

#### NEON_AUTH_JWKS_URL
- **Type**: String (URL)
- **Description**: JSON Web Key Set URL for token verification.

#### NEON_AUTH_ISSUER
- **Type**: String (URL)
- **Description**: JWT token issuer identifier.

#### NEON_AUTH_AUDIENCE
- **Type**: String (URL)
- **Description**: JWT token audience identifier.

#### ALLOW_LEGACY_HS256_AUTH
- **Type**: Boolean
- **Default**: `false`
- **Description**: Allow legacy HS256 JWT authentication (not recommended for production).

---

## Stream.io WebRTC

### STREAM_APP_ID
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://getstream.io/dashboard/
- **Description**: Stream.io application identifier.
- **Used For**: Creating and managing video call sessions.

### STREAM_API_KEY
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://getstream.io/dashboard/
- **Description**: Stream.io API key for authentication.
- **Used For**: Authenticating API requests to Stream.io.

### STREAM_API_SECRET
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Security**: Keep this secret! Never expose in frontend code.
- **Get From**: https://getstream.io/dashboard/
- **Description**: Stream.io API secret for signing tokens.
- **Used For**: Generating secure Stream tokens for video calls.

**Vision Agents Usage:**
- Creates WebRTC video call sessions
- Streams candidate video to EmotionProcessor
- Streams candidate audio to Deepgram STT
- Streams AI audio (ElevenLabs) to candidate
- Manages connection quality and reconnection

---

## AI/LLM Services

### ANTHROPIC_API_KEY
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://console.anthropic.com/
- **Model Used**: Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- **Description**: Anthropic API key for Claude AI.
- **Used For**:
  - Interview decision-making (CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT)
  - Generating intervention messages
  - Evaluating candidate answers
  - Generating session summaries
  - Context-aware coaching feedback

**Vision Agents Context Sent to Claude:**
- Current question text
- Candidate transcript so far
- Latest emotion (confident/nervous/confused/neutral/enthusiastic)
- Confidence score (0-100)
- Engagement level (high/medium/low)
- Filler word count
- Speech pace (words per minute)
- Long pause count

### GEMINI_API_KEY
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://makersuite.google.com/app/apikey
- **Model Used**: Gemini 1.5 Flash-8B
- **Free Tier**: 1000 requests per day
- **Description**: Google Gemini API key.
- **Used For**:
  - Emotion detection from video frames
  - Confidence scoring (0-100)
  - Engagement level detection (high/medium/low)
  - Body language analysis
  - Text embeddings for semantic search

**Vision Agents Frame Analysis:**
- Samples every 10 frames (configurable)
- Analyzes facial expressions and body language
- Returns structured emotion data
- Automatically reduces sampling when approaching rate limit

### GROQ_API_KEY
- **Type**: String
- **Required**: No (optional free-tier alternative)
- **Get From**: https://console.groq.com/
- **Model Used**: Llama 3.1 8B
- **Free Tier**: 14,400 requests per day
- **Description**: Groq API key for free-tier LLM alternative.
- **Used For**: Alternative to Claude for interview decisions (when USE_GROQ_DECISION=true).

---

## Vector Database & Memory

### PINECONE_API_KEY
- **Type**: String
- **Required**: No (optional, recommended)
- **Get From**: https://app.pinecone.io/
- **Description**: Pinecone API key for vector database.
- **Used For**: Semantic search for interview questions based on role and topics.

### PINECONE_INDEX
- **Type**: String
- **Default**: `interview-questions`
- **Description**: Name of the Pinecone index for question storage.

**Vision Agents Usage:**
- Fetches relevant questions using semantic search
- Filters by difficulty level
- Returns top 10 most relevant questions
- Shuffles and selects 5 for interview

### SUPERMEMORY_API_KEY
- **Type**: String
- **Required**: No (optional, recommended)
- **Get From**: https://supermemory.ai/
- **Description**: Supermemory API key for candidate memory.
- **Used For**:
  - Storing session summaries after interviews
  - Retrieving candidate history (last 5 sessions)
  - Personalizing interview greetings
  - Providing context to Claude for better decisions

**Vision Agents Session Summary Includes:**
- Overall performance assessment
- Identified strengths
- Areas for improvement
- Communication style feedback
- Emotion patterns observed
- Speech pattern observations

---

## Caching & Rate Limiting

### UPSTASH_REDIS_REST_URL
- **Type**: String (URL)
- **Required**: No (optional, recommended)
- **Get From**: https://console.upstash.com/
- **Description**: Upstash Redis REST API URL.
- **Used For**:
  - TTS audio caching (reduces ElevenLabs API calls)
  - Rate limiting counters
  - Session state caching

### UPSTASH_REDIS_REST_TOKEN
- **Type**: String
- **Required**: No (optional, recommended)
- **Get From**: https://console.upstash.com/
- **Description**: Upstash Redis authentication token.

**Vision Agents Caching:**
- Caches TTS audio with 24-hour TTL
- Tracks daily API usage per service
- Stores rate limit counters per candidate

---

## Voice Services

### DEEPGRAM_API_KEY
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://console.deepgram.com/
- **Model Used**: Nova-2
- **Description**: Deepgram API key for speech-to-text.
- **Used For**:
  - Real-time transcription of candidate speech
  - Interim results for responsive feedback
  - Final transcripts for analysis

**Vision Agents Integration:**
- Receives audio stream from Stream.io call
- Provides real-time transcript segments
- Forwards transcripts to SpeechProcessor for analysis
- Enables word counting for decision triggers

### ELEVENLABS_API_KEY
- **Type**: String
- **Required**: Yes (for Vision Agents)
- **Get From**: https://elevenlabs.io/
- **Model Used**: eleven_turbo_v2_5
- **Description**: ElevenLabs API key for text-to-speech.
- **Used For**:
  - AI voice generation for greetings
  - Speaking interview questions
  - Speaking intervention messages (interruptions, encouragement, hints)

**Vision Agents TTS Flow:**
- Generates natural-sounding AI voice
- Caches audio to reduce API calls
- Streams audio through Stream.io to candidate
- Falls back to text-only mode on failure

---

## Vision Agents Configuration

These variables control the behavior of the Vision Agents integration for real-time video interview analysis.

### VISION_AGENTS_FRAME_SAMPLE_RATE
- **Type**: Integer
- **Default**: `10`
- **Range**: 5-30
- **Description**: Sample every Nth frame for emotion detection.
- **Impact**:
  - Lower value = More frequent analysis, higher API costs
  - Higher value = Less frequent analysis, lower API costs
- **Recommendation**: 10 (samples 6 times per second at 60fps)
- **Auto-Adjustment**: Automatically increases to 20 when approaching Gemini rate limit

**Cost Calculation:**
- At 60fps video: 10 = 6 samples/sec = 360 samples/min = 21,600 samples/hour
- At rate 10: ~360 Gemini API calls per hour
- At rate 20: ~180 Gemini API calls per hour

### VISION_AGENTS_RATE_LIMIT_THRESHOLD
- **Type**: Integer
- **Default**: `900`
- **Range**: 800-1000
- **Description**: Gemini API request count threshold for automatic sampling reduction.
- **Gemini Free Tier**: 1000 requests per day
- **Behavior**: When daily request count exceeds this threshold, frame sampling rate is automatically doubled to conserve API quota.

### VISION_AGENTS_DECISION_WORD_THRESHOLD
- **Type**: Integer
- **Default**: `20`
- **Range**: 10-50
- **Description**: Minimum words in transcript before requesting AI decision from Claude.
- **Impact**:
  - Lower value = More responsive, higher Claude API costs
  - Higher value = Less responsive, lower Claude API costs
- **Recommendation**: 20 words (approximately 10-15 seconds of speech)

**Decision Trigger:**
- Accumulates transcript words
- When threshold reached, requests emotion + speech data
- Sends multimodal context to Claude for decision
- Executes action (CONTINUE, INTERRUPT, ENCOURAGE, NEXT, HINT)

### VISION_AGENTS_LONG_PAUSE_THRESHOLD
- **Type**: Float
- **Default**: `3.0`
- **Range**: 2.0-5.0
- **Unit**: Seconds
- **Description**: Duration of silence to consider as a "long pause" in speech pattern analysis.
- **Used For**:
  - Detecting candidate hesitation
  - Identifying thinking time
  - Triggering encouragement or hints
  - Speech pattern metrics

### VISION_AGENTS_MAX_SESSIONS_PER_DAY
- **Type**: Integer
- **Default**: `10`
- **Range**: 1-100
- **Description**: Maximum live interview sessions allowed per candidate per day.
- **Purpose**: Rate limiting and cost control
- **Enforcement**: Returns 429 status code when limit exceeded
- **Reset**: Midnight UTC

---

## Feature Flags

### USE_PINECONE
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable Pinecone vector search for questions.
- **Fallback**: Uses MongoDB default questions when false or on failure.

### USE_CLAUDE_DECISION
- **Type**: Boolean
- **Default**: `true`
- **Description**: Use Claude for interview decisions (high quality, paid).
- **Alternative**: Set to false and enable USE_GROQ_DECISION for free tier.

### USE_GROQ_DECISION
- **Type**: Boolean
- **Default**: `false`
- **Description**: Use Groq Llama 3.1 8B for interview decisions (free tier alternative).
- **Note**: Set USE_CLAUDE_DECISION=false when enabling this.

### USE_SUPERMEMORY
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable Supermemory for candidate memory and session summaries.
- **Fallback**: Stores summaries in MongoDB only when false or on failure.

### USE_VISION
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable Vision Agents for video analysis.
- **Impact**: When false, disables emotion detection and body language analysis.

---

## Environment Validation

The application validates all required environment variables on startup. Missing required variables will cause the application to log an error and exit.

### Required Variables (Core)
- `DATABASE_URL`
- `MONGODB_URI`
- `JWT_SECRET`

### Required Variables (Vision Agents)
- `STREAM_APP_ID`
- `STREAM_API_KEY`
- `STREAM_API_SECRET`
- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY` (or `GROQ_API_KEY` if using free tier)
- `DEEPGRAM_API_KEY`
- `ELEVENLABS_API_KEY`

### Optional Variables
- `PINECONE_API_KEY`
- `SUPERMEMORY_API_KEY`
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`
- `GROQ_API_KEY`

### Validation Endpoint

**GET /api/interview/validate-config**

Returns health status for each service:

```json
{
  "status": "healthy",
  "services": {
    "mongodb": "connected",
    "stream": "connected",
    "gemini": "connected",
    "claude": "connected",
    "deepgram": "connected",
    "elevenlabs": "connected",
    "pinecone": "connected",
    "supermemory": "connected"
  }
}
```

---

## Cost Optimization Tips

1. **Increase Frame Sampling Rate**: Set `VISION_AGENTS_FRAME_SAMPLE_RATE=15` or `20` to reduce Gemini API calls.

2. **Increase Decision Threshold**: Set `VISION_AGENTS_DECISION_WORD_THRESHOLD=30` to reduce Claude API calls.

3. **Use Free Tier LLM**: Set `USE_GROQ_DECISION=true` and `USE_CLAUDE_DECISION=false` to use free Groq API.

4. **Enable Caching**: Configure Redis to cache TTS audio and reduce ElevenLabs API calls.

5. **Limit Sessions**: Reduce `VISION_AGENTS_MAX_SESSIONS_PER_DAY` to control daily costs.

6. **Monitor Usage**: Check `/api/admin/usage-stats` endpoint regularly to track API consumption.

---

## Security Best Practices

1. **Never commit .env file**: Add `.env` to `.gitignore`.

2. **Use .env.example**: Commit `.env.example` with placeholder values only.

3. **Rotate secrets regularly**: Change API keys and secrets periodically.

4. **Restrict API key permissions**: Use minimum required permissions for each service.

5. **Use environment-specific keys**: Different keys for development, staging, production.

6. **Monitor for leaks**: Use tools like `git-secrets` to prevent accidental commits.

7. **Secure production deployment**: Use platform-specific secret management (Railway, Render, AWS Secrets Manager).

---

## Troubleshooting

### Application won't start
- Check all required variables are set
- Verify MongoDB and PostgreSQL connection strings
- Test API keys with validation endpoint

### Emotion detection not working
- Verify `GEMINI_API_KEY` is valid
- Check daily rate limit (1000 requests/day)
- Verify `USE_VISION=true`

### Video calls failing
- Verify Stream.io credentials (`STREAM_APP_ID`, `STREAM_API_KEY`, `STREAM_API_SECRET`)
- Check Stream.io dashboard for quota limits
- Test connection with Stream.io test endpoint

### AI decisions not working
- Verify `ANTHROPIC_API_KEY` or `GROQ_API_KEY` is valid
- Check which decision engine is enabled (`USE_CLAUDE_DECISION` or `USE_GROQ_DECISION`)
- Monitor Claude/Groq API usage and limits

### Voice not working
- Verify `DEEPGRAM_API_KEY` for STT
- Verify `ELEVENLABS_API_KEY` for TTS
- Check API quotas on respective dashboards
- Test with validation endpoint

---

## Support

For issues or questions:
1. Check this documentation
2. Review application logs
3. Test with `/api/health` endpoint
4. Check service dashboards for quota/limits
5. Consult service-specific documentation

---

**Last Updated**: 2024
**Version**: 1.0.0
