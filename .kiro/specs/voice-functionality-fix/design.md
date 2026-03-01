# Voice Functionality Fix - Bugfix Design

## Overview

The RoundZero AI Interview application's voice functionality is broken due to a deprecated Gemini model (`gemini-2.0-flash-lite`) that returns 404 errors. This prevents the AI from greeting users, asking questions, providing feedback, and progressing through interviews. The fix involves replacing the deprecated model with a valid Gemini model (`gemini-2.5-flash`) at two locations in `backend/agent/interviewer.py` (lines 162 and 759). This is a minimal, targeted fix that preserves all existing functionality while restoring voice interaction capabilities.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the system attempts to use the deprecated `gemini-2.0-flash-lite` model
- **Property (P)**: The desired behavior - the system successfully initializes and uses a valid Gemini model for LLM responses
- **Preservation**: All existing voice flow components (ElevenLabs TTS, Deepgram STT, Stream.io WebRTC, InterviewerAgent) must remain unchanged
- **InterviewerAgent**: The Vision Agents framework class in `backend/agent/interviewer.py` that manages the AI interview flow
- **LLM Initialization**: The process at line 162 where the Gemini model is instantiated for real-time speech-to-speech interaction
- **Dynamic Question Generation**: The fallback mechanism at line 759 that generates interview questions using Gemini models
- **gemini.LLM()**: The Vision Agents SDK method for initializing a Gemini language model
- **Response Time**: The target latency of <3 seconds per user interaction

## Bug Details

### Fault Condition

The bug manifests when the InterviewerAgent initializes or when the QuestionBank attempts to generate dynamic questions. The system uses the deprecated model `gemini-2.0-flash-lite` which no longer exists in Google's Gemini API v1beta, causing 404 errors that cascade into complete voice functionality failure.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type ModelInitializationAttempt
  OUTPUT: boolean
  
  RETURN input.model_name IN ['gemini-2.0-flash-lite', 'models/gemini-2.0-flash-lite-001']
         AND input.api_version == 'v1beta'
         AND input.initialization_context IN ['InterviewerAgent.__init__', 'QuestionBank._generate_dynamic_questions']
END FUNCTION
```

### Examples

- **Example 1 (InterviewerAgent Initialization)**: When a user starts an interview session, the `InterviewerAgent.__init__()` method at line 162 attempts to create `llm = gemini.LLM("gemini-2.0-flash-lite")`, which returns HTTP 404 error "models/gemini-2.0-flash-lite is not found for API version v1beta". The agent fails to initialize, preventing any voice interaction.

- **Example 2 (Question Generation Fallback)**: When the QuestionBank's `_generate_dynamic_questions()` method at line 759 iterates through model fallbacks, it attempts `models/gemini-2.0-flash-lite-001` as the second option, which also returns 404. This delays question generation and may cause timeouts.

- **Example 3 (Interview Start Flow)**: User clicks "Start Interview" → Backend calls `start_session()` → Agent initialization fails with 404 → No greeting audio is generated → User sees loading screen indefinitely → Response time exceeds 3 seconds (target) and can be indefinite.

- **Edge Case (All Models Fail)**: If both deprecated models fail and other fallbacks are unavailable, the system falls back to local questions, but the agent still cannot speak because the LLM initialization at line 162 is blocking and has no fallback mechanism.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- ElevenLabs TTS service must continue to generate audio using `client.text_to_speech.convert()` method
- Stream.io WebRTC must continue to handle audio/video transport (not WebSocket)
- Deepgram STT must continue to convert speech to text
- InterviewerAgent must continue to use Vision Agents SDK framework
- TTS caching mechanism must continue to optimize performance
- Interview flow sequence must remain: User speaks → Deepgram STT → Gemini LLM → ElevenLabs TTS → Stream.io WebRTC playback

**Scope:**
All inputs that do NOT involve Gemini model initialization should be completely unaffected by this fix. This includes:
- Audio streaming and playback mechanisms
- Speech-to-text transcription
- Text-to-speech audio generation
- WebRTC connection management
- Session state management
- Question scoring and feedback logic
- Database operations (Neon, MongoDB, Pinecone)
- Memory provider and context retrieval

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Deprecated Model Reference**: The code explicitly references `gemini-2.0-flash-lite` at line 162, which was deprecated by Google and removed from the Gemini API v1beta endpoint. This model name no longer resolves to a valid model.

2. **Hardcoded Model Name**: The InterviewerAgent initialization uses a hardcoded string `"gemini-2.0-flash-lite"` without any fallback mechanism or environment variable configuration, making it impossible to recover from model deprecation without code changes.

3. **Fallback List Contains Deprecated Model**: The `_generate_dynamic_questions()` method at line 759 includes `models/gemini-2.0-flash-lite-001` in its fallback list, which also returns 404 errors and wastes time before trying valid models.

4. **No Error Handling for Model Initialization**: The `gemini.LLM()` call at line 162 is not wrapped in try-except, so a 404 error causes the entire agent initialization to fail rather than falling back to an alternative model.

## Correctness Properties

Property 1: Fault Condition - Valid Model Initialization

_For any_ model initialization attempt where the system previously used `gemini-2.0-flash-lite` or `models/gemini-2.0-flash-lite-001`, the fixed code SHALL use `gemini-2.5-flash` or `models/gemini-2.5-flash` respectively, resulting in successful HTTP 200 responses from the Gemini API and functional LLM inference for voice interactions.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation - Non-LLM Component Behavior

_For any_ system component that is NOT the Gemini LLM initialization (TTS, STT, WebRTC, caching, database, session management), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing voice flow functionality and integration points.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct (deprecated model references):

**File**: `backend/agent/interviewer.py`

**Function**: `InterviewerAgent.__init__()` (line 162)

**Specific Changes**:
1. **Replace Deprecated Model in Agent Initialization**:
   - **Current**: `llm = gemini.LLM("gemini-2.0-flash-lite")  # Fast and lightweight`
   - **Fixed**: `llm = gemini.LLM("gemini-2.5-flash")  # Fast and stable`
   - **Rationale**: `gemini-2.5-flash` is the current standard fast model with proven stability and <3s response times

2. **Update Comment for Clarity**:
   - Change comment from "Fast and lightweight" to "Fast and stable"
   - Indicates the model is production-ready and actively maintained

**Function**: `QuestionBank._generate_dynamic_questions()` (line 759)

**Specific Changes**:
3. **Remove Deprecated Model from Fallback List**:
   - **Current**: 
     ```python
     models = [
         "models/gemini-2.5-flash-lite",
         "models/gemini-2.0-flash-lite-001",  # ← REMOVE THIS
         "models/gemini-flash-lite-latest",
         "models/gemini-2.5-flash",
     ]
     ```
   - **Fixed**:
     ```python
     models = [
         "models/gemini-2.5-flash-lite",
         "models/gemini-flash-lite-latest",
         "models/gemini-2.5-flash",
     ]
     ```
   - **Rationale**: Removes the 404-causing model from the fallback chain, reducing latency and preventing unnecessary API calls

4. **Reorder Fallback List for Optimal Performance**:
   - Keep `gemini-2.5-flash-lite` first (fastest, lowest cost)
   - Keep `gemini-flash-lite-latest` second (auto-updates to latest lite version)
   - Keep `gemini-2.5-flash` last (most stable fallback)

5. **No Changes to Error Handling**:
   - The existing try-except loop already handles model failures gracefully
   - No additional error handling needed since valid models will succeed

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (404 errors), then verify the fix works correctly and preserves existing behavior (successful initialization and unchanged voice flow).

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the deprecated model causes 404 errors and prevents voice functionality.

**Test Plan**: Write tests that attempt to initialize the InterviewerAgent and generate dynamic questions using the UNFIXED code. Run these tests to observe 404 failures and confirm the root cause.

**Test Cases**:
1. **Agent Initialization Test**: Attempt to create `InterviewerAgent` with deprecated model (will fail with 404 on unfixed code)
2. **Question Generation Test**: Call `_generate_dynamic_questions()` and observe it trying deprecated model (will fail with 404 on unfixed code)
3. **End-to-End Interview Start Test**: Start a full interview session and observe agent initialization failure (will timeout on unfixed code)
4. **Model Fallback Test**: Verify that the fallback list includes deprecated model at position 2 (will waste time on unfixed code)

**Expected Counterexamples**:
- HTTP 404 error: "models/gemini-2.0-flash-lite is not found for API version v1beta"
- Agent initialization fails and raises exception
- Interview session hangs indefinitely waiting for agent to join
- Response time exceeds 3 seconds (target) and can be 30+ seconds or timeout
- Possible causes: deprecated model name, no fallback mechanism, blocking initialization

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (model initialization attempts), the fixed function produces the expected behavior (successful initialization with valid model).

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := initialize_with_fixed_model(input)
  ASSERT result.status_code == 200
  ASSERT result.model_name IN ['gemini-2.5-flash', 'models/gemini-2.5-flash']
  ASSERT result.llm_instance IS NOT NULL
  ASSERT result.response_time < 3.0 seconds
END FOR
```

**Test Plan**: After applying the fix, run the same initialization tests and verify they succeed with HTTP 200 responses and functional LLM instances.

**Test Cases**:
1. **Fixed Agent Initialization**: Create `InterviewerAgent` and verify LLM is initialized with `gemini-2.5-flash`
2. **Fixed Question Generation**: Call `_generate_dynamic_questions()` and verify it uses valid models only
3. **Response Time Validation**: Measure initialization time and confirm <3s latency
4. **Model API Call Success**: Verify HTTP 200 responses from Gemini API for all model calls

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-LLM components), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT fixed_system(input) = original_system(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-LLM components

**Test Plan**: Observe behavior on UNFIXED code first for TTS, STT, WebRTC, and other components, then write property-based tests capturing that behavior.

**Test Cases**:
1. **TTS Preservation**: Verify ElevenLabs TTS continues to generate audio with same quality and format after fix
2. **STT Preservation**: Verify Deepgram STT continues to transcribe speech with same accuracy after fix
3. **WebRTC Preservation**: Verify Stream.io WebRTC continues to stream audio/video without changes after fix
4. **Session Management Preservation**: Verify session state, question progression, and scoring logic unchanged after fix
5. **Database Preservation**: Verify Neon, MongoDB, and Pinecone operations unchanged after fix
6. **Caching Preservation**: Verify TTS caching mechanism continues to work identically after fix

### Unit Tests

- Test `InterviewerAgent.__init__()` with valid model name and verify successful initialization
- Test `QuestionBank._generate_dynamic_questions()` with updated fallback list and verify no 404 errors
- Test model initialization response time is <3 seconds
- Test that deprecated model names are not present in any code paths
- Test error handling for network failures (not model deprecation)

### Property-Based Tests

- Generate random session configurations and verify agent initializes successfully for all
- Generate random question generation requests and verify valid models are always used
- Test that response times remain <3s across many initialization attempts
- Verify that all voice flow components (TTS, STT, WebRTC) produce identical outputs before and after fix

### Integration Tests

- Test full interview flow: start session → agent joins → greeting plays → question asked → user answers → feedback given → next question
- Test that voice interactions feel dynamic and responsive with <3s latency per interaction
- Test that all questions are asked and answered successfully
- Test that interview completion and report generation work correctly
- Test that the fix works across different environments (development, staging, production)
