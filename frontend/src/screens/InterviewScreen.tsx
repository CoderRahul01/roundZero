import React, { useCallback, useEffect, useRef, useState } from "react";
import { endSession, WS_BASE } from "../api";
import { G } from "../theme";
import { LiveSessionConfig } from "../types";
import { useGeminiLive } from "../hooks/useGeminiLive";

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
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const { isConnected, isAiSpeaking, audioLevel, error, startSession, stopSession } = useGeminiLive({
    userId: config.user_id,
    sessionId: config.session_id,
    mode: config.mode,
    baseUrl: WS_BASE,
    token: config.backend_token,
    onTranscript: (text) => setUserTranscript(prev => `${prev} ${text}`.trim()),
    onAiTranscript: (text) => {
        setAiMsg(text);
        // If AI is proposing a new question, we might want to sync index here
        // though better to do it via 'complete' or separate events if needed.
    },
    onEmotion: (emo, conf) => {
        setEmotion(emo);
        setConfidence(conf);
    },
    onInterrupt: () => {
        // Handle visual cues for interruption if needed
    },
    onComplete: (data) => {
        if (data.is_finished) {
            handleEnd();
        }
    },
    onError: (err) => console.error("Gemini Live Error:", err)
  });

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
    <div style={{ minHeight: "100vh", background: G.bg, fontFamily: G.font, display: "grid", gridTemplateColumns: "1fr 340px", overflow: "hidden" }}>
      <div style={{ display: "flex", flexDirection: "column", padding: "1.5rem", gap: "1rem" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ fontWeight: 800, fontSize: "1.1rem", color: G.text, letterSpacing: "-0.02em" }}>
              Round<span style={{ color: G.accent }}>Zero</span>
            </span>
            <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "0.3rem 0.8rem", fontFamily: G.mono, fontSize: "0.7rem", color: G.accent }}>
              ● GEMINI LIVE
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
            <span style={{ fontFamily: G.mono, fontSize: "0.8rem", color: G.muted }}>{fmt(elapsed)}</span>
            <span style={{ fontFamily: G.mono, fontSize: "0.75rem", color: G.muted }}>
              {questionIndex}/{config.total_questions} questions
            </span>
            <button onClick={handleEnd} style={{ padding: "0.4rem 1rem", background: "rgba(244,63,94,0.1)", border: "1px solid rgba(244,63,94,0.3)", color: G.accent3, fontFamily: G.font, fontSize: "0.8rem", cursor: "pointer" }}>
              End Session
            </button>
          </div>
        </div>

        <div style={{ flex: 1, background: G.surface, border: `1px solid ${G.border}`, position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center", minHeight: "320px" }}>
          {!isConnected ? (
            <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg, #0d0d1a 0%, #111126 100%)", padding: "2rem", textAlign: "center" }}>
              <div style={{ width: 44, height: 44, border: `3px solid ${G.border}`, borderTopColor: G.accent, borderRadius: "50%", animation: "spin 1s linear infinite", marginBottom: "1.5rem" }} />
              <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
              <h3 style={{ color: G.text, marginBottom: "0.5rem", fontSize: "1.2rem", fontWeight: 600 }}>Connecting to Gemini Live...</h3>
              <p style={{ color: G.muted, fontSize: "0.9rem", maxWidth: "400px", lineHeight: 1.5 }}>
                Establishing bidirectional audio stream. Please ensure your microphone is enabled.
              </p>
            </div>
          ) : (
            <div style={{ width: "100%", height: "100%", background: "linear-gradient(135deg, #0d0d1a 0%, #111126 100%)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
              <div style={{ 
                width: 110, 
                height: 110, 
                borderRadius: "50%", 
                background: `linear-gradient(135deg, ${G.surface2}, ${G.border})`, 
                border: `2px solid ${isAiSpeaking ? G.accent : G.border}`, 
                display: "flex", 
                alignItems: "center", 
                justifyContent: "center", 
                fontSize: "2.6rem", 
                boxShadow: isAiSpeaking ? `0 0 ${20 + audioLevel}px ${G.accent}` : 'none', 
                transition: 'all 0.15s ease' 
              }}>
                🤖
              </div>
              <div style={{ position: "absolute", top: 12, right: 12, padding: "4px 10px", background: "rgba(0, 0, 0, 0.4)", backdropFilter: "blur(4px)", borderRadius: "20px", border: `1px solid ${G.accent}44`, display: "flex", alignItems: "center", gap: 6, zIndex: 10 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: isAiSpeaking ? G.accent : G.muted, boxShadow: isAiSpeaking ? `0 0 8px ${G.accent}` : 'none' }} />
                <span style={{ color: "#fff", fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase" }}>
                  {isAiSpeaking ? 'AI Speaking' : 'Listening...'}
                </span>
              </div>
              <p style={{ position: "absolute", bottom: "1.2rem", color: G.muted, fontSize: "0.82rem" }}>
                Multimodal AI Active · Live Feedback
              </p>
            </div>
          )}

          <div style={{ position: "absolute", top: "1rem", left: "1rem", display: "flex", alignItems: "center", gap: "0.5rem", background: "rgba(0,0,0,0.7)", padding: "0.4rem 0.8rem", border: `1px solid ${emotionColor(emotion)}30` }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: emotionColor(emotion), boxShadow: `0 0 6px ${emotionColor(emotion)}` }} />
            <span style={{ fontFamily: G.mono, fontSize: "0.68rem", color: emotionColor(emotion), textTransform: "capitalize" }}>{emotion}</span>
          </div>
          <div style={{ position: "absolute", top: "1rem", right: "1rem", background: "rgba(0,0,0,0.7)", padding: "0.4rem 0.8rem", border: `1px solid ${G.border}`, fontFamily: G.mono, fontSize: "0.68rem", color: G.muted }}>
            {fillers} fillers detected
          </div>
        </div>

        <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "1rem 1.5rem", display: "flex", alignItems: "center", gap: "0.8rem" }}>
          <canvas ref={canvasRef} width={600} height={40} style={{ flex: 1 }} />
        </div>

        <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1rem 1.2rem" }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Real-time User Transcript
          </div>
          <div style={{ 
            minHeight: "100px", 
            maxHeight: "150px", 
            overflowY: "auto", 
            padding: "1rem", 
            background: G.surface, 
            color: G.text, 
            border: `1px solid ${G.border}`, 
            fontFamily: G.font, 
            fontSize: "0.9rem",
            lineHeight: 1.5
          }}>
            {userTranscript || "Transcript will appear here as you speak..."}
          </div>
          {error && <p style={{ marginTop: "0.55rem", color: G.accent3, fontSize: "0.78rem" }}>{error}</p>}
        </div>
      </div>

      <div style={{ background: G.surface, borderLeft: `1px solid ${G.border}`, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "1.5rem", borderBottom: `1px solid ${G.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.8rem", marginBottom: "1rem" }}>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`, border: `1px solid ${G.accent}50`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "1rem", flexShrink: 0 }}>
              AI
            </div>
            <div>
              <div style={{ fontSize: "0.85rem", fontWeight: 600, color: G.text }}>Gemini Coach</div>
              <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: isAiSpeaking ? G.accent : G.muted }}>
                {isAiSpeaking ? "speaking" : isConnected ? "listening" : "offline"}
              </div>
            </div>
          </div>
          <div style={{ background: G.surface2, padding: "1rem", borderRadius: "2px" }}>
            <p style={{ fontSize: "0.83rem", color: G.text, lineHeight: 1.6 }}>{aiMsg}</p>
          </div>
        </div>

        <div style={{ padding: "1.5rem", borderBottom: `1px solid ${G.border}` }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.accent, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "0.7rem" }}>
            Current Question
          </div>
          <p style={{ fontSize: "0.88rem", color: G.text, lineHeight: 1.6, fontWeight: 500 }}>{question}</p>
        </div>

        <div style={{ padding: "1.5rem", borderBottom: `1px solid ${G.border}` }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem" }}>
            <span style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>Confidence</span>
            <span style={{ fontFamily: G.mono, fontSize: "1rem", fontWeight: 600, color: confidence > 65 ? G.accent : confidence > 40 ? G.accent2 : G.accent3 }}>{Math.round(confidence)}</span>
          </div>
          <div style={{ height: 6, background: G.surface2, borderRadius: "3px", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${confidence}%`, background: confidence > 65 ? G.accent : confidence > 40 ? G.accent2 : G.accent3, transition: "width 0.6s ease, background 0.6s ease", borderRadius: "3px" }} />
          </div>
        </div>

        <div style={{ padding: "1.5rem", flex: 1 }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem" }}>Session Stats</div>
          {[
            ["Mode", config.mode === "buddy" ? "Buddy" : "Strict"],
            ["Difficulty", config.difficulty],
            ["Time elapsed", fmt(elapsed)],
          ].map(([key, value]) => (
            <div key={String(key)} style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.8rem", fontSize: "0.82rem" }}>
              <span style={{ color: G.muted }}>{key}</span>
              <span style={{ color: G.text, textTransform: "capitalize" }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
