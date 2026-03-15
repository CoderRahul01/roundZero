import React, { useCallback, useEffect, useRef, useState } from "react";
import { endSession, WS_BASE } from "../api";
import { G } from "../theme";
import { LiveSessionConfig } from "../types";
import { useGeminiLive } from "../hooks/useGeminiLive";

// ─── CSS Animations (injected once) ──────────────────────────────────────────
const ANIM_CSS = `
@keyframes ring-out {
  0%   { transform: translate(-50%,-50%) scale(1);   opacity: 0.7; }
  100% { transform: translate(-50%,-50%) scale(2.6); opacity: 0;   }
}
@keyframes user-ring-out {
  0%   { transform: translate(-50%,-50%) scale(1);   opacity: 0.5; }
  100% { transform: translate(-50%,-50%) scale(1.9); opacity: 0;   }
}
@keyframes orb-idle {
  0%,100% { transform: scale(1);    }
  50%     { transform: scale(1.025);}
}
@keyframes orb-user {
  0%,100% { transform: scale(1);    }
  50%     { transform: scale(1.04); }
}
@keyframes q-enter {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0);    }
}
@keyframes status-enter {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0);   }
}
@keyframes think-dot {
  0%,60%,100% { transform: translateY(0);  opacity: 0.3; }
  30%         { transform: translateY(-5px); opacity: 1;  }
}
@keyframes score-pop {
  0%   { transform: scale(0.7); opacity: 0; }
  60%  { transform: scale(1.15);            }
  100% { transform: scale(1);   opacity: 1; }
}
@keyframes waveform-tick {
  0%,100% { transform: scaleY(0.3); }
  50%     { transform: scaleY(1);   }
}
`;

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmtTime(s: number) {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
function emotionColor(e: string): string {
  const m: Record<string, string> = {
    confident: G.accent, neutral: "#94a3b8",
    confused: G.accent2, focused: "#818cf8", nervous: G.accent3,
  };
  return m[e] ?? "#94a3b8";
}
function scoreColor(s: number): string {
  if (s >= 80) return G.accent;
  if (s >= 60) return G.accent2;
  return G.accent3;
}

// ─── Types ────────────────────────────────────────────────────────────────────
type SpeakState = "connecting" | "idle" | "ai-speaking" | "user-speaking";

// ─── Mini Components ─────────────────────────────────────────────────────────
function ThinkingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          display: "inline-block", width: 5, height: 5, borderRadius: "50%",
          background: G.muted,
          animation: `think-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
        }} />
      ))}
    </span>
  );
}

function SpeakStateLabel({ state, isConnected }: { state: SpeakState; isConnected: boolean }) {
  const map: Record<SpeakState, { text: string; color: string }> = {
    connecting:    { text: "Connecting…",   color: G.muted  },
    idle:          { text: "Listening",      color: G.muted  },
    "ai-speaking": { text: "AI Speaking",    color: G.accent },
    "user-speaking": { text: "Your Answer", color: "#34d399" },
  };
  const { text, color } = map[state];
  return (
    <div key={state} style={{
      fontFamily: G.mono, fontSize: "0.65rem", color,
      letterSpacing: "0.12em", textTransform: "uppercase",
      display: "flex", alignItems: "center", gap: 8,
      animation: "status-enter 0.25s ease",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%", background: color,
        boxShadow: `0 0 6px ${color}`,
        display: "inline-block",
      }} />
      {text}
      {state === "idle" && isConnected && <ThinkingDots />}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export function InterviewScreen({
  config, onEnd,
}: {
  config: LiveSessionConfig;
  onEnd: () => void;
}) {
  // ── State ──────────────────────────────────────────────────────────────────
  const [sessionStarted, setSessionStarted]   = useState(false);
  const [question, setQuestion]               = useState(config.first_question);
  const [questionIndex, setQuestionIndex]     = useState(config.question_index);
  const [questionKey, setQuestionKey]         = useState(0);
  const [aiMsg, setAiMsg]                     = useState("Waiting for Aria…");
  const [confidence, setConfidence]           = useState(68);
  const [emotion, setEmotion]                 = useState("neutral");
  const [fillers, setFillers]                 = useState(0);
  const [elapsed, setElapsed]                 = useState(0);
  const [userTranscript, setUserTranscript]   = useState("");
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [speakState, setSpeakState]           = useState<SpeakState>("connecting");
  const [questionScores, setQuestionScores]   = useState<Record<number, number>>({});
  const [aiSpeakSec, setAiSpeakSec]           = useState(0);
  const [userSpeakSec, setUserSpeakSec]       = useState(0);

  // ── Refs ───────────────────────────────────────────────────────────────────
  const videoRef              = useRef<HTMLVideoElement>(null);
  const screenVideoRef        = useRef<HTMLVideoElement>(null);
  const screenStreamRef       = useRef<MediaStream | null>(null);
  const screenFrameIntervalRef= useRef<number | null>(null);
  const waveCanvasRef         = useRef<HTMLCanvasElement>(null);
  const isScreenSharingRef    = useRef(false);
  const toggleScreenShareRef  = useRef<() => Promise<void>>(() => Promise.resolve());
  const aiSpeakStartRef       = useRef<number | null>(null);
  const userSpeakStartRef     = useRef<number | null>(null);
  const transcriptEndRef      = useRef<HTMLDivElement>(null);

  // ── Transcript update ──────────────────────────────────────────────────────
  const onTranscriptUpdate = useCallback((text: string) => {
    setUserTranscript(prev => {
      if (prev.endsWith(text)) return prev;
      return `${prev} ${text}`.trim();
    });
    const re = /\b(um|uh|like|basically|actually|literally|you know|i mean)\b/gi;
    const m = text.match(re);
    if (m) setFillers(p => p + m.length);
  }, []);

  // ── useGeminiLive ──────────────────────────────────────────────────────────
  const {
    isConnected, isAiSpeaking, audioLevel, error,
    startSession, stopSession, sendMessage, resumeAudio,
  } = useGeminiLive({
    userId: config.user_id, sessionId: config.session_id,
    mode: config.mode, baseUrl: WS_BASE, token: config.backend_token,
    videoSource: config.videoSource, externalStream: config.externalStream,
    onTranscript: onTranscriptUpdate,
    onAiTranscript: (text) => {
      try {
        const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
        const rawJson = jsonMatch ? jsonMatch[1] : text;
        const data = JSON.parse(rawJson);
        if (data.question_type === "NEW_QUESTION") {
          setQuestionIndex(data.question_number);
          setQuestion(data.content);
          setQuestionKey(k => k + 1);
        } else if (data.question_type === "FOLLOW_UP") {
          setQuestion(data.content);
          setQuestionKey(k => k + 1);
        }
        setAiMsg(data.content);
      } catch {
        setAiMsg(text);
      }
    },
    onEmotion: (emo, conf) => { setEmotion(emo); setConfidence(conf); },
    onInterrupt: () => {},
    onComplete: (data) => {
      if (data.is_finished || data.type === "interview_end") handleEnd();
    },
    onScreenShareRequest: () => { if (!isScreenSharingRef.current) toggleScreenShareRef.current(); },
    onScreenShareStop:    () => { if (isScreenSharingRef.current)  toggleScreenShareRef.current(); },
    onAgentEvent: (data) => {
      if (data.type === "tool_call") {
        const { name, args } = data.payload ?? {};
        if (name === "sync_interview_state") {
          setQuestionIndex(args.question_index + 1);
          setQuestion(args.question_text);
          setQuestionKey(k => k + 1);
        }
      }
      if (data.type === "score_update") {
        const { question_index, score } = data.payload ?? {};
        if (question_index != null && score != null) {
          setQuestionScores(prev => ({ ...prev, [question_index]: Math.round(score) }));
        }
      }
    },
    onError: (err) => console.error("Gemini Live Error:", err),
  });

  // ── Derived state ──────────────────────────────────────────────────────────
  const isUserSpeaking = audioLevel > 10 && !isAiSpeaking;

  // ── Speaking state + time tracking ────────────────────────────────────────
  useEffect(() => {
    if (!isConnected) {
      setSpeakState("connecting");
    } else if (isAiSpeaking) {
      setSpeakState("ai-speaking");
      if (aiSpeakStartRef.current === null) aiSpeakStartRef.current = Date.now();
      if (userSpeakStartRef.current !== null) {
        setUserSpeakSec(t => t + Math.round((Date.now() - userSpeakStartRef.current!) / 1000));
        userSpeakStartRef.current = null;
      }
    } else if (isUserSpeaking) {
      setSpeakState("user-speaking");
      if (userSpeakStartRef.current === null) userSpeakStartRef.current = Date.now();
      if (aiSpeakStartRef.current !== null) {
        setAiSpeakSec(t => t + Math.round((Date.now() - aiSpeakStartRef.current!) / 1000));
        aiSpeakStartRef.current = null;
      }
    } else {
      setSpeakState("idle");
    }
  }, [isConnected, isAiSpeaking, isUserSpeaking]);

  // ── Auto-scroll transcript ─────────────────────────────────────────────────
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [userTranscript]);

  // ── Camera preview ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (config.videoSource === "camera" && isConnected) {
      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => { if (videoRef.current) videoRef.current.srcObject = stream; })
        .catch(() => {});
    }
    return () => {
      if (videoRef.current?.srcObject)
        (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
    };
  }, [config.videoSource, isConnected]);

  // ── Screen share ───────────────────────────────────────────────────────────
  const toggleScreenShare = useCallback(async () => {
    if (isScreenSharing) {
      if (screenFrameIntervalRef.current) { clearInterval(screenFrameIntervalRef.current); screenFrameIntervalRef.current = null; }
      screenStreamRef.current?.getTracks().forEach(t => t.stop());
      screenStreamRef.current = null;
      isScreenSharingRef.current = false;
      setIsScreenSharing(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        screenStreamRef.current = stream;
        if (screenVideoRef.current) screenVideoRef.current.srcObject = stream;
        stream.getVideoTracks()[0].onended = () => {
          if (screenFrameIntervalRef.current) { clearInterval(screenFrameIntervalRef.current); screenFrameIntervalRef.current = null; }
          isScreenSharingRef.current = false;
          setIsScreenSharing(false);
          screenStreamRef.current = null;
        };
        const canvas = document.createElement("canvas");
        canvas.width = 768; canvas.height = 432;
        const ctx = canvas.getContext("2d");
        const videoEl = screenVideoRef.current;
        screenFrameIntervalRef.current = window.setInterval(() => {
          if (ctx && videoEl && videoEl.readyState >= 2) {
            ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
            const base64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
            sendMessage({ type: "screen_frame", data: base64, mimeType: "image/jpeg" });
          }
        }, 1000);
        isScreenSharingRef.current = true;
        setIsScreenSharing(true);
      } catch {}
    }
  }, [isScreenSharing, sendMessage]);

  useEffect(() => { toggleScreenShareRef.current = toggleScreenShare; }, [toggleScreenShare]);

  // ── Session timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    const t = setInterval(() => setElapsed(v => v + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // ── Cleanup refs ───────────────────────────────────────────────────────────
  const stopSessionRef = useRef(stopSession);
  useEffect(() => { stopSessionRef.current = stopSession; }, [stopSession]);
  useEffect(() => () => stopSessionRef.current(), []);

  // ── Waveform canvas ────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = waveCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    const bars = 52;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bw = canvas.width / bars - 1.5;
      const color = isAiSpeaking ? G.accent
                  : isUserSpeaking ? "#34d399"
                  : G.border;
      ctx.globalAlpha = 0.85;
      for (let i = 0; i < bars; i++) {
        const h = isAiSpeaking
          ? Math.max(4, (Math.random() * 0.7 + 0.3) * (8 + Math.random() * 28))
          : audioLevel > 8
            ? Math.max(4, (Math.random() * 0.5 + 0.5) * (audioLevel / 5) + 4)
            : Math.abs(Math.sin(Date.now() / 400 + i * 0.7)) * 4 + 3;
        ctx.fillStyle = color;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(i * (bw + 1.5), (canvas.height - h) / 2, bw, h, 2);
        else ctx.rect(i * (bw + 1.5), (canvas.height - h) / 2, bw, h);
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(raf);
  }, [isConnected, isAiSpeaking, audioLevel, isUserSpeaking]);

  // ── Handle end ─────────────────────────────────────────────────────────────
  const handleEnd = async () => {
    if (screenFrameIntervalRef.current) { clearInterval(screenFrameIntervalRef.current); screenFrameIntervalRef.current = null; }
    stopSession();
    try { await endSession(config.session_id); } finally { onEnd(); }
  };

  // ─── Orb state ─────────────────────────────────────────────────────────────
  const orbColor   = isAiSpeaking   ? G.accent
                   : isUserSpeaking ? "#34d399"
                   : G.border;
  const orbGlow    = isAiSpeaking   ? `0 0 40px ${G.accent}55, 0 0 80px ${G.accent}22`
                   : isUserSpeaking ? `0 0 24px #34d39944`
                   : "none";
  const orbAnim    = isAiSpeaking   ? "none"
                   : isUserSpeaking ? "orb-user 1.2s ease-in-out infinite"
                   : isConnected    ? "orb-idle 3s ease-in-out infinite"
                   : "none";

  const ringColor  = isAiSpeaking ? G.accent : "#34d399";
  const rings      = isAiSpeaking ? [0, 0.4, 0.8] : isUserSpeaking ? [0, 0.5] : [];

  return (
    <>
      {/* Inject keyframe animations */}
      <style>{ANIM_CSS}</style>

      <div style={{
        minHeight: "100vh", background: G.bg, fontFamily: G.font,
        display: "flex", flexDirection: "column", overflow: "hidden",
      }}>

        {/* ── HEADER BAR ─────────────────────────────────────────────────── */}
        <div style={{
          height: 52, background: G.surface, borderBottom: `1px solid ${G.border}`,
          display: "flex", alignItems: "center", padding: "0 1.5rem", gap: "1.5rem",
          flexShrink: 0,
        }}>
          {/* Logo */}
          <span style={{ fontWeight: 800, fontSize: "1rem", color: G.text, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </span>

          {/* Live badge */}
          <div style={{
            background: "transparent", border: `1px solid ${G.accent}55`,
            padding: "2px 8px", fontFamily: G.mono, fontSize: "0.58rem", color: G.accent,
            letterSpacing: "0.1em",
          }}>
            ● LIVE
          </div>

          {/* Question progress dots */}
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {Array.from({ length: config.total_questions }).map((_, i) => {
              const done    = i < questionIndex - 1;
              const current = i === questionIndex - 1;
              const sc      = questionScores[i];
              return (
                <div key={i} style={{ position: "relative" }}>
                  <div style={{
                    width: current ? 12 : 8, height: current ? 12 : 8,
                    borderRadius: "50%",
                    background: done    ? (sc != null ? scoreColor(sc) : G.accent)
                              : current ? G.accent2
                              : G.border,
                    boxShadow: current ? `0 0 10px ${G.accent2}` : "none",
                    transition: "all 0.3s",
                    cursor: "default",
                  }} title={sc != null ? `Q${i+1}: ${sc}%` : `Q${i+1}`} />
                  {sc != null && (
                    <div style={{
                      position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)",
                      fontFamily: G.mono, fontSize: "0.5rem", color: scoreColor(sc),
                      whiteSpace: "nowrap", animation: "score-pop 0.4s ease",
                    }}>{sc}</div>
                  )}
                </div>
              );
            })}
            <span style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, marginLeft: 4 }}>
              Q{questionIndex}/{config.total_questions}
            </span>
          </div>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Mode badge */}
          <div style={{
            fontFamily: G.mono, fontSize: "0.6rem", color: G.accent2,
            border: `1px solid ${G.accent2}44`, padding: "2px 8px",
            textTransform: "uppercase", letterSpacing: "0.08em",
          }}>
            {config.mode}
          </div>

          {/* Timer */}
          <div style={{
            fontFamily: G.mono, fontSize: "0.9rem", fontWeight: 600,
            color: elapsed > 2400 ? G.accent3 : G.text, letterSpacing: "0.05em",
          }}>
            {fmtTime(elapsed)}
          </div>

          {/* Quit */}
          <button
            onClick={handleEnd}
            style={{
              padding: "0.35rem 0.9rem", background: "transparent",
              border: `1px solid ${G.border}`, color: G.accent3,
              fontFamily: G.font, fontSize: "0.75rem", cursor: "pointer",
              fontWeight: 600, letterSpacing: "0.02em",
            }}
          >
            Quit
          </button>
        </div>

        {/* ── BODY 3-COLUMN ──────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "260px 1fr 280px", overflow: "hidden" }}>

          {/* ── LEFT: CANDIDATE + TRANSCRIPT ─────────────────────────────── */}
          <div style={{
            background: G.surface, borderRight: `1px solid ${G.border}`,
            display: "flex", flexDirection: "column", padding: "1.2rem", gap: "1rem",
            overflow: "hidden",
          }}>
            {/* Candidate profile */}
            <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.9rem" }}>
              <div style={{ fontSize: "0.85rem", color: G.text, fontWeight: 600 }}>
                {config.name || "Candidate"}
              </div>
              <div style={{ fontSize: "0.72rem", color: G.muted, marginTop: 3 }}>
                {config.role}
              </div>
              <div style={{
                marginTop: 8, display: "flex", gap: 6, alignItems: "center",
                fontFamily: G.mono, fontSize: "0.6rem",
              }}>
                <span style={{ color: isConnected ? G.accent : G.accent3 }}>
                  {isConnected ? "● Connected" : "○ Disconnected"}
                </span>
                {error && <span style={{ color: G.accent3 }}>⚠ {error}</span>}
              </div>
            </div>

            {/* Question score cards */}
            <div>
              <div style={{
                fontFamily: G.mono, fontSize: "0.58rem", color: G.muted,
                textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8,
              }}>Question Tracker</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {Array.from({ length: config.total_questions }).map((_, i) => {
                  const qi   = i + 1;
                  const done = qi < questionIndex;
                  const cur  = qi === questionIndex;
                  const sc   = questionScores[i];
                  return (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "0.4rem 0.6rem",
                      background: cur ? `${G.accent2}11` : "transparent",
                      border: `1px solid ${cur ? G.accent2 + "55" : G.border}`,
                      transition: "all 0.3s",
                    }}>
                      <div style={{
                        width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: done ? (sc != null ? scoreColor(sc) + "22" : G.accent + "22")
                                  : cur  ? G.accent2 + "22"
                                  : G.surface2,
                        border: `1px solid ${done ? (sc != null ? scoreColor(sc) : G.accent) : cur ? G.accent2 : G.border}`,
                        fontFamily: G.mono, fontSize: "0.55rem",
                        color: done ? (sc != null ? scoreColor(sc) : G.accent) : cur ? G.accent2 : G.muted,
                        fontWeight: 700,
                      }}>
                        {done ? (sc != null ? "✓" : "✓") : cur ? qi : qi}
                      </div>
                      <span style={{
                        fontSize: "0.72rem", color: cur ? G.text : done ? G.muted : G.muted + "88",
                        flex: 1, fontWeight: cur ? 600 : 400,
                      }}>
                        Q{qi}
                      </span>
                      {sc != null && (
                        <span style={{
                          fontFamily: G.mono, fontSize: "0.62rem", color: scoreColor(sc),
                          fontWeight: 700, animation: "score-pop 0.4s ease",
                        }}>{sc}%</span>
                      )}
                      {cur && !sc && (
                        <span style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.accent2 }}>now</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Live transcript */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
              <div style={{
                fontFamily: G.mono, fontSize: "0.58rem", color: G.muted,
                textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8,
              }}>Your Transcript</div>
              <div style={{
                flex: 1, background: G.surface2, border: `1px solid ${G.border}`,
                padding: "0.8rem", fontSize: "0.78rem", color: G.text,
                lineHeight: 1.65, overflowY: "auto", minHeight: 0,
              }}>
                {userTranscript ? (
                  <>
                    {userTranscript}
                    <div ref={transcriptEndRef} />
                  </>
                ) : (
                  <span style={{ color: G.muted }}>Waiting for your voice…</span>
                )}
              </div>
            </div>
          </div>

          {/* ── CENTER: ORB + QUESTION + WAVEFORM ────────────────────────── */}
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "space-between", padding: "2rem 2.5rem", gap: "1.5rem",
            overflow: "hidden",
          }}>
            {/* Question display */}
            <div style={{
              width: "100%", textAlign: "center", flex: "0 0 auto",
            }}>
              <div style={{
                fontFamily: G.mono, fontSize: "0.62rem", color: G.accent,
                letterSpacing: "0.25em", textTransform: "uppercase", marginBottom: "0.8rem",
              }}>
                Current Question
              </div>
              <div
                key={questionKey}
                style={{
                  fontSize: "clamp(1.4rem, 2.5vw, 2.4rem)", fontWeight: 700,
                  color: G.text, lineHeight: 1.25, letterSpacing: "-0.02em",
                  maxWidth: 680, margin: "0 auto",
                  animation: "q-enter 0.4s ease",
                }}
              >
                {question || "Introduce yourself to begin."}
              </div>
            </div>

            {/* ── AI ORB ──────────────────────────────────────────────────── */}
            <div style={{ position: "relative", width: 180, height: 180, flexShrink: 0 }}>
              {/* Expanding rings */}
              {rings.map((delay, i) => (
                <div key={i} style={{
                  position: "absolute", left: "50%", top: "50%",
                  width: 180, height: 180, borderRadius: "50%",
                  border: `1.5px solid ${ringColor}`,
                  animation: `ring-out 1.8s ease-out ${delay}s infinite`,
                  pointerEvents: "none",
                }} />
              ))}

              {/* Orb body */}
              <div style={{
                position: "absolute", inset: 0, borderRadius: "50%",
                background: isAiSpeaking
                  ? `radial-gradient(circle at 38% 35%, ${G.accent}18, ${G.bg})`
                  : isUserSpeaking
                    ? `radial-gradient(circle at 38% 35%, #34d39918, ${G.bg})`
                    : `radial-gradient(circle at 38% 35%, ${G.surface}, ${G.bg})`,
                border: `2px solid ${orbColor}`,
                boxShadow: orbGlow,
                animation: orbAnim,
                transition: "border-color 0.3s, box-shadow 0.4s",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {/* Inner icon — SVG waveform bars */}
                <div style={{ display: "flex", gap: 3, alignItems: "center", height: 36 }}>
                  {[0.4, 0.7, 1, 0.85, 0.55, 0.75, 0.45].map((scale, i) => (
                    <div key={i} style={{
                      width: 4, borderRadius: 2,
                      background: orbColor,
                      opacity: isConnected ? 0.9 : 0.3,
                      height: `${scale * 100}%`,
                      animation: (isAiSpeaking || isUserSpeaking)
                        ? `waveform-tick ${0.5 + i * 0.08}s ease-in-out ${i * 0.07}s infinite alternate`
                        : "none",
                      transition: "background 0.3s",
                    }} />
                  ))}
                </div>
              </div>
            </div>

            {/* State label */}
            <SpeakStateLabel state={speakState} isConnected={isConnected} />

            {/* Waveform bar */}
            <div style={{
              width: "100%", background: G.surface2,
              border: `1px solid ${G.border}`, padding: "1rem", flexShrink: 0,
            }}>
              <div style={{
                fontFamily: G.mono, fontSize: "0.55rem", color: G.muted,
                textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8,
                display: "flex", justifyContent: "space-between",
              }}>
                <span>Audio</span>
                <span style={{ color: isAiSpeaking ? G.accent : isUserSpeaking ? "#34d399" : G.muted }}>
                  {isAiSpeaking ? "AI output" : isUserSpeaking ? "Mic active" : "Silent"}
                </span>
              </div>
              <canvas ref={waveCanvasRef} width={700} height={52} style={{ width: "100%", height: 52, display: "block" }} />
            </div>
          </div>

          {/* ── RIGHT: METRICS + CAMERA ───────────────────────────────────── */}
          <div style={{
            background: G.surface, borderLeft: `1px solid ${G.border}`,
            display: "flex", flexDirection: "column", padding: "1.2rem", gap: "1rem",
            overflow: "hidden",
          }}>
            {/* Camera / vision preview */}
            <div>
              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                marginBottom: 8,
              }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                  Vision
                </div>
                <button
                  onClick={toggleScreenShare}
                  style={{
                    background: isScreenSharing ? G.accent2 : "transparent",
                    border: `1px solid ${isScreenSharing ? G.accent2 : G.border}`,
                    color: isScreenSharing ? "#000" : G.muted,
                    fontSize: "0.58rem", padding: "2px 7px", cursor: "pointer",
                    textTransform: "uppercase", fontWeight: 700,
                  }}
                >
                  {isScreenSharing ? "Stop" : "Screen"}
                </button>
              </div>
              <div style={{
                background: "#000", border: `2px solid ${isConnected ? orbColor : G.border}`,
                overflow: "hidden", position: "relative",
                transition: "border-color 0.3s",
              }}>
                {isScreenSharing && (
                  <div style={{ width: "100%", aspectRatio: "16/9" }}>
                    <video ref={screenVideoRef} autoPlay playsInline style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                  </div>
                )}
                <div style={{ width: "100%", aspectRatio: "4/3", position: "relative" }}>
                  {config.videoSource === "camera" ? (
                    <video ref={videoRef} autoPlay playsInline muted style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scaleX(-1)" }} />
                  ) : (
                    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: G.muted, fontSize: "0.75rem" }}>
                      Audio Only
                    </div>
                  )}
                  <div style={{
                    position: "absolute", bottom: 7, left: 7,
                    background: "rgba(0,0,0,0.65)", padding: "2px 8px", borderRadius: 8,
                    border: `1px solid ${emotionColor(emotion)}`,
                  }}>
                    <span style={{ color: emotionColor(emotion), fontSize: "0.6rem", fontWeight: 600, textTransform: "uppercase" }}>
                      {emotion}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Confidence meter */}
            <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, textTransform: "uppercase" }}>
                  Confidence
                </span>
                <span style={{ fontSize: "1.1rem", fontWeight: 800, color: confidence > 65 ? G.accent : G.accent2 }}>
                  {Math.round(confidence)}%
                </span>
              </div>
              <div style={{ height: 6, background: G.bg, borderRadius: 3, overflow: "hidden" }}>
                <div style={{
                  height: "100%", width: `${confidence}%`,
                  background: confidence > 65 ? G.accent : G.accent2,
                  transition: "width 0.8s ease",
                }} />
              </div>
              <div style={{ fontSize: "0.67rem", color: G.muted, marginTop: 6, textAlign: "center" }}>
                {confidence > 75 ? "Excellent composure" : confidence > 50 ? "Steady — keep going" : "Take a breath, relax"}
              </div>
            </div>

            {/* Stats grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {/* Fillers */}
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.8rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase" }}>Fillers</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 700, color: fillers > 5 ? G.accent3 : G.text, marginTop: 4 }}>
                  {fillers}
                </div>
              </div>

              {/* Words spoken (rough estimate) */}
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.8rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase" }}>Words</div>
                <div style={{ fontSize: "1.6rem", fontWeight: 700, color: G.text, marginTop: 4 }}>
                  {userTranscript.split(/\s+/).filter(Boolean).length}
                </div>
              </div>

              {/* User speak time */}
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.8rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase" }}>You</div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#34d399", marginTop: 4, fontFamily: G.mono }}>
                  {fmtTime(userSpeakSec)}
                </div>
              </div>

              {/* AI speak time */}
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.8rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase" }}>AI</div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: G.accent, marginTop: 4, fontFamily: G.mono }}>
                  {fmtTime(aiSpeakSec)}
                </div>
              </div>
            </div>

            {/* AI Feedback */}
            <div style={{ flex: 1, background: G.surface2, border: `1px solid ${G.border}`, padding: "1rem", overflow: "hidden", display: "flex", flexDirection: "column" }}>
              <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 8 }}>
                AI Message
              </div>
              <div style={{
                fontSize: "0.78rem", color: G.text, lineHeight: 1.55,
                background: G.bg, padding: "0.8rem",
                borderLeft: `2px solid ${G.accent}`,
                flex: 1, overflowY: "auto",
              }}>
                {aiMsg || <span style={{ color: G.muted }}>Waiting for Aria…</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── BEGIN INTERVIEW OVERLAY ─────────────────────────────────────── */}
      {!sessionStarted && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(5,5,8,0.92)",
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: "1.8rem",
          backdropFilter: "blur(8px)",
        }}>
          {/* Orb preview */}
          <div style={{
            width: 90, height: 90, borderRadius: "50%",
            border: `2px solid ${G.accent}`,
            background: `radial-gradient(circle at 38% 35%, ${G.accent}18, ${G.bg})`,
            boxShadow: `0 0 40px ${G.accent}33`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ display: "flex", gap: 3, alignItems: "center", height: 22 }}>
              {[0.4, 0.7, 1, 0.85, 0.55, 0.75, 0.45].map((s, i) => (
                <div key={i} style={{ width: 3, borderRadius: 2, background: G.accent, height: `${s * 100}%`, opacity: 0.85 }} />
              ))}
            </div>
          </div>

          <div style={{ fontWeight: 800, fontSize: "2rem", color: G.text, letterSpacing: "-0.03em" }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </div>

          <div style={{ textAlign: "center", maxWidth: 380 }}>
            <p style={{ color: G.muted, fontSize: "0.9rem", margin: 0 }}>
              Your session is ready. Aria will guide you through {config.total_questions} questions.
            </p>
            <p style={{ color: G.muted + "88", fontSize: "0.78rem", marginTop: 8 }}>
              Allow microphone access when prompted. Speak clearly and naturally.
            </p>
          </div>

          <button
            onClick={() => {
              setSessionStarted(true);
              startSession();
            }}
            style={{
              padding: "0.85rem 3rem",
              background: G.accent, border: "none",
              color: "#000", fontFamily: G.font,
              fontSize: "0.95rem", fontWeight: 700, cursor: "pointer",
              letterSpacing: "-0.01em",
            }}
          >
            Begin Interview →
          </button>

          <div style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, letterSpacing: "0.05em" }}>
            {config.name} · {config.role} · {config.mode} mode
          </div>
        </div>
      )}
    </>
  );
}
