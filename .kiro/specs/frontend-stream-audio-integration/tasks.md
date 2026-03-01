# Implementation Plan: Frontend Stream.io Audio Integration

## Overview

This plan implements complete Stream.io Video SDK integration in the React frontend to enable real-time bidirectional audio communication between users and the AI interviewer. The implementation follows a vertical slice approach: backend API → custom hook → component integration → styling → testing.

## Tasks

- [x] 1. Update backend API to include stream_api_key in response
  - Modify StartLiveSessionResponse model to include stream_api_key field
  - Update /api/interview/start-live-session endpoint to return stream_api_key from environment
  - _Requirements: 1.1_

- [ ]* 1.1 Write unit test for backend API response
  - Test that stream_api_key is included in response
  - Test that stream_api_key matches environment variable
  - _Requirements: 1.1_

- [x] 2. Create useStreamAudio custom hook - Core initialization
  - [x] 2.1 Create hook file with TypeScript interfaces
    - Define UseStreamAudioOptions interface
    - Define UseStreamAudioReturn interface
    - Define ConnectionStatus type
    - Define StreamError interface
    - _Requirements: 1.2, 1.3_

  - [x] 2.2 Implement state management and refs
    - Add state: audioLevel, connectionStatus, error, isAgentConnected
    - Add refs: clientRef, callRef, audioContextRef, analyserRef, animationFrameRef, audioElementRef
    - _Requirements: 1.5_

  - [x] 2.3 Implement StreamVideoClient initialization
    - Create useEffect for client initialization
    - Initialize StreamVideoClient with apiKey, token, userId
    - Store client in ref to prevent re-initialization
    - Handle initialization errors with error state
    - _Requirements: 1.2, 1.3, 1.4, 1.5_

  - [ ]* 2.4 Write property test for client initialization
    - **Property 1: Client Initialization with Valid Credentials**
    - **Validates: Requirements 1.2, 1.3, 1.5**

- [ ] 3. Checkpoint - Verify hook initialization
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement call joining with retry logic
  - [x] 4.1 Create joinCall function with exponential backoff
    - Create call reference with type "interview" and callId
    - Implement join() with audio enabled
    - Add retry logic: 3 attempts with 1s, 2s, 4s delays
    - Handle join errors and update connection status
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 4.2 Write property test for call joining
    - **Property 2: Call Creation and Joining**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [ ]* 4.3 Write unit tests for retry logic
    - Test successful join on first attempt
    - Test retry with exponential backoff
    - Test failure after 3 retries
    - _Requirements: 2.5, 2.6_

- [ ] 5. Implement participant event handling
  - [x] 5.1 Create setupEventListeners function
    - Subscribe to participant.joined events
    - Detect agent participant by userId === "agent"
    - Update isAgentConnected state when agent joins
    - Subscribe to connection.changed events for reconnection
    - _Requirements: 3.1, 3.2, 7.5_

  - [ ]* 5.2 Write property test for participant events
    - **Property 3: Participant Event Subscription**
    - **Validates: Requirements 3.1, 3.2**

- [ ] 6. Checkpoint - Verify connection handling
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement audio track subscription and playback
  - [x] 7.1 Create subscribeToAgentAudio function
    - Filter participant tracks for kind === "audio"
    - Validate track is not muted and readyState === "live"
    - Select most recent track if multiple tracks exist
    - Create HTMLAudioElement with autoplay=true
    - Attach track to audio.srcObject via MediaStream
    - Handle playback errors with user interaction fallback
    - _Requirements: 3.3, 3.4, 3.5, 3.6, 3.7, 10.1, 10.2, 10.4_

  - [ ]* 7.2 Write property test for audio track filtering
    - **Property 4: Audio Track Filtering and Setup**
    - **Validates: Requirements 3.3, 3.4, 3.6**

  - [ ]* 7.3 Write property test for track validation
    - **Property 13: Audio Track Validation**
    - **Validates: Requirements 10.1, 10.2**

  - [ ]* 7.4 Write property test for most recent track selection
    - **Property 14: Most Recent Track Playback**
    - **Validates: Requirements 10.4**

  - [ ]* 7.5 Write unit tests for audio playback
    - Test audio element creation
    - Test track attachment to srcObject
    - Test playback error handling
    - _Requirements: 3.7, 10.3_

- [x] 8. Implement Web Audio API analysis
  - [x] 8.1 Create setupAudioAnalysis function
    - Create AudioContext and AnalyserNode
    - Set analyser.fftSize to 256
    - Create MediaStreamSource from audio track
    - Connect source to analyser
    - Store context and analyser in refs
    - _Requirements: 6.1, 6.2_

  - [x] 8.2 Create analyzeAudioLevel function
    - Get frequency data from analyser
    - Calculate average level from frequency data
    - Normalize level to 0-100 range
    - Update audioLevel state
    - Use requestAnimationFrame for 60fps sampling
    - _Requirements: 6.3, 6.4_

  - [ ]* 8.3 Write property test for audio level range
    - **Property 6: Web Audio API Analysis**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [ ]* 8.4 Write property test for state transition
    - **Property 7: Audio Level State Transition**
    - **Validates: Requirements 6.6**

- [ ] 9. Checkpoint - Verify audio analysis
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement microphone access
  - [x] 10.1 Create enableMicrophone function
    - Call call.microphone.enable()
    - Handle permission granted successfully
    - Handle permission denied with error state
    - Log microphone status
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 10.2 Write property test for microphone publishing
    - **Property 5: Microphone Permission and Publishing**
    - **Validates: Requirements 4.1, 4.5**

  - [ ]* 10.3 Write unit tests for microphone errors
    - Test permission denied error handling
    - Test error message display
    - _Requirements: 4.3, 7.3_

- [x] 11. Implement cleanup and disconnection
  - [x] 11.1 Create cleanup function
    - Cancel animation frame for audio analysis
    - Close AudioContext
    - Stop and remove audio element
    - Call leave() on Stream call
    - Call disconnectUser() on client
    - Handle cleanup errors gracefully (log but don't throw)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]* 11.2 Write property test for comprehensive cleanup
    - **Property 10: Comprehensive Cleanup**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

  - [ ]* 11.3 Write unit tests for cleanup
    - Test all cleanup steps execute
    - Test cleanup errors are logged but don't throw
    - _Requirements: 8.6_

- [x] 12. Implement error handling and reconnection
  - [x] 12.1 Create handleError helper function
    - Accept error type, message, and details
    - Set error state with structured error object
    - Update connection status appropriately
    - Log detailed error to console
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6_

  - [x] 12.2 Create attemptReconnection function
    - Handle connection.changed events
    - Call reconnect() on connection drop
    - Update connection status to "reconnecting"
    - Handle reconnection success and failure
    - _Requirements: 7.5_

  - [ ]* 12.3 Write property test for automatic reconnection
    - **Property 8: Automatic Reconnection on Connection Drop**
    - **Validates: Requirements 7.5**

  - [ ]* 12.4 Write property test for error logging
    - **Property 9: Error Logging**
    - **Validates: Requirements 7.6**

  - [ ]* 12.5 Write unit tests for all error scenarios
    - Test initialization error handling
    - Test join error handling
    - Test permission error handling
    - Test audio timeout handling
    - Test connection drop handling
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 13. Checkpoint - Verify error handling
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Update LiveInterviewScreen component
  - [x] 14.1 Add streamApiKey state and update initializeSession
    - Add useState for streamApiKey
    - Update initializeSession to extract stream_api_key from response
    - Set streamApiKey state with response value
    - _Requirements: 1.1_

  - [x] 14.2 Integrate useStreamAudio hook
    - Import useStreamAudio hook
    - Call hook with callId, streamToken, streamApiKey, userId
    - Destructure audioLevel, connectionStatus, error, isAgentConnected
    - Add onConnectionChange callback for logging
    - Add onError callback to update component error state
    - _Requirements: 1.2, 1.3, 5.1, 5.2, 5.3_

  - [x] 14.3 Remove legacy audio code
    - Delete initializeStreamSDK function (replaced by hook)
    - Delete handleAIAudio function (audio from Stream.io)
    - Delete base64ToBlob function (no longer needed)
    - _Requirements: 9.2_

  - [x] 14.4 Update WebSocket message handler
    - Modify handleWebSocketMessage to ignore "ai_audio" messages
    - Add console.log for ignored ai_audio messages
    - Keep "state_change" message handling unchanged
    - _Requirements: 9.2, 9.3, 9.4_

  - [x] 14.5 Update AIPresence component usage
    - Pass audioLevel prop from hook
    - Pass connectionStatus === 'connected' to isConnected prop
    - Keep aiState from sessionState unchanged
    - _Requirements: 6.5_

  - [ ]* 14.6 Write property test for independent connections
    - **Property 11: Independent Connection Handling**
    - **Validates: Requirements 9.5**

  - [ ]* 14.7 Write property test for WebSocket message routing
    - **Property 12: WebSocket Message Routing**
    - **Validates: Requirements 9.2, 9.3**

  - [ ]* 14.8 Write integration test for complete audio flow
    - Test initialization → connection → audio playback → cleanup
    - Verify all components work together
    - _Requirements: All_

- [x] 15. Add connection status UI
  - [x] 15.1 Add connection status display
    - Show status message based on connectionStatus
    - Display "Connecting to audio..." for initializing/connecting
    - Display "Reconnecting..." for reconnecting
    - Display "Audio connection failed" for error
    - Apply conditional CSS classes based on status
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [x] 15.2 Add agent status indicator
    - Show "AI audio active" when isAgentConnected is true
    - Position indicator below connection status
    - Apply success styling
    - _Requirements: 5.3_

- [ ] 16. Create CSS styling for connection status
  - [ ] 16.1 Create LiveInterviewScreen.css file
    - Add .connection-status base styles
    - Add status-specific classes (initializing, connecting, connected, reconnecting, error)
    - Add .agent-status styles
    - Add slideIn animation
    - Use color coding: blue (connecting), green (connected), yellow (reconnecting), red (error)
    - _Requirements: 5.5_

- [ ] 17. Checkpoint - Verify UI integration
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 18. Final integration and testing
  - [ ] 18.1 Run all unit tests
    - Execute npm test -- --run
    - Verify all tests pass
    - Check test coverage >80%

  - [ ] 18.2 Run all property-based tests
    - Execute property tests with 100 iterations minimum
    - Verify all properties hold
    - Check for any counterexamples

  - [ ] 18.3 Manual testing checklist
    - Start interview session and verify connection flow
    - Verify audio plays from speakers
    - Verify AIPresence waveforms animate with audio
    - Test microphone permission grant/deny
    - Test network disconnection and reconnection
    - Test session end and cleanup
    - Test in Chrome, Firefox, Safari
    - _Requirements: All_

- [ ] 19. Final checkpoint - Complete feature verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Follow vertical slice: backend → hook → component → styling → testing
- The useStreamAudio hook encapsulates all Stream.io logic for reusability
- WebSocket and Stream.io connections operate independently
- Audio comes from Stream.io WebRTC, state updates from WebSocket
