import React, { useCallback, useEffect, useRef, useState } from "react";
import { endSession, WS_BASE } from "../api";
import { G } from "../theme";
import { LiveSessionConfig } from "../types";
import { useGeminiLive } from "../hooks/useGeminiLive";

// ─── CSS Animations ───────────────────────────────────────────────────────────
const ANIM_CSS = `
@keyframes ring-out {
  0%   { transform: scale(1);   opacity: 0.6; }
  100% { transform: scale(2.2); opacity: 0;   }
}
@keyframes orb-idle {
  0%,100% { transform: scale(1);     }
  50%     { transform: scale(1.025); }
}
@keyframes q-enter {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0);    }
}
@keyframes status-enter {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes bar-dance {
  0%,100% { transform: scaleY(0.35); }
  50%     { transform: scaleY(1);    }
}
@keyframes q-new-flash {
  0%,100% { background: transparent; box-shadow: none; }
  25%,75% { background: rgba(110,231,183,0.12); box-shadow: 0 0 14px rgba(110,231,183,0.2); }
}
@keyframes badge-pop {
  0%   { opacity: 0; transform: translateY(-5px) scale(0.9); }
  12%  { opacity: 1; transform: translateY(0) scale(1); }
  75%  { opacity: 1; }
  100% { opacity: 0; }
}
@keyframes complete-in {
  from { opacity: 0; transform: scale(0.96); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
`;

// ─── Helpers ──────────────────────────────────────────────────────────────────
function fmtTime(s: number) {
  const safe = Math.max(0, Math.round(s));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
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

type SpeakState = "connecting" | "idle" | "ai-speaking" | "user-speaking";

// ─── State pill ───────────────────────────────────────────────────────────────
function StatePill({ state, isConnected }: { state: SpeakState; isConnected: boolean }) {
  const cfg: Record<SpeakState, { label: string; color: string }> = {
    connecting:      { label: "Connecting…",  color: G.muted  },
    idle:            { label: "Listening",     color: G.muted  },
    "ai-speaking":   { label: "AI Speaking",   color: G.accent },
    "user-speaking": { label: "Your Turn",     color: "#34d399" },
  };
  const { label, color } = cfg[state];
  return (
    <div key={state} style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      background: `${color}14`, border: `1px solid ${color}44`,
      padding: "3px 10px", borderRadius: 20,
      fontFamily: G.mono, fontSize: "0.6rem", color,
      letterSpacing: "0.1em", textTransform: "uppercase",
      animation: "status-enter 0.2s ease",
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, boxShadow: `0 0 5px ${color}` }} />
      {label}
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
  const [sessionStarted, setSessionStarted]   = useState(false);
  const [question, setQuestion]               = useState(config.first_question);
  // Always start at Q1 — API returns question_index:0 as a placeholder
  const [questionIndex, setQuestionIndex]     = useState(1);
  const [questionKey, setQuestionKey]         = useState(0);
  const [aiMsg, setAiMsg]                     = useState("");
  const [confidence, setConfidence]           = useState(68);
  const [emotion, setEmotion]                 = useState("neutral");
  const [fillers, setFillers]                 = useState(0);
  const [elapsed, setElapsed]                 = useState(0);
  const [userTranscript, setUserTranscript]   = useState("");
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [speakState, setSpeakState]           = useState<SpeakState>("connecting");
  const [questionScores, setQuestionScores]   = useState<Record<number, number>>({});
  // Simple 1-second interval counters — no ref arithmetic that can overflow
  const [aiSpeakSec, setAiSpeakSec]           = useState(0);
  const [userSpeakSec, setUserSpeakSec]       = useState(0);
  // Flash when a new question arrives
  const [isNewQuestion, setIsNewQuestion]     = useState(false);
  // Interview completion overlay (shows before navigating to report)
  const [interviewEnded, setInterviewEnded]   = useState(false);

  const videoRef               = useRef<HTMLVideoElement>(null);
  const screenVideoRef         = useRef<HTMLVideoElement>(null);
  const screenStreamRef        = useRef<MediaStream | null>(null);
  const screenFrameIntervalRef = useRef<number | null>(null);
  const waveCanvasRef          = useRef<HTMLCanvasElement>(null);
  const isScreenSharingRef     = useRef(false);
  const toggleScreenShareRef   = useRef<() => Promise<void>>(() => Promise.resolve());
  const transcriptEndRef       = useRef<HTMLDivElement>(null);

  // ── Transcript ─────────────────────────────────────────────────────────────
  const onTranscriptUpdate = useCallback((text: string) => {
    setUserTranscript(prev => {
      if (prev.endsWith(text)) return prev;
      return `${prev} ${text}`.trim();
    });
    const re = /\b(um|uh|like|basically|actually|literally|you know|i mean)\b/gi;
    const m = text.match(re);
    if (m) setFillers(p => p + m.length);
  }, []);

  // ── Hook ───────────────────────────────────────────────────────────────────
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
      if (data.is_finished || data.type === "interview_end") handleInterviewComplete();
    },
    onScreenShareRequest: () => { if (!isScreenSharingRef.current) toggleScreenShareRef.current(); },
    onScreenShareStop:    () => { if (isScreenSharingRef.current)  toggleScreenShareRef.current(); },
    onAgentEvent: (data) => {
      // Backend sends question_change when record_score is called — update panel immediately
      if (data.type === "question_change") {
        setQuestionIndex(data.question_number);
        setQuestion(data.question_text);
        setQuestionKey(k => k + 1);
      }
      if (data.type === "tool_call") {
        const { name, args } = data.payload ?? {};
        if (name === "sync_interview_state") {
          setQuestionIndex(args.question_index + 1);
          setQuestion(args.question_text);
          setQuestionKey(k => k + 1);
        }
      }
      // score_update: backend sends { type, data: { question_number, score, ... } }
      if (data.type === "score_update") {
        const entry = data.data ?? {};
        const { question_number, score } = entry;
        if (question_number != null && score != null) {
          // score is 0-10; display as 0-100%
          setQuestionScores(prev => ({ ...prev, [question_number - 1]: Math.round(score * 10) }));
        }
      }
    },
    onError: (err) => console.error("Gemini Live Error:", err),
  });

  const isUserSpeaking = audioLevel > 10 && !isAiSpeaking;

  // ── Speak state ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isConnected) setSpeakState("connecting");
    else if (isAiSpeaking) setSpeakState("ai-speaking");
    else if (isUserSpeaking) setSpeakState("user-speaking");
    else setSpeakState("idle");
  }, [isConnected, isAiSpeaking, isUserSpeaking]);

  // ── Speaking time — simple per-second counters, no ref arithmetic ──────────
  useEffect(() => {
    if (!isConnected) return;
    const id = setInterval(() => {
      if (isAiSpeaking) setAiSpeakSec(s => s + 1);
      else if (isUserSpeaking) setUserSpeakSec(s => s + 1);
    }, 1000);
    return () => clearInterval(id);
  }, [isConnected, isAiSpeaking, isUserSpeaking]);

  // ── Session timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    const id = setInterval(() => setElapsed(v => v + 1), 1000);
    return () => clearInterval(id);
  }, []);

  // ── New question flash ─────────────────────────────────────────────────────
  useEffect(() => {
    if (questionKey === 0) return; // skip initial mount
    setIsNewQuestion(true);
    const t = setTimeout(() => setIsNewQuestion(false), 2500);
    return () => clearTimeout(t);
  }, [questionKey]);

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
            sendMessage({ type: "screen_frame", data: canvas.toDataURL("image/jpeg", 0.6).split(",")[1], mimeType: "image/jpeg" });
          }
        }, 1000);
        isScreenSharingRef.current = true;
        setIsScreenSharing(true);
      } catch {}
    }
  }, [isScreenSharing, sendMessage]);

  useEffect(() => { toggleScreenShareRef.current = toggleScreenShare; }, [toggleScreenShare]);

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
    const bars = 44;
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bw = canvas.width / bars - 1.5;
      const color = isAiSpeaking ? G.accent : isUserSpeaking ? "#34d399" : `${G.border}cc`;
      ctx.globalAlpha = 0.9;
      for (let i = 0; i < bars; i++) {
        const h = isAiSpeaking
          ? Math.max(3, (Math.random() * 0.65 + 0.35) * (6 + Math.random() * 22))
          : audioLevel > 8
            ? Math.max(3, (Math.random() * 0.5 + 0.5) * (audioLevel / 5.5) + 3)
            : Math.abs(Math.sin(Date.now() / 500 + i * 0.9)) * 3 + 2;
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

  // Called by Quit button — immediate exit
  const handleQuit = async () => {
    if (screenFrameIntervalRef.current) { clearInterval(screenFrameIntervalRef.current); screenFrameIntervalRef.current = null; }
    stopSession();
    try { await endSession(config.session_id); } finally { onEnd(); }
  };

  // Called when AI signals interview_end — show completion overlay first
  const handleInterviewComplete = () => {
    if (interviewEnded) return; // guard against double-fire
    setInterviewEnded(true);
    if (screenFrameIntervalRef.current) { clearInterval(screenFrameIntervalRef.current); screenFrameIntervalRef.current = null; }
    stopSession();
    setTimeout(async () => {
      try { await endSession(config.session_id); } finally { onEnd(); }
    }, 3500);
  };

  // Back-compat alias so stopSessionRef still works
  const handleEnd = handleQuit;

  // ── Orb appearance ─────────────────────────────────────────────────────────
  const orbColor = isAiSpeaking ? G.accent : isUserSpeaking ? "#34d399" : G.border;
  const orbGlow  = isAiSpeaking ? `0 0 28px ${G.accent}55, 0 0 56px ${G.accent}22` : isUserSpeaking ? `0 0 18px #34d39940` : "none";
  const rings    = isAiSpeaking ? [0, 0.5, 1.0] : isUserSpeaking ? [0, 0.6] : [];

  return (
    <>
      <style>{ANIM_CSS}</style>

      {/* Full-viewport container, no scroll */}
      <div style={{
        height: "100vh", overflow: "hidden",
        background: G.bg, fontFamily: G.font,
        display: "flex", flexDirection: "column",
      }}>

        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <div style={{
          flexShrink: 0, height: 48,
          background: G.surface, borderBottom: `1px solid ${G.border}`,
          display: "flex", alignItems: "center", padding: "0 1.2rem", gap: "1rem",
        }}>
          <span style={{ fontWeight: 800, fontSize: "0.95rem", color: G.text, letterSpacing: "-0.02em", whiteSpace: "nowrap" }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </span>
          <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.accent, border: `1px solid ${G.accent}44`, padding: "2px 6px", letterSpacing: "0.1em" }}>
            ● LIVE
          </div>

          {/* Compact progress dots */}
          <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
            {Array.from({ length: config.total_questions }).map((_, i) => {
              const qi = i + 1; const done = qi < questionIndex; const cur = qi === questionIndex; const sc = questionScores[i];
              return (
                <div key={i} style={{
                  width: cur ? 10 : 7, height: cur ? 10 : 7, borderRadius: "50%",
                  background: done ? (sc != null ? scoreColor(sc) : G.accent) : cur ? G.accent2 : G.border,
                  boxShadow: cur ? `0 0 7px ${G.accent2}` : "none",
                  transition: "all 0.3s", flexShrink: 0,
                }} title={sc != null ? `Q${qi}: ${sc}%` : `Q${qi}`} />
              );
            })}
            <span style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, marginLeft: 2 }}>
              Q{questionIndex}/{config.total_questions}
            </span>
          </div>

          <div style={{ flex: 1 }} />

          <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: G.accent2, border: `1px solid ${G.accent2}44`, padding: "2px 7px", textTransform: "uppercase" }}>
            {config.mode}
          </div>
          <div style={{ fontFamily: G.mono, fontSize: "0.85rem", fontWeight: 600, color: elapsed > 2400 ? G.accent3 : G.text, letterSpacing: "0.05em" }}>
            {fmtTime(elapsed)}
          </div>
          <button onClick={handleQuit} style={{
            padding: "3px 10px", background: "transparent",
            border: `1px solid ${G.border}`, color: G.accent3,
            fontFamily: G.font, fontSize: "0.72rem", cursor: "pointer", fontWeight: 600,
          }}>
            Quit
          </button>
        </div>

        {/* ── BODY 3-COLUMN ───────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "230px 1fr 250px", overflow: "hidden", minHeight: 0 }}>

          {/* ── LEFT ──────────────────────────────────────────────────────── */}
          <div style={{
            background: G.surface, borderRight: `1px solid ${G.border}`,
            display: "flex", flexDirection: "column", padding: "0.9rem", gap: "0.8rem",
            overflow: "hidden",
          }}>
            {/* Profile */}
            <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.7rem", flexShrink: 0 }}>
              <div style={{ fontSize: "0.82rem", color: G.text, fontWeight: 600 }}>{config.name || "Candidate"}</div>
              <div style={{ fontSize: "0.68rem", color: G.muted, marginTop: 2 }}>{config.role}</div>
              <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: isConnected ? G.accent : G.accent3, marginTop: 5 }}>
                {isConnected ? "● Connected" : "○ Disconnected"}
                {error && <span style={{ color: G.accent3, marginLeft: 6 }}>⚠ {error}</span>}
              </div>
            </div>

            {/* Question tracker */}
            <div style={{ flexShrink: 0 }}>
              <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 6 }}>
                Questions
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
                {Array.from({ length: config.total_questions }).map((_, i) => {
                  const qi = i + 1; const done = qi < questionIndex; const cur = qi === questionIndex; const sc = questionScores[i];
                  return (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 7,
                      padding: "4px 7px",
                      background: cur ? `${G.accent2}0e` : "transparent",
                      border: `1px solid ${cur ? G.accent2 + "44" : G.border}`,
                      animation: cur && isNewQuestion ? "q-new-flash 2.5s ease" : "none",
                    }}>
                      <div style={{
                        width: 16, height: 16, borderRadius: "50%", flexShrink: 0,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        background: done ? `${scoreColor(sc ?? 70)}18` : cur ? `${G.accent2}18` : G.surface2,
                        border: `1px solid ${done ? scoreColor(sc ?? 70) : cur ? G.accent2 : G.border}`,
                        fontFamily: G.mono, fontSize: "0.5rem",
                        color: done ? scoreColor(sc ?? 70) : cur ? G.accent2 : G.muted, fontWeight: 700,
                      }}>
                        {done ? "✓" : qi}
                      </div>
                      <span style={{ fontSize: "0.68rem", color: cur ? G.text : G.muted, fontWeight: cur ? 600 : 400, flex: 1 }}>
                        Q{qi}
                      </span>
                      {sc != null && (
                        <span style={{ fontFamily: G.mono, fontSize: "0.58rem", color: scoreColor(sc), fontWeight: 700 }}>
                          {sc}%
                        </span>
                      )}
                      {cur && sc == null && (
                        <span style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.accent2 }}>now</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Transcript */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
              <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 5, flexShrink: 0 }}>
                Your Transcript
              </div>
              <div style={{
                flex: 1, background: G.surface2, border: `1px solid ${G.border}`,
                padding: "0.7rem", fontSize: "0.74rem", color: G.text,
                lineHeight: 1.6, overflowY: "auto", minHeight: 0,
              }}>
                {userTranscript || <span style={{ color: G.muted }}>Waiting for your voice…</span>}
                <div ref={transcriptEndRef} />
              </div>
            </div>
          </div>

          {/* ── CENTER ────────────────────────────────────────────────────── */}
          <div style={{
            display: "flex", flexDirection: "column",
            padding: "1.2rem 2rem 1rem", gap: "1rem",
            overflow: "hidden",
          }}>

            {/* Question — clean area, no background animation */}
            <div style={{ flexShrink: 0, textAlign: "center" }}>
              {/* "NEW QUESTION" badge — flashes in for 2.5s on each transition */}
              {isNewQuestion && (
                <div key={`badge-${questionKey}`} style={{
                  display: "inline-flex", alignItems: "center", gap: 5,
                  background: `${G.accent}18`, border: `1px solid ${G.accent}55`,
                  padding: "2px 10px", borderRadius: 12, marginBottom: "0.45rem",
                  fontFamily: G.mono, fontSize: "0.53rem", color: G.accent,
                  letterSpacing: "0.18em", textTransform: "uppercase",
                  animation: "badge-pop 2.5s ease forwards",
                }}>
                  <span style={{ width: 4, height: 4, borderRadius: "50%", background: G.accent, display: "inline-block" }} />
                  New Question
                </div>
              )}
              <div style={{
                fontFamily: G.mono, fontSize: "0.58rem", color: isNewQuestion ? G.accent : G.muted,
                letterSpacing: "0.25em", textTransform: "uppercase", marginBottom: "0.6rem",
                transition: "color 0.4s",
              }}>
                {isNewQuestion ? `Question ${questionIndex} of ${config.total_questions}` : "Current Question"}
              </div>
              <div
                key={questionKey}
                style={{
                  fontSize: "clamp(1.15rem, 1.9vw, 1.9rem)", fontWeight: 700,
                  color: G.text, lineHeight: 1.3, letterSpacing: "-0.02em",
                  maxWidth: 620, margin: "0 auto",
                  animation: "q-enter 0.35s ease",
                  // Clamp to 4 lines so long questions don't push the orb off screen
                  display: "-webkit-box",
                  WebkitLineClamp: 4,
                  WebkitBoxOrient: "vertical",
                  overflow: "hidden",
                }}
              >
                {question || "Introduce yourself to begin."}
              </div>
            </div>

            {/* Thin divider */}
            <div style={{ height: 1, background: G.border, flexShrink: 0 }} />

            {/* Orb — self-contained, rings don't bleed outside */}
            <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.7rem" }}>
              {/* Container clips the rings */}
              <div style={{ position: "relative", width: 130, height: 130, overflow: "visible" }}>
                {/* Expanding rings — anchored to center of orb, won't overlap question */}
                {rings.map((delay, i) => (
                  <div key={i} style={{
                    position: "absolute",
                    left: "50%", top: "50%",
                    width: 130, height: 130,
                    marginLeft: -65, marginTop: -65,
                    borderRadius: "50%",
                    border: `1px solid ${orbColor}`,
                    animation: `ring-out 1.8s ease-out ${delay}s infinite`,
                    pointerEvents: "none",
                  }} />
                ))}
                {/* Orb body */}
                <div style={{
                  position: "absolute", inset: 0, borderRadius: "50%",
                  background: isAiSpeaking
                    ? `radial-gradient(circle at 38% 35%, ${G.accent}1a, ${G.bg})`
                    : isUserSpeaking
                      ? `radial-gradient(circle at 38% 35%, #34d3991a, ${G.bg})`
                      : `radial-gradient(circle at 38% 35%, ${G.surface}, ${G.bg})`,
                  border: `2px solid ${orbColor}`,
                  boxShadow: orbGlow,
                  animation: isConnected && !isAiSpeaking && !isUserSpeaking ? "orb-idle 3s ease-in-out infinite" : "none",
                  transition: "border-color 0.3s, box-shadow 0.4s",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {/* Inner bars */}
                  <div style={{ display: "flex", gap: 3, alignItems: "center", height: 28 }}>
                    {[0.45, 0.7, 1, 0.8, 0.55, 0.7, 0.45].map((sc, i) => (
                      <div key={i} style={{
                        width: 3, borderRadius: 2,
                        background: orbColor,
                        opacity: isConnected ? 0.85 : 0.25,
                        height: `${sc * 100}%`,
                        animation: (isAiSpeaking || isUserSpeaking)
                          ? `bar-dance ${0.5 + i * 0.07}s ease-in-out ${i * 0.06}s infinite alternate`
                          : "none",
                        transition: "background 0.3s",
                      }} />
                    ))}
                  </div>
                </div>
              </div>

              {/* State pill — right under orb */}
              <StatePill state={speakState} isConnected={isConnected} />
            </div>

            {/* Waveform — compact, clearly labelled */}
            <div style={{
              background: G.surface2, border: `1px solid ${G.border}`,
              padding: "0.5rem 0.8rem", flexShrink: 0,
            }}>
              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                fontFamily: G.mono, fontSize: "0.52rem", color: G.muted,
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5,
              }}>
                <span>Audio</span>
                <span style={{ color: isAiSpeaking ? G.accent : isUserSpeaking ? "#34d399" : G.muted }}>
                  {isAiSpeaking ? "AI output" : isUserSpeaking ? "Mic active" : "Silence"}
                </span>
              </div>
              <canvas ref={waveCanvasRef} width={600} height={36} style={{ width: "100%", height: 36, display: "block" }} />
            </div>

            {/* AI message — bottom of center, key info for user */}
            <div style={{
              flex: 1, background: G.surface2, border: `1px solid ${G.border}`,
              padding: "0.7rem 0.9rem", minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column",
            }}>
              <div style={{ fontFamily: G.mono, fontSize: "0.52rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 5, flexShrink: 0 }}>
                Aria's Message
              </div>
              <div style={{
                fontSize: "0.76rem", color: G.text, lineHeight: 1.55,
                borderLeft: `2px solid ${G.accent}`, paddingLeft: "0.7rem",
                flex: 1, overflowY: "auto",
              }}>
                {aiMsg || <span style={{ color: G.muted }}>Waiting for Aria…</span>}
              </div>
            </div>
          </div>

          {/* ── RIGHT ─────────────────────────────────────────────────────── */}
          <div style={{
            background: G.surface, borderLeft: `1px solid ${G.border}`,
            display: "flex", flexDirection: "column", padding: "0.9rem", gap: "0.8rem",
            overflow: "hidden",
          }}>
            {/* Camera */}
            <div style={{ flexShrink: 0 }}>
              <div style={{
                display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6,
              }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.52rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.08em" }}>Vision</div>
                <button onClick={toggleScreenShare} style={{
                  background: isScreenSharing ? G.accent2 : "transparent",
                  border: `1px solid ${isScreenSharing ? G.accent2 : G.border}`,
                  color: isScreenSharing ? "#000" : G.muted,
                  fontSize: "0.52rem", padding: "2px 6px", cursor: "pointer",
                  textTransform: "uppercase", fontWeight: 700,
                }}>
                  {isScreenSharing ? "Stop" : "Screen"}
                </button>
              </div>
              <div style={{
                background: "#000", border: `2px solid ${orbColor}`, overflow: "hidden",
                position: "relative", transition: "border-color 0.3s",
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
                    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: G.muted, fontSize: "0.7rem" }}>
                      Audio Only
                    </div>
                  )}
                  <div style={{
                    position: "absolute", bottom: 6, left: 6,
                    background: "rgba(0,0,0,0.65)", padding: "1px 7px", borderRadius: 8,
                    border: `1px solid ${emotionColor(emotion)}`,
                  }}>
                    <span style={{ color: emotionColor(emotion), fontSize: "0.55rem", fontWeight: 700, textTransform: "uppercase" }}>
                      {emotion}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Confidence */}
            <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.7rem", flexShrink: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase" }}>Confidence</span>
                <span style={{ fontSize: "1rem", fontWeight: 800, color: confidence > 65 ? G.accent : G.accent2 }}>{Math.round(confidence)}%</span>
              </div>
              <div style={{ height: 5, background: G.bg, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${confidence}%`, background: confidence > 65 ? G.accent : G.accent2, transition: "width 0.8s ease" }} />
              </div>
              <div style={{ fontSize: "0.62rem", color: G.muted, marginTop: 5, textAlign: "center" }}>
                {confidence > 75 ? "Excellent composure" : confidence > 50 ? "Steady — keep going" : "Take a breath"}
              </div>
            </div>

            {/* Stats 2×2 grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, flexShrink: 0 }}>
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.6rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.muted, textTransform: "uppercase" }}>Fillers</div>
                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: fillers > 5 ? G.accent3 : G.text, marginTop: 2 }}>{fillers}</div>
              </div>
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.6rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.muted, textTransform: "uppercase" }}>Words</div>
                <div style={{ fontSize: "1.3rem", fontWeight: 700, color: G.text, marginTop: 2 }}>
                  {userTranscript.split(/\s+/).filter(Boolean).length}
                </div>
              </div>
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.6rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.muted, textTransform: "uppercase" }}>You</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#34d399", marginTop: 2, fontFamily: G.mono }}>
                  {fmtTime(userSpeakSec)}
                </div>
              </div>
              <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.6rem" }}>
                <div style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.muted, textTransform: "uppercase" }}>AI</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: G.accent, marginTop: 2, fontFamily: G.mono }}>
                  {fmtTime(aiSpeakSec)}
                </div>
              </div>
            </div>

            {/* Spacer + score summary */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 4 }}>
              {Object.entries(questionScores).length > 0 && (
                <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "0.7rem" }}>
                  <div style={{ fontFamily: G.mono, fontSize: "0.5rem", color: G.muted, textTransform: "uppercase", marginBottom: 6 }}>Scores</div>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    {Object.entries(questionScores).map(([qi, sc]) => (
                      <div key={qi} style={{
                        fontFamily: G.mono, fontSize: "0.6rem",
                        color: scoreColor(sc), fontWeight: 700,
                        background: `${scoreColor(sc)}18`, border: `1px solid ${scoreColor(sc)}44`,
                        padding: "2px 7px", borderRadius: 3,
                      }}>
                        Q{parseInt(qi) + 1}: {sc}%
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ── INTERVIEW COMPLETE OVERLAY ──────────────────────────────────────── */}
      {interviewEnded && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(5,5,8,0.96)",
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: "1.4rem",
          backdropFilter: "blur(12px)",
          animation: "complete-in 0.5s ease",
        }}>
          {/* Circle with checkmark */}
          <div style={{
            width: 80, height: 80, borderRadius: "50%",
            border: `2px solid ${G.accent}`,
            background: `radial-gradient(circle at 38% 35%, ${G.accent}18, transparent)`,
            boxShadow: `0 0 40px ${G.accent}33`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <polyline points="6,16 13,23 26,9" stroke={G.accent} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>

          <div style={{ fontWeight: 800, fontSize: "2rem", color: G.text, letterSpacing: "-0.03em" }}>
            Interview <span style={{ color: G.accent }}>Complete</span>
          </div>

          <p style={{ color: G.muted, fontSize: "0.9rem", textAlign: "center", maxWidth: 360, lineHeight: 1.6, margin: 0 }}>
            Great session. Compiling your performance report and scorecard…
          </p>

          {/* Spinner dots */}
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {[0, 0.3, 0.6].map((delay, i) => (
              <div key={i} style={{
                width: 6, height: 6, borderRadius: "50%", background: G.accent,
                animation: `bar-dance 1s ease-in-out ${delay}s infinite alternate`,
                opacity: 0.7,
              }} />
            ))}
          </div>
        </div>
      )}

      {!sessionStarted && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(5,5,8,0.93)",
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: "1.5rem",
          backdropFilter: "blur(6px)",
        }}>
          {/* Mini orb preview */}
          <div style={{
            width: 72, height: 72, borderRadius: "50%",
            border: `2px solid ${G.accent}`,
            background: `radial-gradient(circle at 38% 35%, ${G.accent}18, ${G.bg})`,
            boxShadow: `0 0 28px ${G.accent}33`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ display: "flex", gap: 2.5, alignItems: "center", height: 18 }}>
              {[0.4, 0.7, 1, 0.8, 0.55, 0.7, 0.45].map((s, i) => (
                <div key={i} style={{ width: 2.5, borderRadius: 2, background: G.accent, height: `${s * 100}%`, opacity: 0.8 }} />
              ))}
            </div>
          </div>

          <div style={{ fontWeight: 800, fontSize: "1.8rem", color: G.text, letterSpacing: "-0.03em" }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </div>

          <div style={{ textAlign: "center", maxWidth: 360, padding: "0 1rem" }}>
            <p style={{ color: G.muted, fontSize: "0.85rem", margin: 0 }}>
              Aria will guide you through {config.total_questions} questions. Speak clearly and take your time.
            </p>
          </div>

          <button
            onClick={() => { setSessionStarted(true); startSession(); }}
            style={{
              padding: "0.8rem 2.8rem", background: G.accent, border: "none",
              color: "#000", fontFamily: G.font, fontSize: "0.9rem",
              fontWeight: 700, cursor: "pointer", letterSpacing: "-0.01em",
            }}
          >
            Begin Interview →
          </button>

          <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, letterSpacing: "0.05em" }}>
            {config.name} · {config.role} · {config.mode} mode
          </div>
        </div>
      )}
    </>
  );
}
