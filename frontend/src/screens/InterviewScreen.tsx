import React, { useCallback, useEffect, useRef, useState } from "react";
import { endSession, WS_BASE } from "../api";
import { G } from "../theme";
import { LiveSessionConfig } from "../types";
import { useGeminiLive } from "../hooks/useGeminiLive";
import { InterviewProgress } from "../components/Interview/InterviewProgress";

function emotionColor(emotion: string): string {
  const map: Record<string, string> = {
    confident: G.accent,
    neutral: "#94a3b8",
    confused: G.accent2,
    focused: "#818cf8",
    nervous: G.accent3,
  };
  return map[emotion] || "#94a3b8";
}

export function InterviewScreen({
  config,
  onEnd,
}: {
  config: LiveSessionConfig;
  onEnd: () => void;
}) {
  const [question, setQuestion] = useState(config.first_question);
  const [questionIndex, setQuestionIndex] = useState(config.question_index);
  const [aiMsg, setAiMsg] = useState("Initializing connection...");
  const [confidence, setConfidence] = useState(68);
  const [emotion, setEmotion] = useState("neutral");
  const [fillers, setFillers] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [userTranscript, setUserTranscript] = useState("");
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Filter out duplicate or very short transcripts and count fillers
  const onTranscriptUpdate = useCallback((text: string) => {
    setUserTranscript(prev => {
      if (prev.endsWith(text)) return prev;
      return `${prev} ${text}`.trim();
    });

    // Simple filler word detection
    const fillers_regex = /\b(um|uh|like|basically|actually|literally|you know|i mean)\b/gi;
    const matches = text.match(fillers_regex);
    if (matches) {
      setFillers(prev => prev + matches.length);
    }
  }, []);

  const { isConnected, isAiSpeaking, audioLevel, error, startSession, stopSession } = useGeminiLive({
    userId: config.user_id,
    sessionId: config.session_id,
    mode: config.mode,
    baseUrl: WS_BASE,
    token: config.backend_token,
    videoSource: config.videoSource,
    externalStream: config.externalStream,
    onTranscript: onTranscriptUpdate,
    onAiTranscript: (text) => {
        // AI now sends: ```json { "question_type": "...", "question_number": ..., "content": "..." } ```
        // We need to parse this.
        try {
            const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
            const rawJson = jsonMatch ? jsonMatch[1] : text;
            const data = JSON.parse(rawJson);
            
            if (data.question_type === "NEW_QUESTION") {
                setQuestionIndex(data.question_number);
                setQuestion(data.content);
            } else if (data.question_type === "FOLLOW_UP") {
                // Keep the same question index, just show the follow-up content
                setQuestion(data.content);
            }
            setAiMsg(data.content);
        } catch (e) {
            // Fallback for non-json responses
            setAiMsg(text);
        }
    },
    onEmotion: (emo, conf) => {
        setEmotion(emo);
        setConfidence(conf);
    },
    onInterrupt: () => {
        // Handle visual cues for interruption
    },
    onComplete: (data) => {
        if (data.is_finished) {
            handleEnd();
        }
    },
    onAgentEvent: (data) => {
        // Handle sync_interview_state tool call manually if needed 
        // or any other agent-specific JSON events
        if (data.type === 'tool_call') {
            const { name, args } = data.payload;
            if (name === 'sync_interview_state') {
                setQuestionIndex(args.question_index + 1);
                setQuestion(args.question_text);
            }
        }
    },
    onError: (err) => console.error("Gemini Live Error:", err)
  });

  // Camera Preview Logic
  useEffect(() => {
    if (config.videoSource === 'camera' && isConnected) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
          if (videoRef.current) videoRef.current.srcObject = stream;
        })
        .catch(err => console.error("Camera preview failed:", err));
    }
    return () => {
      if (videoRef.current?.srcObject) {
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      }
    };
  }, [config.videoSource, isConnected]);

  const toggleScreenShare = async () => {
    if (isScreenSharing) {
        if (screenStreamRef.current) {
            screenStreamRef.current.getTracks().forEach(t => t.stop());
            screenStreamRef.current = null;
        }
        setIsScreenSharing(false);
    } else {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({ 
                video: true, 
                audio: false  // DO NOT CAPTURE AUDIO - already handled by getUserMedia
            });
            screenStreamRef.current = stream;
            if (screenVideoRef.current) {
                screenVideoRef.current.srcObject = stream;
            }
            
            stream.getVideoTracks()[0].onended = () => {
                setIsScreenSharing(false);
                screenStreamRef.current = null;
            };
            
            setIsScreenSharing(true);
        } catch (err) {
            console.error("Screen share failed:", err);
        }
    }
  };

  useEffect(() => {
    const timer = setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // Use refs to capture latest functions without adding them to useEffect deps
  // This prevents the effect from re-firing (and disconnecting/reconnecting) when
  // startSession or stopSession are recreated by useCallback on every render.
  const startSessionRef = useRef(startSession);
  const stopSessionRef = useRef(stopSession);
  useEffect(() => { startSessionRef.current = startSession; }, [startSession]);
  useEffect(() => { stopSessionRef.current = stopSession; }, [stopSession]);

  useEffect(() => {
    startSessionRef.current();           // Connect once on mount
    return () => stopSessionRef.current(); // Disconnect on unmount
  }, []);  // Empty array = only fires on mount/unmount, never re-fires

  // Audio Visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 38;
      const width = canvas.width / bars - 2;
      
      for (let i = 0; i < bars; i += 1) {
        // Use audioLevel from hook for visualization
        const pulse = audioLevel > 0 
            ? (Math.random() * 0.5 + 0.5) * (audioLevel / 5) + 5 
            : Math.sin(Date.now() / 200 + i * 0.6) * 3 + 6;
        
        ctx.fillStyle = isConnected ? G.accent : G.muted;
        ctx.globalAlpha = 0.75;
        ctx.fillRect(i * (width + 2), (canvas.height - pulse) / 2, width, pulse);
      }
      raf = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(raf);
  }, [isConnected, audioLevel]);

  const fmt = (seconds: number) =>
    `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

  const handleEnd = async () => {
    stopSession();
    try {
      await endSession(config.session_id);
    } finally {
      onEnd();
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: G.bg, fontFamily: G.font, display: "grid", gridTemplateColumns: "300px 1fr 340px", overflow: "hidden" }}>
      
      {/* LEFT COLUMN: SESSION INFO & TRANSCRIPT */}
      <div style={{ background: G.surface, borderRight: `1px solid ${G.border}`, display: "flex", flexDirection: "column", padding: "1.5rem", gap: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
          <span style={{ fontWeight: 800, fontSize: "1.1rem", color: G.text, letterSpacing: "-0.02em" }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </span>
          <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "0.3rem 0.6rem", fontFamily: G.mono, fontSize: "0.6rem", color: G.accent }}>
            ● LIVE
          </div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "1.2rem" }}>
          <div>
            <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.8rem" }}>Candidate Profile</div>
            <div style={{ background: G.surface2, padding: "1rem", border: `1px solid ${G.border}` }}>
              <div style={{ fontSize: "0.9rem", color: G.text, fontWeight: 600 }}>{config.name || "Candidate"}</div>
              <div style={{ fontSize: "0.75rem", color: G.muted, marginTop: "0.2rem" }}>Target: {config.role}</div>
            </div>
          </div>

          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.8rem" }}>Live Transcript</div>
            <div style={{ 
              flex: 1, 
              background: G.surface2, 
              border: `1px solid ${G.border}`, 
              padding: "1rem", 
              fontSize: "0.8rem", 
              color: G.text, 
              lineHeight: 1.6, 
              overflowY: "auto",
              maxHeight: "40vh"
            }}>
              {userTranscript || <span style={{ color: G.muted }}>Listening for speech...</span>}
            </div>
          </div>

          <div style={{ marginTop: "auto" }}>
             <InterviewProgress current={questionIndex} total={config.total_questions} />
          </div>
        </div>

        <button onClick={handleEnd} style={{ width: "100%", padding: "0.8rem", background: "transparent", border: `1px solid ${G.border}`, color: G.accent3, fontFamily: G.font, fontSize: "0.8rem", cursor: "pointer", borderRadius: "2px", fontWeight: 600 }}>
          Quit Session
        </button>
      </div>

      {/* CENTER COLUMN: QUESTION & AI STATUS */}
      <div style={{ display: "flex", flexDirection: "column", padding: "2rem", gap: "2rem", position: "relative" }}>
        
        {/* Progress Dots */}
        <div style={{ display: "flex", gap: "0.6rem", justifyContent: "center" }}>
          {Array.from({ length: config.total_questions }).map((_, i) => (
            <div key={i} style={{ 
              width: 10, height: 10, borderRadius: "50%", 
              background: i < questionIndex ? G.accent : i === questionIndex ? G.accent2 : G.border,
              boxShadow: i === questionIndex ? `0 0 10px ${G.accent2}` : 'none',
              transition: "all 0.3s"
            }} />
          ))}
        </div>

        {/* Large Question Display */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: "3rem" }}>
          <div style={{ maxWidth: "800px" }}>
            <span style={{ fontFamily: G.mono, color: G.accent, fontSize: "0.7rem", letterSpacing: "0.3em", textTransform: "uppercase" }}>Current Question</span>
            <h2 style={{ fontSize: "2.8rem", fontWeight: 700, color: G.text, lineHeight: 1.2, marginTop: "1rem", letterSpacing: "-0.03em" }}>
              {question || "Please introduce yourself to start."}
            </h2>
          </div>

          {/* AI Visualizer Icon */}
          <div style={{ position: "relative" }}>
            <div style={{ 
              width: 140, height: 140, borderRadius: "50%", 
              background: isConnected ? G.surface : G.surface2, 
              border: `2px solid ${isAiSpeaking ? G.accent : G.border}`, 
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: "3.5rem",
              boxShadow: isAiSpeaking ? `0 0 ${30 + audioLevel}px ${G.accent}44` : 'none',
              transition: 'all 0.2s ease'
            }}>
              {isConnected ? (isAiSpeaking ? '🗣️' : '👂') : '⌛'}
            </div>
            {isAiSpeaking && (
              <div style={{ position: "absolute", bottom: -20, left: "50%", transform: "translateX(-50%)", width: 120, height: 2, background: G.accent, boxShadow: `0 0 8px ${G.accent}` }} />
            )}
          </div>
        </div>

        {/* Audio Visualizer Bar */}
        <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1.2rem", borderRadius: "2px" }}>
          <canvas ref={canvasRef} width={800} height={60} style={{ width: "100%", height: 60 }} />
        </div>
      </div>

      {/* RIGHT COLUMN: VISION & METRICS */}
      <div style={{ background: G.surface, borderLeft: `1px solid ${G.border}`, display: "flex", flexDirection: "column", padding: "1.5rem", gap: "1.5rem" }}>
        
        {/* Camera/Screen Preview */}
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.8rem" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>Visual Input</div>
            <button 
                onClick={toggleScreenShare}
                style={{ 
                    background: isScreenSharing ? G.accent2 : "transparent", 
                    border: `1px solid ${isScreenSharing ? G.accent2 : G.border}`,
                    color: isScreenSharing ? "#000" : G.muted,
                    fontSize: "0.6rem",
                    padding: "2px 6px",
                    cursor: "pointer",
                    textTransform: "uppercase",
                    fontWeight: 700
                }}
            >
                {isScreenSharing ? "Stop Sharing" : "Share Screen"}
            </button>
          </div>
          
          <div style={{ background: "#000", border: `2px solid ${isConnected ? G.accent : G.border}`, overflow: "hidden", position: "relative", borderRadius: "2px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {/* Screen Share element - visible only when sharing */}
            {isScreenSharing && (
              <div style={{ width: "100%", aspectRatio: "16/9", background: "#000" }}>
                <video ref={screenVideoRef} autoPlay playsInline style={{ width: "100%", height: "100%", objectFit: "contain" }} />
              </div>
            )}
            
            {/* Primary camera feed */}
            <div style={{ width: "100%", aspectRatio: isScreenSharing ? "4/3" : "4/3", position: "relative" }}>
              {config.videoSource === 'camera' ? (
                <video ref={videoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }} />
              ) : (
                <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: G.muted, fontSize: "0.8rem" }}>
                  Vision Disabled
                </div>
              )}
              <div style={{ position: "absolute", bottom: 8, left: 8, background: "rgba(0,0,0,0.6)", padding: "2px 8px", borderRadius: "10px", border: `1px solid ${emotionColor(emotion)}` }}>
                 <span style={{ color: emotionColor(emotion), fontSize: "0.65rem", fontWeight: 600, textTransform: "uppercase" }}>{emotion}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Confidence Meter */}
        <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <span style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, textTransform: "uppercase" }}>Confidence Scale</span>
            <span style={{ fontSize: "1.2rem", fontWeight: 800, color: confidence > 65 ? G.accent : G.accent2 }}>{Math.round(confidence)}%</span>
          </div>
          <div style={{ height: 8, background: G.bg, borderRadius: "4px", overflow: "hidden" }}>
             <div style={{ height: "100%", width: `${confidence}%`, background: confidence > 65 ? G.accent : G.accent2, transition: "width 0.8s ease" }} />
          </div>
          <p style={{ fontSize: "0.7rem", color: G.muted, marginTop: "0.8rem", textAlign: "center" }}>
            {confidence > 75 ? "Excellent composure." : confidence > 50 ? "Steady performance." : "Try to breathe and relax."}
          </p>
        </div>

        {/* Feedback / Filler Counter */}
        <div style={{ flex: 1, background: G.surface2, border: `1px solid ${G.border}`, padding: "1.5rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <div style={{ color: G.muted, fontSize: "0.65rem", fontFamily: G.mono, textTransform: "uppercase" }}>Fillers Detected</div>
            <div style={{ fontSize: "2rem", fontWeight: 700, color: fillers > 5 ? G.accent3 : G.text, marginTop: "0.2rem" }}>{fillers}</div>
          </div>
          <div style={{ height: "1px", background: G.border }} />
          <div>
            <div style={{ color: G.muted, fontSize: "0.65rem", fontFamily: G.mono, textTransform: "uppercase", marginBottom: "0.6rem" }}>AI Feedback</div>
            <div style={{ fontSize: "0.85rem", color: G.text, lineHeight: 1.5, background: G.bg, padding: "1rem", borderLeft: `2px solid ${G.accent}` }}>
              {aiMsg || "Waiting for your response..."}
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
