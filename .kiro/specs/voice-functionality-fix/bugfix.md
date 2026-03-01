# Bugfix Requirements Document

## Introduction

The RoundZero AI Interview application's voice functionality is non-functional due to a deprecated Gemini model (`gemini-2.0-flash-lite`) that returns 404 errors. This breaks the entire interview flow, preventing the AI from greeting users, asking questions, providing feedback, and progressing through the interview. The system is slow and unresponsive, failing to deliver the expected dynamic interview experience.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the interview session starts THEN the system uses deprecated model `gemini-2.0-flash-lite` which returns 404 error "models/gemini-2.0-flash-lite is not found for API version v1beta"

1.2 WHEN the LLM fails with 404 error THEN the AI voice does not work at the start of the interview

1.3 WHEN the LLM cannot respond THEN the AI does not ask the first question

1.4 WHEN the user answers a question THEN the system does not move to the next question automatically

1.5 WHEN the LLM is unavailable THEN the overall system becomes slow and non-dynamic with no responses

1.6 WHEN the interview flow is broken THEN response time exceeds 3 seconds (target) and can be indefinite

### Expected Behavior (Correct)

2.1 WHEN the interview session starts THEN the system SHALL use a valid Gemini model (e.g., `gemini-2.5-flash` or `gemini-2.5-flash-lite`) that returns successful responses

2.2 WHEN the LLM responds successfully THEN the AI voice SHALL greet the user immediately when the interview starts

2.3 WHEN the greeting completes THEN the AI SHALL ask the first question automatically

2.4 WHEN the user finishes answering THEN the AI SHALL provide feedback and move to the next question automatically

2.5 WHEN the LLM is available and responding THEN the system SHALL feel dynamic and responsive with continuous interaction flow

2.6 WHEN processing user interactions THEN response time SHALL be under 3 seconds per interaction

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the TTS service generates audio THEN the system SHALL CONTINUE TO use ElevenLabs API with `client.text_to_speech.convert()` method

3.2 WHEN audio is transmitted THEN the system SHALL CONTINUE TO use Stream.io WebRTC for audio/video transport (not WebSocket)

3.3 WHEN the interview progresses THEN the system SHALL CONTINUE TO use Deepgram STT for speech-to-text conversion

3.4 WHEN questions are managed THEN the system SHALL CONTINUE TO use the InterviewerAgent from Vision Agents SDK

3.5 WHEN audio is cached THEN the system SHALL CONTINUE TO use the existing TTS caching mechanism for performance optimization

3.6 WHEN the interview flow executes THEN the system SHALL CONTINUE TO follow the sequence: User speaks → Deepgram STT → Gemini LLM → ElevenLabs TTS → Stream.io WebRTC playback
