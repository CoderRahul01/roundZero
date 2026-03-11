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
  onAgentEvent?: (data: any) => void;
  onError?: (error: string) => void;
  onScreenShareRequest?: () => void;
  onScreenShareStop?: () => void;
  videoSource?: 'camera' | 'screen' | 'none';
  externalStream?: MediaStream | null;
}

export interface UseGeminiLiveReturn {
  isConnected: boolean;
  isAiSpeaking: boolean;
  audioLevel: number;
  error: string | null;
  startSession: () => void;
  stopSession: () => void;
  sendMessage: (data: object | string) => void;
  resumeAudio: () => Promise<void>;
}

// Worklet code for mic capture - processes blocks and sends to main thread
const MIC_PROCESSOR_WORKLET = `
  class MicProcessor extends AudioWorkletProcessor {
    constructor() {
      super();
      this.bufferSize = 1024;
      this.buffer = new Float32Array(this.bufferSize);
      this.bufferIndex = 0;
    }

    process(inputs) {
      const input = inputs[0];
      if (!input || !input[0]) return true;
      
      const channelData = input[0];
      for (let i = 0; i < channelData.length; i++) {
        this.buffer[this.bufferIndex++] = channelData[i];
        
        if (this.bufferIndex >= this.bufferSize) {
          // Send a copy of the buffer to the main thread
          this.port.postMessage(this.buffer);
          this.bufferIndex = 0;
        }
      }
      return true;
    }
  }
  registerProcessor('mic-processor', MicProcessor);
`;

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
    onAgentEvent,
    onError,
    onScreenShareRequest,
    onScreenShareStop,
    videoSource = 'camera',
    externalStream
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
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const isWorkletLoadedRef = useRef(false);
  
  // Ref for scheduled playback timing
  const nextPlayTimeRef = useRef<number>(0);
  const playbackQueueRef = useRef<Int16Array[]>([]);
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
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
        isWorkletLoadedRef.current = false;
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

      // Register and load AudioWorklet ONLY ONCE per context
      if (!isWorkletLoadedRef.current) {
        const blob = new Blob([MIC_PROCESSOR_WORKLET], { type: 'application/javascript' });
        const workletUrl = URL.createObjectURL(blob);
        try {
          await micCtxRef.current.audioWorklet.addModule(workletUrl);
          isWorkletLoadedRef.current = true;
          console.log('AudioWorklet module loaded successfully');
        } catch (e) {
          console.warn('AudioWorklet module add failed (might already exist):', e);
        } finally {
          URL.revokeObjectURL(workletUrl);
        }
      }
      
      const workletNode = new AudioWorkletNode(micCtxRef.current, 'mic-processor');
      source.connect(workletNode);
      workletNode.connect(micCtxRef.current.destination);
      workletNodeRef.current = workletNode;

      workletNode.port.onmessage = (event) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          const inputData = event.data; // Float32Array of 1024 samples
          // Convert Float32 to Int16 PCM
          const pcmData = new Int16Array(inputData.length);
          for (let i = 0; i < inputData.length; i++) {
              pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
          }
          wsRef.current.send(pcmData.buffer);
        }

        // Update audio level for UI (using analyser)
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
  
  // Setup Video Capture (Phase 2 & 5)
  const initVideo = useCallback(async (sourceLabel: 'camera' | 'screen' | 'none') => {
    if (sourceLabel === 'none') return;
    
    try {
      let stream;
      if (externalStream) {
        stream = externalStream;
      } else if (sourceLabel === 'screen') {
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
      const targetWidth = sourceLabel === 'screen' ? 768 : 640;
      const targetHeight = sourceLabel === 'screen' ? 768 : 480;
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext('2d');

      const captureInterval = sourceLabel === 'screen' ? 1000 : 5000;

      frameIntervalRef.current = window.setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN && ctx) {
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          const base64 = canvas.toDataURL('image/jpeg', 0.6);
          const data = base64.split(',')[1];
          wsRef.current.send(JSON.stringify({
            type: sourceLabel === 'screen' ? 'screen_frame' : 'image',
            data: data,
            mimeType: 'image/jpeg'
          }));
        }
      }, captureInterval);

    } catch (err) {
      console.warn('Video capture failed or denied, continuing audio-only:', err);
    }
  }, []);

  // AI audio playback — Scheduled for zero-gap playback at 24kHz
  const playNextChunk = useCallback(async () => {
    if (playbackQueueRef.current.length === 0 || !playbackCtxRef.current) {
      isPlayingRef.current = false;
      setIsAiSpeaking(false);
      return;
    }

    isPlayingRef.current = true;
    setIsAiSpeaking(true);
    
    const chunk = playbackQueueRef.current.shift()!;
    const audioBuffer = playbackCtxRef.current.createBuffer(1, chunk.length, 24000);
    const channelData = audioBuffer.getChannelData(0);
    
    for (let i = 0; i < chunk.length; i++) {
      channelData[i] = chunk[i] / 0x7FFF;
    }

    if (playbackCtxRef.current.state === 'suspended') {
      try {
        nextPlayTimeRef.current = 0; // reset so audio doesn't pile up
        await playbackCtxRef.current.resume();
      } catch (e) {
        // Browser blocked resume (no user gesture) — push chunk back and bail.
        playbackQueueRef.current.unshift(chunk);
        isPlayingRef.current = false;
        setIsAiSpeaking(false);
        return;
      }
    }

    const source = playbackCtxRef.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(playbackCtxRef.current.destination);
    activeSourcesRef.current.push(source);
    
    // Scheduled playback logic
    const now = playbackCtxRef.current.currentTime;
    if (nextPlayTimeRef.current < now) {
      // If we fell behind, catch up to 'now + small padding'
      nextPlayTimeRef.current = now + 0.05;
    }
    
    source.start(nextPlayTimeRef.current);
    
    // Update next play time
    const duration = chunk.length / 24000;
    nextPlayTimeRef.current += duration;

    // We don't wait for onended anymore for the next chunk, 
    // we can schedule the whole queue ahead of time.
    if (playbackQueueRef.current.length > 0) {
      playNextChunk();
    } else {
        source.onended = () => {
          // Remove from active sources
          activeSourcesRef.current = activeSourcesRef.current.filter(s => s !== source);
          
          if (playbackQueueRef.current.length === 0 && activeSourcesRef.current.length === 0) {
            isPlayingRef.current = false;
            setIsAiSpeaking(false);
          } else if (playbackQueueRef.current.length > 0) {
            playNextChunk();
          }
        };
      }
  }, []);

  const sendMessage = useCallback((data: object | string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }, []);

  // Must be called from a user-gesture handler to unlock autoplay.
  const resumeAudio = useCallback(async () => {
    try {
      if (micCtxRef.current?.state === 'suspended') await micCtxRef.current.resume();
      if (playbackCtxRef.current?.state === 'suspended') {
        nextPlayTimeRef.current = 0; // reset scheduling so queued audio plays immediately
        await playbackCtxRef.current.resume();
      }
    } catch (e) {
      console.warn('AudioContext resume failed:', e);
    }
  }, []);

  const startSession = useCallback(() => {
    if (wsRef.current) return;

    // ── Create BOTH AudioContexts synchronously here, before any async gap. ──
    // This function must be called directly from a user-click handler so the
    // browser still considers us inside a "user activation" and allows
    // AudioContext creation + resume without blocking autoplay policy.
    if (!micCtxRef.current) {
      micCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      isWorkletLoadedRef.current = false;
    }
    if (!playbackCtxRef.current) {
      playbackCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    }
    // Attempt synchronous unlock while still in the gesture call stack.
    micCtxRef.current.resume().catch(() => {});
    playbackCtxRef.current.resume().catch(() => {});

    // For WebSocket, connect directly to backend — bypass Vite proxy
    const wsBase = baseUrl.includes('localhost:3000')
      ? 'ws://localhost:8080'
      : baseUrl.replace('http', 'ws');
    const wsUrl = `${wsBase}/ws/${userId}/${sessionId}?mode=${mode}${token ? `&token=${token}` : ''}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = async () => {
      retryCountRef.current = 0;
      setIsConnected(true);
      setError(null);

      await initAudio(); // getUserMedia + worklet setup (contexts already exist)

      // Re-attempt resume after getUserMedia — media permission grants implicit
      // autoplay activation in Chrome/Firefox even when called outside a gesture.
      if (micCtxRef.current?.state === 'suspended') await micCtxRef.current.resume().catch(() => {});
      if (playbackCtxRef.current?.state === 'suspended') await playbackCtxRef.current.resume().catch(() => {});

      initVideo(videoSource);
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
          onAgentEvent?.(data);
        }
        if (data.type === 'tool_call') {
            onAgentEvent?.(data);
        }
        if (data.type === 'score_update') {
            onAgentEvent?.(data);
        }
        if (data.type === 'screen_share') {
            if (data.action === 'request') onScreenShareRequest?.();
            else if (data.action === 'stop') onScreenShareStop?.();
        }
        if (data.type === 'interrupt') {
            onInterrupt?.();
            playbackQueueRef.current = []; // Clear queue on interrupt
            // Stop ALL active and scheduled sources immediately
            activeSourcesRef.current.forEach(source => {
                try { source.stop(); } catch (e) {}
            });
            activeSourcesRef.current = [];
            // Reset scheduled time on interrupt so new audio starts fresh
            nextPlayTimeRef.current = 0;
            isPlayingRef.current = false;
            setIsAiSpeaking(false);
        }
        if (data.type === 'interview_end') onComplete?.(data);
        if (data.type === 'complete') onComplete?.(data);
      } else {
        // Audio chunk (binary)
        if (event.data instanceof ArrayBuffer) {
            if (playbackQueueRef.current.length === 0) {
                console.log("🔊 First audio chunk received, size:", event.data.byteLength);
            }
            const chunk = new Int16Array(event.data);
            playbackQueueRef.current.push(chunk);
            if (!isPlayingRef.current) {
              playNextChunk();
            }
        } else {
            console.warn("⚠️ Received non-ArrayBuffer binary data", event.data);
        }
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
  }, [baseUrl, mode, sessionId, userId, token, initAudio, onTranscript, onAiTranscript, onEmotion, onInterrupt, onComplete, onAgentEvent, onError, onScreenShareRequest, onScreenShareStop, playNextChunk, initVideo, videoSource]);

  const stopSession = useCallback(() => {
    wsRef.current?.close();
    workletNodeRef.current?.disconnect();
    
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
    stopSession,
    sendMessage,
    resumeAudio,
  };
}
