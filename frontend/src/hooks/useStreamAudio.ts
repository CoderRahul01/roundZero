/**
 * useStreamAudio - Custom hook for Stream.io audio integration
 * 
 * Handles all Stream.io SDK logic:
 * - Client initialization
 * - Call joining with retry
 * - Audio track subscription
 * - Microphone access
 * - Audio level analysis
 * - Connection lifecycle
 */

import { useState, useEffect, useRef } from 'react';
import { StreamVideoClient, Call } from '@stream-io/video-react-sdk';

// Types
export type ConnectionStatus = 
  | 'initializing' 
  | 'connecting' 
  | 'connected' 
  | 'disconnected' 
  | 'reconnecting' 
  | 'error';

export interface StreamError {
  type: 'initialization' | 'join' | 'audio' | 'permission' | 'network';
  message: string;
  details?: any;
}

export interface UseStreamAudioOptions {
  callId: string;
  streamToken: string;
  streamApiKey: string;
  userId: string;
  onConnectionChange?: (status: ConnectionStatus) => void;
  onError?: (error: StreamError) => void;
}

export interface UseStreamAudioReturn {
  audioLevel: number;
  connectionStatus: ConnectionStatus;
  error: StreamError | null;
  isAgentConnected: boolean;
  retryConnection: () => Promise<void>;
}

export function useStreamAudio(options: UseStreamAudioOptions): UseStreamAudioReturn {
  const { callId, streamToken, streamApiKey, userId, onConnectionChange, onError } = options;

  // State
  const [audioLevel, setAudioLevel] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('initializing');
  const [error, setError] = useState<StreamError | null>(null);
  const [isAgentConnected, setIsAgentConnected] = useState(false);

  // Refs
  const clientRef = useRef<StreamVideoClient | null>(null);
  const callRef = useRef<Call | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const participantCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Update connection status with callback
  const updateConnectionStatus = (status: ConnectionStatus) => {
    setConnectionStatus(status);
    onConnectionChange?.(status);
  };

  // Handle errors with callback
  const handleError = (type: StreamError['type'], message: string, details?: any) => {
    const err: StreamError = { type, message, details };
    setError(err);
    onError?.(err);
    console.error(`[Stream.io ${type} error]:`, message, details);
  };

  // Analyze audio level at 60fps
  const analyzeAudioLevel = () => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average level
    const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
    const normalizedLevel = (average / 255) * 100;

    setAudioLevel(normalizedLevel);

    // Continue analyzing
    animationFrameRef.current = requestAnimationFrame(analyzeAudioLevel);
  };

  // Setup audio analysis
  const setupAudioAnalysis = (track: MediaStreamTrack) => {
    try {
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;

      const stream = new MediaStream([track]);
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Start analyzing
      analyzeAudioLevel();
    } catch (err) {
      console.error('Audio analysis setup failed:', err);
    }
  };

  // Subscribe to agent audio
  const subscribeToAgentAudio = (participant: any) => {
    try {
      // Get audio tracks
      const audioTracks = participant.publishedTracks?.filter(
        (track: any) => track.kind === 'audio'
      ) || [];

      if (audioTracks.length === 0) {
        console.warn('No audio tracks from agent, retrying in 1s...');
        setTimeout(() => subscribeToAgentAudio(participant), 1000);
        return;
      }

      // Use most recent track
      const audioTrack = audioTracks[audioTracks.length - 1];

      // Validate track
      if (audioTrack.muted || audioTrack.readyState !== 'live') {
        console.warn('Audio track not ready:', { 
          muted: audioTrack.muted, 
          readyState: audioTrack.readyState 
        });
        return;
      }

      // Create audio element
      const audioElement = new Audio();
      audioElement.autoplay = true;
      audioElement.srcObject = new MediaStream([audioTrack]);
      audioElementRef.current = audioElement;

      // Play audio
      audioElement.play().catch(err => {
        console.error('Audio playback failed:', err);
        // Retry on user interaction
        document.addEventListener('click', () => audioElement.play(), { once: true });
      });

      // Setup audio analysis
      setupAudioAnalysis(audioTrack);

      console.log('✅ Agent audio subscribed and playing');
    } catch (err) {
      console.error('Failed to subscribe to agent audio:', err);
    }
  };

  // Setup event listeners
  const setupEventListeners = (call: Call) => {
    // Listen for participant joined - using call.state for participant tracking
    const checkForAgent = () => {
      const participants = call.state.participants;
      const agentParticipant = participants?.find((p: any) => p.userId === 'agent');
      
      if (agentParticipant && !isAgentConnected) {
        console.log('🤖 Agent joined the call');
        setIsAgentConnected(true);
        subscribeToAgentAudio(agentParticipant);
      }
    };

    // Check periodically for agent
    const intervalId = setInterval(checkForAgent, 1000);
    
    // Store interval for cleanup
    return intervalId;
  };

  // Enable microphone
  const enableMicrophone = async (call: Call) => {
    try {
      await call.microphone.enable();
      console.log('🎤 Microphone enabled');
    } catch (err) {
      handleError('permission', 'Microphone access required for interview', err);
    }
  };

  // Join call with retry
  const joinCall = async (client: StreamVideoClient, retryCount = 0): Promise<void> => {
    try {
      const call = client.call('interview', callId);
      callRef.current = call;

      await call.join({ create: true });

      updateConnectionStatus('connected');
      setError(null);

      // Setup event listeners and store interval
      const intervalId = setupEventListeners(call);
      participantCheckIntervalRef.current = intervalId;

      // Enable microphone
      await enableMicrophone(call);

      console.log('✅ Joined Stream.io call:', callId);
    } catch (err) {
      if (retryCount < 3) {
        const delay = Math.pow(2, retryCount) * 1000;
        console.log(`Join failed, retrying in ${delay}ms (attempt ${retryCount + 1}/3)`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return joinCall(client, retryCount + 1);
      } else {
        handleError('join', 'Unable to join audio call - please refresh', err);
        updateConnectionStatus('error');
      }
    }
  };

  // Initialize client and join call
  useEffect(() => {
    // Don't initialize if any required value is missing or empty
    if (!streamApiKey || !streamToken || !userId || !callId || 
        streamApiKey === '' || streamToken === '' || callId === '') {
      console.log('Waiting for Stream.io credentials...', { 
        hasApiKey: !!streamApiKey, 
        hasToken: !!streamToken, 
        hasCallId: !!callId 
      });
      
      // If token is explicitly null/empty, show error
      if (streamApiKey && callId && !streamToken) {
        handleError('initialization', 'Stream.io authentication not configured on backend', {
          hint: 'STREAM_API_SECRET may be missing from backend .env'
        });
        updateConnectionStatus('error');
      }
      return;
    }

    const initializeClient = async () => {
      try {
        updateConnectionStatus('connecting');

        const client = new StreamVideoClient({
          apiKey: streamApiKey,
          token: streamToken,
          user: { id: userId }
        });

        clientRef.current = client;

        // Join call
        await joinCall(client);
      } catch (err) {
        handleError('initialization', 'Failed to initialize audio system', err);
        updateConnectionStatus('error');
      }
    };

    initializeClient();

    // Cleanup
    return () => {
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [streamApiKey, streamToken, userId, callId]);

  // Cleanup function
  const cleanup = async () => {
    try {
      // Clear participant check interval
      if (participantCheckIntervalRef.current) {
        clearInterval(participantCheckIntervalRef.current);
        participantCheckIntervalRef.current = null;
      }

      // Stop audio analysis
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }

      // Close audio context
      if (audioContextRef.current) {
        await audioContextRef.current.close();
        audioContextRef.current = null;
      }

      // Stop audio element
      if (audioElementRef.current) {
        audioElementRef.current.pause();
        audioElementRef.current.srcObject = null;
        audioElementRef.current = null;
      }

      // Leave call
      if (callRef.current) {
        await callRef.current.leave();
        callRef.current = null;
      }

      // Disconnect client
      if (clientRef.current) {
        await clientRef.current.disconnectUser();
        clientRef.current = null;
      }
    } catch (err) {
      console.error('Cleanup error (non-fatal):', err);
    }
  };

  // Retry connection function
  const retryConnection = async () => {
    if (clientRef.current && callId) {
      await joinCall(clientRef.current);
    }
  };

  return {
    audioLevel,
    connectionStatus,
    error,
    isAgentConnected,
    retryConnection
  };
}
