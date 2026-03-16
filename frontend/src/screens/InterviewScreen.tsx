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
@keyframes ai-card-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes blink {
  0%,100% { opacity: 1; }
  50%     { opacity: 0; }
}
@keyframes dot-pulse {
  0%,100% { opacity: 1; transform: scale(1); }
  50%     { opacity: 0.4; transform: scale(0.8); }
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

// ─── AI Speech Card ───────────────────────────────────────────────────────────
function AiSpeechCard({ text, isActive }: { text: string; isActive: boolean }) {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, overflow: "hidden" }}>
      {/* Header row */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "0.55rem 0.9rem 0.3rem", flexShrink: 0,
      }}>
        <span style={{ fontFamily: G.mono, fontSize: "0.52rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.18em" }}>
          Aria
        </span>
        <span style={{
          width: 6, height: 6, borderRadius: "50%", display: "inline-block",
          background: isActive ? G.accent : G.muted,
          boxShadow: isActive ? `0 0 6px ${G.accent}` : "none",
          animation: isActive ? "dot-pulse 1.2s ease-in-out infinite" : "none",
          transition: "background 0.3s, box-shadow 0.3s",
        }} />
      </div>
      {/* Body */}
      <div style={{
        flex: 1, overflowY: "auto", padding: "0.3rem 0.9rem 0.8rem",
        marginLeft: "0.5rem",
        borderLeft: isActive ? `2px solid ${G.accent}` : `2px solid ${G.border}`,
        transition: "border-left-color 0.3s",
        animation: "ai-card-in 0.3s ease",
      }}>
        {text ? (
          <p style={{ fontSize: "0.88rem", lineHeight: 1.7, color: G.text, margin: 0 }}>
            {text}
            {isActive && (
              <span style={{
                display: "inline-block", width: 2, height: "0.9em",
                background: G.accent, marginLeft: 3, verticalAlign: "text-bottom",
                animation: "blink 1.1s step-end infinite",
              }} />
            )}
          </p>
        ) : (
          <span style={{ fontSize: "0.78rem", color: G.muted, fontStyle: "italic" }}>
            Aria will speak here…
          </span>
        )}
      </div>
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
  // Key that increments each time AI starts speaking — triggers card entrance animation
  const [aiMsgKey, setAiMsgKey]               = useState(0);

  const videoRef               = useRef<HTMLVideoElement>(null);
  const screenVideoRef         = useRef<HTMLVideoElement>(null);
  const screenStreamRef        = useRef<MediaStream | null>(null);
  const screenFrameIntervalRef = useRef<number | null>(null);
  const isScreenSharingRef     = useRef(false);
  // Only send screen frames to AI after request_screen_share tool fires.
  // Prevents arbitrary desktop content from being processed as an answer.
  const screenAIEnabledRef     = useRef(false);
  const toggleScreenShareRef   = useRef<() => Promise<void>>(() => Promise.resolve());

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
    onScreenShareRequest: () => {
      screenAIEnabledRef.current = true;
      if (!isScreenSharingRef.current) toggleScreenShareRef.current();
      // Tell AI the screen is now being shared for context
      sendMessage({ type: "text", content: "[Candidate is now sharing their screen. You can see their code editor.]" });
    },
    onScreenShareStop: () => {
      screenAIEnabledRef.current = false;
      if (isScreenSharingRef.current) toggleScreenShareRef.current();
    },
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

  // ── AI speech card key — re-triggers entrance animation on each new AI turn
  useEffect(() => {
    if (isAiSpeaking) setAiMsgKey(k => k + 1);
  }, [isAiSpeaking]);

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
          // Only send frames to AI after request_screen_share tool fires.
          // This prevents the AI from processing the desktop as an answer unprompted.
          if (ctx && videoEl && videoEl.readyState >= 2 && screenAIEnabledRef.current) {
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

        {/* ── BODY 2-COLUMN ───────────────────────────────────────────────── */}
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 220px", overflow: "hidden", minHeight: 0 }}>

          {/* ── CENTER ────────────────────────────────────────────────────── */}
          <div style={{
            display: "flex", flexDirection: "column",
            padding: "1.2rem 2.4rem 1rem", gap: "1rem",
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
                  fontSize: "clamp(1.2rem, 2vw, 1.75rem)", fontWeight: 700,
                  color: G.text, lineHeight: 1.35, letterSpacing: "-0.02em",
                  maxWidth: 720, margin: "0 auto",
                  animation: "q-enter 0.35s ease",
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

            {/* AI speech card */}
            <div key={aiMsgKey} style={{
              flex: 1, background: G.surface2, border: `1px solid ${G.border}`,
              minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column",
            }}>
              <AiSpeechCard text={aiMsg} isActive={isAiSpeaking} />
            </div>
          </div>

          {/* ── RIGHT ─────────────────────────────────────────────────────── */}
          <div style={{
            background: G.surface, borderLeft: `1px solid ${G.border}`,
            display: "flex", flexDirection: "column", padding: "0.9rem", gap: "0.6rem",
            overflow: "hidden",
          }}>
            {/* Screen share toggle + camera */}
            <div style={{ flexShrink: 0 }}>
              <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
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
              {/* Compact confidence + emotion line */}
              <div style={{
                fontFamily: G.mono, fontSize: "0.55rem", color: G.muted,
                marginTop: 5, textAlign: "center",
              }}>
                {Math.round(confidence)}% · {emotion}
              </div>
            </div>

            {/* Spacer */}
            <div style={{ flex: 1 }} />
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
