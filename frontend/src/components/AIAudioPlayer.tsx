/**
 * AIAudioPlayer - Handles AI voice playback with auto-play
 * 
 * Features:
 * - Automatic audio playback
 * - Audio level detection
 * - Fallback handling
 * - Stream.io integration
 */

import React, { useEffect, useRef, useState } from 'react';

interface AIAudioPlayerProps {
  audioTrack?: MediaStreamTrack | null;
  onAudioLevel?: (level: number) => void;
  onPlaybackStart?: () => void;
  onPlaybackEnd?: () => void;
}

const AIAudioPlayer: React.FC<AIAudioPlayerProps> = ({
  audioTrack,
  onAudioLevel,
  onPlaybackStart,
  onPlaybackEnd
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const [isPlaying, setIsPlaying] = useState(false);

  // Setup audio track
  useEffect(() => {
    if (!audioTrack || !audioRef.current) return;

    const stream = new MediaStream([audioTrack]);
    audioRef.current.srcObject = stream;
    
    // Auto-play with user gesture fallback
    const playAudio = async () => {
      try {
        await audioRef.current?.play();
        setIsPlaying(true);
        onPlaybackStart?.();
      } catch (error) {
        console.warn('Auto-play blocked, waiting for user interaction:', error);
        
        // Add click listener to enable audio on user interaction
        const enableAudio = async () => {
          try {
            await audioRef.current?.play();
            setIsPlaying(true);
            onPlaybackStart?.();
            document.removeEventListener('click', enableAudio);
          } catch (err) {
            console.error('Failed to play audio:', err);
          }
        };
        
        document.addEventListener('click', enableAudio, { once: true });
      }
    };

    playAudio();

    return () => {
      if (audioRef.current) {
        audioRef.current.srcObject = null;
      }
    };
  }, [audioTrack, onPlaybackStart]);

  // Setup audio analysis
  useEffect(() => {
    if (!audioTrack || !onAudioLevel) return;

    const setupAnalyser = async () => {
      try {
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;

        const stream = new MediaStream([audioTrack]);
        const source = audioContext.createMediaStreamSource(stream);
        const analyser = audioContext.createAnalyser();
        
        analyser.fftSize = 256;
        source.connect(analyser);
        analyserRef.current = analyser;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        const detectAudioLevel = () => {
          if (!analyserRef.current) return;

          analyserRef.current.getByteFrequencyData(dataArray);
          
          // Calculate average audio level
          const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
          const normalizedLevel = average / 255;
          
          onAudioLevel(normalizedLevel);
          
          animationRef.current = requestAnimationFrame(detectAudioLevel);
        };

        detectAudioLevel();
      } catch (error) {
        console.error('Failed to setup audio analyser:', error);
      }
    };

    setupAnalyser();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [audioTrack, onAudioLevel]);

  // Handle audio end
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleEnded = () => {
      setIsPlaying(false);
      onPlaybackEnd?.();
    };

    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onPlaybackEnd]);

  return (
    <audio
      ref={audioRef}
      autoPlay
      playsInline
      style={{ display: 'none' }}
    />
  );
};

export default AIAudioPlayer;
