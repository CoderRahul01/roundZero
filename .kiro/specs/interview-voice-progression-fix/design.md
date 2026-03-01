# Interview Voice and Progression Bugfix Design

## Overview

This design addresses three critical bugs preventing the RoundZero AI interview system from functioning: (1) AI voice is inaudible despite backend audio generation, (2) questions do not progress automatically after user answers, and (3) generated questions don't match user-selected role/topics. The root causes span frontend audio playback, Gemini Realtime turn detection configuration, and question generation logic. The fix strategy involves adding explicit turn detection configuration to Gemini Realtime, implementing comprehensive error handling for browser TTS with autoplay policy compliance, and adding logging/fallbacks to question generation.

## Glossary

- **Bug_Condition (C)**: The conditions that trigger the bugs - when AI speaks but no audio plays, when user finishes speaking but interview doesn't advance, when questions don't match selected topics
- **Property (P)**: The desired behavior - audible AI voice output, automatic question progression within 2-3 seconds of turn completion, questions matching user selections
- **Preservation**: Existing Stream.io WebRTC connection, speech transcription, SSE event broadcasting, manual text mode submission
- **Gemini Realtime**: Google's speech-to-speech LLM API used for real-time voice interaction
- **Turn Detection**: Gemini Realtime's mechanism to detect when a speaker has finished talking (end of turn)
- **Function Tools**: Python functions registered with Gemini LLM that it can call (`advance_question`, `end_interview`)
- **Browser TTS**: Web Speech API's `window.speechSynthesis` used as fallback for AI voice output
- **SSE (Server-Sent Events)**: One-way event stream from backend to frontend for real-time updates
- **Stream.io**: WebRTC platform used for audio/video calls between user and AI agent
- **Autoplay Policy**: Browser security policy requiring user interaction before playing audio

## Bug Details

### Fault Condition

The bugs manifest in three distinct scenarios:

**Voice Bug**: When the AI agent speaks a message via Gemini Realtime, the backend successfully generates TTS and publishes audio tracks to Stream.io, but the frontend does not play any audible voice output. The browser TTS fallback either doesn't trigger or fails silently.

**Progression Bug**: When the user finishes answering a question and stops speaking for 10+ seconds, Gemini Realtime should detect turn completion and call the `advance_question` function tool, but the interview remains stuck on the current question indefinitely.

**Question Generation Bug**: When questions are generated for the interview session, they do not match the role and topics selected by the user in the setup screen, resulting in generic or irrelevant questions.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type InterviewEvent
  OUTPUT: boolean
  
  RETURN (
    // Voice bug condition
    (input.type == "agent_message" 
     AND input.backend_audio_generated == true 
     AND input.frontend_audio_played == false)
    
    OR
    
    // Progression bug condition
    (input.type == "user_speech_end" 
     AND input.silence_duration > 10_seconds 
     AND input.advance_question_called == false)
    
    OR
    
    // Question generation bug condition
    (input.type == "question_generated"
     AND input.question_topics NOT IN input.user_selected_topics)
  )
END FUNCTION
```

### Examples

**Voice Bug Examples:**
- Backend logs show "TTS generated: 'Hello, let's begin the interview'" and "Audio track published to Stream.io", but user hears nothing
- SSE event `agent_message` arrives at frontend with text "Tell me about your experience", browser console shows the event, but `speechSynthesis.speak()` never executes or fails silently
- User clicks "Start Interview" but browser autoplay policy blocks audio, no error message shown to user

**Progression Bug Examples:**
- User answers "I have 5 years of Python experience" and stops speaking, 15 seconds pass, interview still shows "Question 1/8" without advancing
- Backend logs show user transcript accumulated in `answer_buffer`, but no log of `advance_question` function being called by Gemini
- Gemini Realtime continues listening but never detects end-of-turn, waiting indefinitely for more user speech

**Question Generation Bug Examples:**
- User selects role="Backend Engineer" and topics=["Python", "APIs"], but receives questions about frontend frameworks
- Dynamic generation with Gemini returns generic questions like "Tell me about yourself" instead of role-specific technical questions
- Fallback to MongoDB/Pinecone returns questions from wrong category due to missing role/topic filters

**Edge Cases:**
- User grants microphone permission but denies autoplay permission - voice should still work after first user interaction
- Network latency causes SSE events to arrive out of order - system should handle gracefully
- Gemini API rate limit hit during question generation - should fallback to cached questions without error

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Stream.io WebRTC connection establishment and audio track publishing must continue to work exactly as before
- Speech transcription via Deepgram STT and accumulation in `answer_buffer` must remain unchanged
- SSE event broadcasting from backend (all event types: `transcript`, `agent_message`, `next_question`, `vision`, etc.) must continue working
- Manual text mode submission via REST API endpoint `/api/interview/submit-answer` must remain functional
- Interview completion flow calling `end_interview` and broadcasting final scorecard must be preserved

**Scope:**
All inputs that do NOT involve AI voice playback, automatic question progression, or question generation should be completely unaffected by this fix. This includes:
- User microphone input and speech recognition
- Manual button clicks to submit answers or end interview
- Video emotion analysis and vision processing
- Session state management and database operations
- Authentication and authorization flows

## Hypothesized Root Cause

Based on the bug description and code analysis, the most likely issues are:

### Voice Bug Root Causes

1. **Browser Autoplay Policy Violation**: The browser TTS code in `InterviewScreen.tsx` (lines 312-320) attempts to call `window.speechSynthesis.speak()` without prior user interaction, which modern browsers block by default. The code has no error handling for this scenario and fails silently.

2. **Stream.io Audio Track Not Consumed**: The backend publishes audio tracks to Stream.io, but the frontend may not be properly subscribing to and playing these tracks. The browser TTS is intended as a fallback, but if Stream.io audio should be primary, the frontend WebRTC setup may be incomplete.

3. **SSE Event Timing Issue**: The `agent_message` SSE event may arrive before the frontend has initialized `speechSynthesis` or before the user has interacted with the page, causing the TTS call to be ignored.

4. **Missing Error Logging**: The `utterance.onerror` callback (line 322) sets `isAiSpeaking` to false but doesn't log the error or notify the user, making debugging impossible.

### Progression Bug Root Causes

1. **Missing Turn Detection Configuration**: The Gemini Realtime LLM initialization (line 162) uses `gemini.LLM("gemini-2.5-flash")` with no explicit turn detection configuration. Gemini may require explicit parameters like `turn_detection={"type": "server_vad"}` to enable automatic end-of-turn detection.

2. **Function Tool Registration Issue**: While `advance_question` is registered with `@llm.register_function()` decorator (lines 174-235), Gemini may not understand when to call it without explicit turn detection signals or additional system prompt instructions.

3. **System Prompt Ambiguity**: The system prompt in `_build_interviewer_instructions()` may not clearly instruct Gemini to call `advance_question` immediately after the user finishes speaking, leading to indefinite waiting.

4. **Event Loop Blocking**: The `advance_question` function is async but may not be properly awaited or scheduled, causing it to never execute even if Gemini attempts to call it.

### Question Generation Bug Root Causes

1. **Missing Role/Topic Context**: The `_generate_dynamic_questions()` function (line 662) may not be receiving or using the `config.role` and `config.topics` parameters when constructing the Gemini prompt.

2. **Fallback Logic Ignoring Filters**: When dynamic generation fails and the system falls back to MongoDB or Pinecone, the queries may not filter by role/topics, returning generic questions instead.

3. **Prompt Engineering Issue**: The Gemini prompt for question generation may be too generic or not emphasize the importance of matching the specified role and topics.

4. **Silent Failure Swallowing**: Try/except blocks in question generation may be catching errors and falling back without logging, making it impossible to diagnose why dynamic generation isn't working.

## Correctness Properties

Property 1: Fault Condition - AI Voice Audibility

_For any_ AI agent message where the backend successfully generates TTS audio and broadcasts an `agent_message` SSE event, the frontend SHALL play audible voice output either through Stream.io audio tracks or browser TTS fallback, with proper error handling and user notification if audio playback fails due to browser policies.

**Validates: Requirements 2.1, 2.3**

Property 2: Fault Condition - Automatic Question Progression

_For any_ user speech input where Gemini Realtime detects turn completion (user has finished speaking), the system SHALL automatically call `advance_question(score, feedback)` within 2-3 seconds and progress to the next question, with the LLM configured for proper turn detection.

**Validates: Requirements 2.2, 2.4**

Property 3: Fault Condition - Question Relevance

_For any_ interview session where the user has selected a specific role and topics in the setup screen, the generated questions SHALL match those selections, with dynamic generation prioritized and fallbacks filtered by role/topic.

**Validates: Requirements 2.5**

Property 4: Preservation - Existing Functionality

_For any_ input that does NOT involve AI voice playback, automatic question progression, or question generation (manual submissions, transcription, SSE events, WebRTC connection), the system SHALL produce exactly the same behavior as the original code, preserving all existing functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

#### File 1: `backend/agent/interviewer.py`

**Function**: `InterviewerAgent.__init__()`

**Specific Changes**:

1. **Add Turn Detection Configuration**: Modify Gemini LLM initialization (line 162) to explicitly enable turn detection:
   ```python
   llm = gemini.LLM(
       "gemini-2.5-flash",
       turn_detection={"type": "server_vad", "threshold": 0.5}
   )
   ```
   This tells Gemini to use server-side voice activity detection to automatically detect when the user has finished speaking.

2. **Enhance System Prompt**: Update `_build_interviewer_instructions()` to explicitly instruct Gemini to call `advance_question` immediately after evaluating the user's answer:
   ```python
   instructions += "\n\nIMPORTANT: After the candidate finishes answering, immediately call advance_question(score, feedback) to progress to the next question. Do not wait for additional input."
   ```

3. **Add Function Call Logging**: Add logging inside `advance_question` function (line 174) to track when it's called:
   ```python
   logger.info(f"🔄 advance_question called: score={score}, feedback={feedback[:50]}...")
   ```

4. **Add Turn Detection Event Logging**: Subscribe to turn detection events to verify Gemini is detecting end-of-turn:
   ```python
   @self.events.subscribe
   async def on_turn_complete(event: TurnCompleteEvent):
       logger.info(f"🎤 Turn complete detected for user")
       await self.service.broadcast(self.session_id, {
           "type": "turn_complete",
           "timestamp": time.time()
       })
   ```

#### File 2: `backend/agent/interviewer.py`

**Function**: `_generate_dynamic_questions()`

**Specific Changes**:

1. **Pass Role/Topic to Prompt**: Ensure the Gemini prompt includes role and topics from `config`:
   ```python
   prompt = f"""Generate {count} technical interview questions for a {config.role} position.
   Focus on these topics: {', '.join(config.topics)}.
   Difficulty: {config.difficulty}
   
   Requirements:
   - Questions MUST be specific to {config.role} role
   - Questions MUST cover the topics: {', '.join(config.topics)}
   - Avoid generic questions like "Tell me about yourself"
   """
   ```

2. **Add Generation Logging**: Log the generation attempt and result:
   ```python
   logger.info(f"🎯 Generating {count} questions for role={config.role}, topics={config.topics}")
   # ... after generation ...
   logger.info(f"✅ Generated {len(questions)} questions: {[q.question[:50] for q in questions]}")
   ```

3. **Add Fallback Filtering**: When falling back to MongoDB/Pinecone, filter by role and topics:
   ```python
   # In MongoDB fallback
   questions = await db.questions.find({
       "role": config.role,
       "topics": {"$in": config.topics}
   }).limit(count).to_list()
   ```

4. **Log Fallback Usage**: Track which source provided questions:
   ```python
   logger.warning(f"⚠️ Dynamic generation failed, falling back to MongoDB for role={config.role}")
   ```

#### File 3: `frontend/src/screens/InterviewScreen.tsx`

**Function**: SSE event listener for `agent_message`

**Specific Changes**:

1. **Add Autoplay Policy Handling**: Wrap TTS in user interaction check and provide fallback:
   ```typescript
   // Add state for autoplay permission
   const [audioPermissionGranted, setAudioPermissionGranted] = useState(false);
   
   // Request audio permission on first user interaction
   const requestAudioPermission = async () => {
     try {
       const utterance = new SpeechSynthesisUtterance("");
       window.speechSynthesis.speak(utterance);
       setAudioPermissionGranted(true);
       console.log("✅ Audio permission granted");
     } catch (error) {
       console.error("❌ Audio permission denied:", error);
       setAudioPermissionGranted(false);
     }
   };
   ```

2. **Add Comprehensive Error Handling**: Log all TTS errors and notify user:
   ```typescript
   if (streamEnabled && typeof window !== "undefined" && "speechSynthesis" in window) {
     try {
       window.speechSynthesis.cancel();
       const utterance = new SpeechSynthesisUtterance(data.text);
       utterance.rate = 1.0;
       utterance.pitch = 1.0;
       
       utterance.onstart = () => {
         console.log("🔊 TTS started:", data.text.substring(0, 50));
         setIsAiSpeaking(true);
       };
       
       utterance.onend = () => {
         console.log("✅ TTS completed");
         setIsAiSpeaking(false);
       };
       
       utterance.onerror = (event) => {
         console.error("❌ TTS error:", event.error, event);
         setIsAiSpeaking(false);
         // Show user notification
         setErrorMessage(`Voice playback failed: ${event.error}. Please check browser permissions.`);
       };
       
       window.speechSynthesis.speak(utterance);
       console.log("🎤 TTS speak() called");
     } catch (error) {
       console.error("❌ TTS exception:", error);
       setErrorMessage("Voice playback failed. Please enable audio in your browser.");
     }
   } else {
     console.warn("⚠️ TTS not available: streamEnabled=", streamEnabled, "speechSynthesis=", typeof window !== "undefined" && "speechSynthesis" in window);
   }
   ```

3. **Add User Interaction Trigger**: Add a "Start Interview" button that requests audio permission:
   ```typescript
   <button onClick={async () => {
     await requestAudioPermission();
     startInterview();
   }}>
     Start Interview
   </button>
   ```

4. **Add Visual Feedback**: Show audio status to user:
   ```typescript
   {!audioPermissionGranted && (
     <div className="audio-warning">
       ⚠️ Audio permission required. Click "Start Interview" to enable voice.
     </div>
   )}
   ```

#### File 4: `backend/agent/interviewer.py`

**Function**: `on_transcript` event handler

**Specific Changes**:

1. **Add Silence Detection**: Track silence duration to help debug turn detection:
   ```python
   @self.events.subscribe
   async def on_transcript(event: Any):
       # ... existing code ...
       
       # Track silence for debugging
       current_time = time.time()
       silence_duration = current_time - self.last_transcript_time
       if silence_duration > 5.0:
           logger.info(f"🔇 Silence detected: {silence_duration:.1f}s since last transcript")
       
       self.last_transcript_time = current_time
   ```

2. **Add Turn Detection Fallback**: If Gemini doesn't call `advance_question` after 15 seconds of silence, log a warning:
   ```python
   # In InterviewerAgent class
   async def check_turn_timeout(self):
       """Monitor for stuck turns and log warnings."""
       while True:
           await asyncio.sleep(5)
           sess = self.service.sessions.get(self.session_id)
           if not sess or sess.completed:
               break
           
           silence_duration = time.time() - self.last_transcript_time
           if silence_duration > 15.0 and sess.answer_buffer.strip() and not self.is_speaking:
               logger.warning(f"⚠️ Possible stuck turn: {silence_duration:.1f}s silence with answer buffer: {sess.answer_buffer[:100]}")
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate the three bug scenarios and observe failures on the UNFIXED code to understand the root causes.

**Test Cases**:

1. **Voice Bug Test - Autoplay Policy**: Open interview in fresh browser session, start interview without user interaction, verify TTS fails silently (will fail on unfixed code - no error logged)

2. **Voice Bug Test - SSE Event**: Mock `agent_message` SSE event, verify browser TTS is called, check for errors in console (will fail on unfixed code - no error handling)

3. **Progression Bug Test - Turn Detection**: Simulate user speaking then 15 seconds of silence, verify `advance_question` is never called (will fail on unfixed code - no turn detection config)

4. **Progression Bug Test - Function Tool**: Mock Gemini LLM response, verify `advance_question` function is registered and callable (may pass - registration works, but Gemini doesn't call it)

5. **Question Generation Bug Test - Role Mismatch**: Request questions for role="Backend Engineer" topics=["Python"], verify generated questions are generic or frontend-focused (will fail on unfixed code - no role/topic filtering)

6. **Question Generation Bug Test - Fallback**: Force dynamic generation to fail, verify MongoDB fallback returns role-specific questions (will fail on unfixed code - no filtering in fallback)

**Expected Counterexamples**:
- Browser console shows "speechSynthesis.speak() called" but no audio plays, no error logged
- Backend logs show user transcript accumulated but no "advance_question called" log after 15+ seconds
- Generated questions include "Explain React hooks" when user selected "Backend Engineer" role
- Possible causes: missing turn detection config, autoplay policy blocking, missing role/topic filters

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixed_interview_system(input)
  ASSERT expectedBehavior(result)
END FOR
```

**Specific Fix Validation Tests**:

1. **Voice Fix Validation**: 
   - Start interview with user interaction, verify TTS plays audibly
   - Start interview without user interaction, verify error message shown to user
   - Mock TTS error, verify error logged and user notified

2. **Progression Fix Validation**:
   - Simulate user answer + 3 seconds silence, verify `advance_question` called within 5 seconds
   - Check backend logs for "Turn complete detected" and "advance_question called" messages
   - Verify frontend receives `next_question` SSE event and updates UI

3. **Question Generation Fix Validation**:
   - Request questions for specific role/topics, verify all questions match criteria
   - Force dynamic generation failure, verify fallback questions match role/topics
   - Check logs for "Generating questions for role=X, topics=Y" messages

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT original_system(input) = fixed_system(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-voice/non-progression flows, then write property-based tests capturing that behavior.

**Test Cases**:

1. **Manual Text Mode Preservation**: Submit answer via REST API `/api/interview/submit-answer`, verify question advances exactly as before (no Stream.io or TTS involved)

2. **Transcription Preservation**: Speak into microphone, verify transcript appears in UI and accumulates in `answer_buffer` exactly as before

3. **SSE Event Preservation**: Verify all SSE event types (`transcript`, `vision`, `question_scored`, `interview_complete`) continue to broadcast and be received

4. **WebRTC Connection Preservation**: Verify Stream.io connection establishment, audio track publishing, and connection status monitoring work exactly as before

5. **Session State Preservation**: Verify session creation, question loading, result saving, and completion flow work exactly as before

6. **Vision Processing Preservation**: Verify emotion analysis and vision stats continue to update and broadcast exactly as before

### Unit Tests

- Test Gemini LLM initialization with turn detection config
- Test `advance_question` function in isolation with mock session
- Test `_generate_dynamic_questions` with various role/topic combinations
- Test browser TTS error handling with mocked `speechSynthesis` API
- Test SSE event parsing and handling in frontend
- Test autoplay permission request flow

### Property-Based Tests

- Generate random interview sessions with various roles/topics, verify all generated questions match criteria
- Generate random SSE event sequences, verify frontend handles all events correctly
- Generate random user speech patterns (short answers, long answers, silence), verify turn detection works consistently
- Generate random browser permission states, verify audio playback handles all cases gracefully

### Integration Tests

- Test full interview flow: start → AI greets → user answers → auto-advance → repeat 8 times → completion
- Test voice flow: AI speaks → verify audio plays → user speaks → verify transcription → verify auto-advance
- Test question generation flow: select role/topics → start interview → verify all 8 questions match criteria
- Test error recovery: simulate TTS failure → verify error shown → verify interview can continue
- Test browser compatibility: test in Chrome, Firefox, Safari with various permission states
