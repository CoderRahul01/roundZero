# Implementation Plan

- [ ] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Deprecated Model Causes 404 Errors
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For this deterministic bug, scope the property to the concrete failing cases: model initialization with `gemini-2.0-flash-lite` at line 162 and `models/gemini-2.0-flash-lite-001` at line 759
  - Test that `InterviewerAgent.__init__()` with deprecated model `gemini-2.0-flash-lite` returns HTTP 404 error
  - Test that `QuestionBank._generate_dynamic_questions()` attempts deprecated model `models/gemini-2.0-flash-lite-001` in fallback list
  - Test that agent initialization fails and raises exception on unfixed code
  - Test that interview session hangs or times out when agent cannot initialize
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found: HTTP 404 errors, initialization failures, timeout durations
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-LLM Component Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-LLM components (TTS, STT, WebRTC, caching, session management)
  - Observe: ElevenLabs TTS generates audio with specific format and quality on unfixed code
  - Observe: Deepgram STT transcribes speech with specific accuracy on unfixed code
  - Observe: Stream.io WebRTC streams audio/video with specific configuration on unfixed code
  - Observe: TTS caching mechanism stores and retrieves cached audio on unfixed code
  - Observe: Session state management tracks interview progress on unfixed code
  - Write property-based tests: for all non-LLM operations, behavior matches observed baseline (from Preservation Requirements in design)
  - Property-based testing generates many test cases for stronger guarantees
  - Verify tests pass on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 3. Fix for deprecated Gemini model causing voice functionality failure

  - [x] 3.1 Replace deprecated model in InterviewerAgent initialization (line 162)
    - Change `llm = gemini.LLM("gemini-2.0-flash-lite")` to `llm = gemini.LLM("gemini-2.5-flash")`
    - Update comment from "Fast and lightweight" to "Fast and stable"
    - Verify the change is at line 162 in `backend/agent/interviewer.py`
    - _Bug_Condition: isBugCondition(input) where input.model_name == "gemini-2.0-flash-lite" AND input.initialization_context == "InterviewerAgent.__init__"_
    - _Expected_Behavior: result.status_code == 200 AND result.model_name == "gemini-2.5-flash" AND result.response_time < 3.0 seconds_
    - _Preservation: All TTS, STT, WebRTC, caching, and session management components unchanged_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Remove deprecated model from fallback list (line 759)
    - Remove `"models/gemini-2.0-flash-lite-001"` from the models list in `_generate_dynamic_questions()`
    - Keep fallback order: `gemini-2.5-flash-lite` → `gemini-flash-lite-latest` → `gemini-2.5-flash`
    - Verify the change is at line 759 in `backend/agent/interviewer.py`
    - _Bug_Condition: isBugCondition(input) where input.model_name == "models/gemini-2.0-flash-lite-001" AND input.initialization_context == "QuestionBank._generate_dynamic_questions"_
    - _Expected_Behavior: Fallback list contains only valid models, reducing latency and preventing 404 errors_
    - _Preservation: Question generation logic and error handling unchanged_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Valid Model Initialization Succeeds
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - Verify `InterviewerAgent.__init__()` succeeds with HTTP 200 response
    - Verify `QuestionBank._generate_dynamic_questions()` uses only valid models
    - Verify agent initialization completes in <3 seconds
    - Verify interview session starts successfully without timeouts
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-LLM Component Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - Verify ElevenLabs TTS continues to generate audio identically
    - Verify Deepgram STT continues to transcribe speech identically
    - Verify Stream.io WebRTC continues to stream audio/video identically
    - Verify TTS caching mechanism continues to work identically
    - Verify session state management continues to work identically
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
