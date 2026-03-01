# Bugfix Requirements Document

## Introduction

This document addresses critical bugs in the RoundZero AI interview system that prevent the core interview flow from functioning. Users report that AI voice is not audible and questions do not progress automatically after the candidate finishes speaking, causing the interview to stall on the first question. These bugs break the fundamental user experience of conducting a voice-based AI interview.

The system uses Gemini Realtime (speech-to-speech) with function tools (`advance_question`, `end_interview`) to manage interview flow. The backend agent joins Stream.io calls and publishes audio tracks, while the frontend uses browser TTS as a fallback. The expected flow is: AI greets → asks question → user answers → Gemini detects turn completion → calls `advance_question` → AI speaks feedback + next question → repeat for 8 questions.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the AI agent speaks a message via Gemini Realtime THEN the frontend does not play any audible voice output despite backend logs showing successful TTS generation and audio track publishing

1.2 WHEN the user finishes answering a question and stops speaking for 10+ seconds THEN the interview remains stuck on the current question without advancing to the next question

1.3 WHEN the backend broadcasts `agent_transcript` or `agent_message` SSE events THEN the browser TTS fallback does not trigger or fails silently without error messages

1.4 WHEN Gemini Realtime detects the user has finished speaking (turn detection) THEN the LLM does not call the `advance_question` function tool to progress the interview

1.5 WHEN questions are generated for the interview session THEN the questions do not match the selected role and topics from the setup screen

### Expected Behavior (Correct)

2.1 WHEN the AI agent speaks a message via Gemini Realtime THEN the frontend SHALL play audible voice output either through Stream.io audio tracks or browser TTS fallback

2.2 WHEN the user finishes answering a question and Gemini Realtime detects turn completion THEN the system SHALL automatically call `advance_question(score, feedback)` and progress to the next question within 2-3 seconds

2.3 WHEN the backend broadcasts `agent_transcript` or `agent_message` SSE events THEN the browser TTS SHALL speak the text using `window.speechSynthesis.speak()` with proper error handling and state management

2.4 WHEN Gemini Realtime is initialized THEN the LLM SHALL be configured with turn detection enabled and function tools (`advance_question`, `end_interview`) properly registered

2.5 WHEN questions are generated for the interview session THEN the questions SHALL match the role and topics selected by the user in the setup screen using the dynamic generation system

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the backend agent joins a Stream.io call THEN the system SHALL CONTINUE TO publish audio tracks and maintain WebRTC connection status

3.2 WHEN the user speaks into the microphone THEN the system SHALL CONTINUE TO transcribe speech and accumulate it in the session answer buffer

3.3 WHEN the backend broadcasts SSE events THEN the frontend SHALL CONTINUE TO receive and log all event types (`transcript`, `agent_message`, `next_question`, etc.)

3.4 WHEN the interview completes all 8 questions THEN the system SHALL CONTINUE TO call `end_interview` and broadcast the final scorecard

3.5 WHEN the user manually submits an answer in text mode (non-Stream) THEN the system SHALL CONTINUE TO process the answer and advance questions via the REST API endpoint
