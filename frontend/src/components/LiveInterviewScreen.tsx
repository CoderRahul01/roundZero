/**
 * LiveInterviewScreen - Main component for live video interviews
 * 
 * Features:
 * - Stream.io video call integration
 * - Real-time confidence meter
 * - AI status display
 * - Question progress tracking
 * - WebSocket for live updates
 */

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface LiveInterviewScreenProps {
  role: string;
  topics: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  mode: 'practice' | 'mock' | 'coaching';
}

interface SessionState {
  session_id: string;
  status: string;
  current_question: number;
  total_questions: number;
  ai_state: 'idle' | 'listening' | 'thinking' | 'speaking';
  emotion: {
    emotion: string;
    confidence_score: number;
    engagement_level: string;
  };
  speech_metrics: {
    filler_word_count: number;
    speech_pace: number;
    long_pause_count: number;
  };
}

const LiveInterviewScreen: React.FC<LiveInterviewScreenProps> = ({
  role,
  topics,
  difficulty,
  mode
}) => {
  // State
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [callId, setCallId] = useState<string | null>(null);
  const [streamToken, setStreamToken] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
    
    return () => {
      cleanup();
    };
  }, []);

  /**
   * Initialize live interview session
   */
  const initializeSession = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Call API to start live session
      const response = await axios.post('/api/interview/start-live-session', {
        role,
        topics,
        difficulty,
        mode
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      const { session_id, call_id, stream_token, question_count } = response.data;

      setSessionId(session_id);
      setCallId(call_id);
      setStreamToken(stream_token);

      // Initialize Stream SDK
      await initializeStreamSDK(call_id, stream_token);

      // Setup WebSocket for real-time updates
      setupWebSocket(session_id);

      setIsLoading(false);

    } catch (err: any) {
      console.error('Failed to initialize session:', err);
      setError(err.response?.data?.detail || 'Failed to start interview session');
      setIsLoading(false);
    }
  };

  /**
   * Initialize Stream.io Video SDK
   */
  const initializeStreamSDK = async (callId: string, token: string) => {
    try {
      // TODO: Implement actual Stream SDK initialization
      // const client = new StreamVideoClient({ apiKey: 'YOUR_API_KEY', token });
      // const call = client.call('interview', callId);
      // await call.join();
      
      console.log('Stream SDK initialized', { callId, token });

      // TODO: Setup video display
      // if (videoRef.current) {
      //   videoRef.current.srcObject = localStream;
      // }

    } catch (err) {
      console.error('Stream SDK initialization failed:', err);
      throw err;
    }
  };

  /**
   * Setup WebSocket connection for real-time updates
   */
  const setupWebSocket = (sessionId: string) => {
    try {
      const wsUrl = `ws://localhost:8000/ws/interview/${sessionId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
      };

      wsRef.current = ws;

    } catch (err) {
      console.error('WebSocket setup failed:', err);
    }
  };

  /**
   * Handle WebSocket messages
   */
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'state_change':
        setSessionState(data.state);
        break;
      case 'confidence_update':
        if (sessionState) {
          setSessionState({
            ...sessionState,
            emotion: data.emotion
          });
        }
        break;
      case 'question_asked':
        console.log('New question:', data.question);
        break;
      case 'interview_complete':
        handleInterviewComplete();
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  };

  /**
   * End interview session
   */
  const handleEndSession = async () => {
    if (!sessionId) return;

    try {
      await axios.delete(`/api/interview/${sessionId}/end-live-session`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      cleanup();
      // Navigate to summary screen
      window.location.href = `/interview/summary/${sessionId}`;

    } catch (err) {
      console.error('Failed to end session:', err);
    }
  };

  /**
   * Handle interview completion
   */
  const handleInterviewComplete = () => {
    console.log('Interview completed');
    setTimeout(() => {
      if (sessionId) {
        window.location.href = `/interview/summary/${sessionId}`;
      }
    }, 2000);
  };

  /**
   * Cleanup resources
   */
  const cleanup = () => {
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // TODO: Leave Stream call
    // if (call) {
    //   call.leave();
    // }

    // TODO: Disconnect Stream client
    // if (client) {
    //   client.disconnectUser();
    // }
  };

  /**
   * Get confidence meter color
   */
  const getConfidenceColor = (score: number): string => {
    if (score >= 71) return '#10b981'; // green
    if (score >= 41) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  /**
   * Get AI state display
   */
  const getAIStateDisplay = (state: string): { text: string; color: string } => {
    switch (state) {
      case 'listening':
        return { text: 'Listening...', color: '#3b82f6' };
      case 'thinking':
        return { text: 'Thinking...', color: '#8b5cf6' };
      case 'speaking':
        return { text: 'Speaking...', color: '#10b981' };
      default:
        return { text: 'Idle', color: '#6b7280' };
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-white text-lg">Initializing interview session...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-white text-2xl font-bold mb-2">Session Error</h2>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">Live Interview</h1>
            <p className="text-gray-400">{role} - {difficulty}</p>
          </div>
          <button
            onClick={handleEndSession}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
          >
            End Session
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Video Feed */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-lg overflow-hidden aspect-video">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
              {!videoRef.current && (
                <div className="flex items-center justify-center h-full">
                  <p className="text-gray-500">Camera initializing...</p>
                </div>
              )}
            </div>

            {/* Question Progress */}
            {sessionState && (
              <div className="mt-4 bg-gray-800 rounded-lg p-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-400">Question Progress</span>
                  <span className="text-white font-semibold">
                    {sessionState.current_question} / {sessionState.total_questions}
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${(sessionState.current_question / sessionState.total_questions) * 100}%`
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* AI Status */}
            {sessionState && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">AI Status</h3>
                <div className="flex items-center space-x-2">
                  <div
                    className="w-3 h-3 rounded-full animate-pulse"
                    style={{ backgroundColor: getAIStateDisplay(sessionState.ai_state).color }}
                  />
                  <span className="text-gray-300">
                    {getAIStateDisplay(sessionState.ai_state).text}
                  </span>
                </div>
              </div>
            )}

            {/* Confidence Meter */}
            {sessionState && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">Confidence Level</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-400">Score</span>
                    <span className="text-white font-bold text-xl">
                      {sessionState.emotion.confidence_score}
                    </span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-4">
                    <div
                      className="h-4 rounded-full transition-all duration-300"
                      style={{
                        width: `${sessionState.emotion.confidence_score}%`,
                        backgroundColor: getConfidenceColor(sessionState.emotion.confidence_score)
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Low</span>
                    <span>Medium</span>
                    <span>High</span>
                  </div>
                </div>
              </div>
            )}

            {/* Emotion & Engagement */}
            {sessionState && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">Analysis</h3>
                <div className="space-y-3">
                  <div>
                    <span className="text-gray-400 text-sm">Emotion</span>
                    <p className="text-white capitalize">{sessionState.emotion.emotion}</p>
                  </div>
                  <div>
                    <span className="text-gray-400 text-sm">Engagement</span>
                    <p className="text-white capitalize">{sessionState.emotion.engagement_level}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Speech Metrics */}
            {sessionState && (
              <div className="bg-gray-800 rounded-lg p-4">
                <h3 className="text-white font-semibold mb-3">Speech Patterns</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Filler Words</span>
                    <span className="text-white">{sessionState.speech_metrics.filler_word_count}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Speech Pace</span>
                    <span className="text-white">{sessionState.speech_metrics.speech_pace.toFixed(0)} WPM</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Long Pauses</span>
                    <span className="text-white">{sessionState.speech_metrics.long_pause_count}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveInterviewScreen;
