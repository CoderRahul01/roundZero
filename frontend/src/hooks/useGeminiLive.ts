import { useState, useEffect, useRef, useCallback } from 'react';

export interface GeminiLiveOptions {
  userId: string;
  sessionId: string;
  mode: string;
  baseUrl: string;
  token?: string | null;
  onTranscript?: (text: string) => void;
  onAiTranscript?: (text: string) => void;
  onEmotion?: (emotion: string, confidence: number) => void;
  onInterrupt?: () => void;
  onComplete?: (data: any) => void;
  onError?: (error: string) => void;
  videoSource?: 'camera' | 'screen' | 'none';
}

export interface UseGeminiLiveReturn {
  isConnected: boolean;
  isAiSpeaking: boolean;
  audioLevel: number;
  error: string | null;
  startSession: () => void;
  stopSession: () => void;
}

export function useGeminiLive(options: GeminiLiveOptions): UseGeminiLiveReturn {
  const { 
    userId,
    sessionId, 
    mode, 
    baseUrl, 
    token,
    onTranscript, 
    onAiTranscript, 
    onEmotion, 
    onInterrupt, 
    onComplete, 
    onError,
    videoSource = 'camera'
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  // Use a ref (not state) for retry counting — state causes stale closures in onclose handlers
  const retryCountRef = useRef(0);

  const wsRef = useRef<WebSocket | null>(null);
  // mic capture context — MUST be 16kHz (ADK/Gemini input requirement)
  const micCtxRef = useRef<AudioContext | null>(null);
  // AI playback context — MUST be 24kHz (Gemini native-audio output rate)
  const playbackCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const playbackQueueRef = useRef<Int16Array[]>([]);
  const isPlayingRef = useRef(false);
  const videoStreamRef = useRef<MediaStream | null>(null);
  const frameIntervalRef = useRef<number | null>(null);

  // Setup Mic AudioContext (16kHz) & AI Playback AudioContext (24kHz)
  const initAudio = useCallback(async () => {
    try {
      // 16kHz context for mic capture — required by ADK/Gemini STT
      if (!micCtxRef.current) {
        micCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 16000,
        });
      }
      // 24kHz context for AI audio playback — Gemini native-audio outputs 24kHz PCM
      if (!playbackCtxRef.current) {
        playbackCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({
          sampleRate: 24000,
        });
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const source = micCtxRef.current.createMediaStreamSource(stream);
      
      const analyser = micCtxRef.current.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // ScriptProcessor captures mic audio and sends raw 16kHz PCM to backend
      const processor = micCtxRef.current.createScriptProcessor(4096, 1, 1);
      source.connect(processor);
      processor.connect(micCtxRef.current.destination);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const inputData = e.inputBuffer.getChannelData(0);
          // Convert Float32 to Int16 PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }
          wsRef.current.send(pcmData.buffer);
        }

        // Update audio level for UI
        if (analyserRef.current) {
            const data = new Uint8Array(analyserRef.current.frequencyBinCount);
            analyserRef.current.getByteFrequencyData(data);
            const avg = data.reduce((a, b) => a + b) / data.length;
            setAudioLevel(avg);
        }
      };
    } catch (err) {
      console.error('Audio initialization failed:', err);
      setError('Microphone access denied or not supported.');
      onError?.('Microphone access denied or not supported.');
    }
  }, [onError]);
  
  // Setup Video Capture (Phase 2)
  const initVideo = useCallback(async (sourceLabel: 'camera' | 'screen' | 'none') => {
    if (sourceLabel === 'none') return;
    
    try {
      let stream;
      if (sourceLabel === 'screen') {
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: { frameRate: 2, width: 1280, height: 720 }
        });
      } else {
        stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 640, height: 480, frameRate: 5 } 
        });
      }
      videoStreamRef.current = stream;

      const video = document.createElement('video');
      video.srcObject = stream;
      await video.play();

      const canvas = document.createElement('canvas');
      canvas.width = sourceLabel === 'screen' ? 1280 : 640;
      canvas.height = sourceLabel === 'screen' ? 720 : 480;
      const ctx = canvas.getContext('2d');

      frameIntervalRef.current = window.setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN && ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const base64 = canvas.toDataURL('image/jpeg', 0.4);
          const data = base64.split(',')[1];
          wsRef.current.send(JSON.stringify({
            type: 'image',
            data: data,
            mimeType: 'image/jpeg'
          }));
        }
      }, 5000); // 1 frame per 5 seconds

    } catch (err) {
      console.warn('Video capture failed or denied, continuing audio-only:', err);
    }
  }, []);

  // AI audio playback — uses 24kHz context to match Gemini native-audio output
  const playNextChunk = useCallback(async () => {
    if (playbackQueueRef.current.length === 0 || isPlayingRef.current || !playbackCtxRef.current) {
      return;
    }

    isPlayingRef.current = true;
    setIsAiSpeaking(true);
    
    const chunk = playbackQueueRef.current.shift()!;
    // playbackCtxRef is 24kHz — matches Gemini native-audio PCM output rate
    const audioBuffer = playbackCtxRef.current.createBuffer(1, chunk.length, 24000);
    const channelData = audioBuffer.getChannelData(0);
    
    for (let i = 0; i < chunk.length; i++) {
      channelData[i] = chunk[i] / 0x7FFF;
    }

    const source = playbackCtxRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(playbackCtxRef.current.destination);
    
    source.onended = () => {
      isPlayingRef.current = false;
      if (playbackQueueRef.current.length === 0) {
        setIsAiSpeaking(false);
      }
      playNextChunk();
    };
    
    source.start();
  }, []);

  const startSession = useCallback(() => {
    if (wsRef.current) return;

    // For WebSocket, connect directly to backend — bypass Vite proxy
    const wsBase = baseUrl.includes('localhost:3000') 
      ? 'ws://localhost:8080' 
      : baseUrl.replace('http', 'ws');
    const wsUrl = `${wsBase}/ws/${userId}/${sessionId}?mode=${mode}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = async () => {
      retryCountRef.current = 0;  // Reset on successful connect
      setIsConnected(true);
      setError(null);
      
      // Resume both AudioContexts — browser suspends them until user gesture
      if (micCtxRef.current?.state === 'suspended') {
        await micCtxRef.current.resume();
      }
      if (playbackCtxRef.current?.state === 'suspended') {
        await playbackCtxRef.current.resume();
      }
      
      initAudio();
      initVideo(videoSource); // Start vision pipeline
    };

    ws.binaryType = 'arraybuffer';

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        const data = JSON.parse(event.data);
        // Backend sends: { type: 'text', content: '...' } for AI responses
        if (data.type === 'text') onAiTranscript?.(data.content);
        // Backend sends: { type: 'transcription', content: '...', source: 'user' }
        if (data.type === 'transcription' && data.source === 'user') onTranscript?.(data.content);
        if (data.type === 'vision') onEmotion?.(data.emotion, data.confidence);
        if (data.type === 'agent_event') {
          // Map ADK agent_event to AI transcript if it has text
          const parts = data.payload?.content?.parts;
          if (parts && parts[0]?.text) {
            onAiTranscript?.(parts[0].text);
          }
        }
        if (data.type === 'interrupt') {
            onInterrupt?.();
            playbackQueueRef.current = []; // Clear queue on interrupt
        }
        if (data.type === 'complete') onComplete?.(data);
      } else {
        // Audio chunk (binary)
        const chunk = new Int16Array(event.data);
        playbackQueueRef.current.push(chunk);
        playNextChunk();
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection error.');
      onError?.('WebSocket connection error.');
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      wsRef.current = null;
      
      // Retry logic using ref (not state) to avoid stale closure infinite loop
      const MAX_RETRIES = 2;
      if (event.code !== 1000 && retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current += 1;
        console.log(`WebSocket closed (code ${event.code}). Retrying (${retryCountRef.current}/${MAX_RETRIES}) in 3s...`);
        setTimeout(() => {
          startSession();
        }, 3000);
      } else if (retryCountRef.current >= MAX_RETRIES) {
        console.log('Max retries reached. Not retrying.');
        retryCountRef.current = 0;  // Reset for next manual start
      }
    };
  }, [baseUrl, mode, sessionId, userId, token, initAudio, onTranscript, onAiTranscript, onEmotion, onInterrupt, onComplete, onError, playNextChunk, initVideo, videoSource]);

  const stopSession = useCallback(() => {
    wsRef.current?.close();
    processorRef.current?.disconnect();
    
    // Cleanup video (Phase 2)
    if (frameIntervalRef.current) {
        clearInterval(frameIntervalRef.current);
        frameIntervalRef.current = null;
    }
    if (videoStreamRef.current) {
        videoStreamRef.current.getTracks().forEach(t => t.stop());
        videoStreamRef.current = null;
    }

    setIsConnected(false);
    setIsAiSpeaking(false);
    setAudioLevel(0);
  }, []);

  useEffect(() => {
    return () => stopSession();
  }, [stopSession]);

  return {
    isConnected,
    isAiSpeaking,
    audioLevel,
    error,
    startSession,
    stopSession
  };
}
