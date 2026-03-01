import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  ParticipantView,
  useCall,
  useCallStateHooks,
} from "@stream-io/video-react-sdk";
import { endSession, submitAnswer, getEventSource } from "../api";
import { G } from "../theme";
import { LiveSessionConfig } from "../types";

type RecognitionCtor = new () => {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: {
    resultIndex: number;
    results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal?: boolean }>;
  }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

function getRecognitionCtor(): RecognitionCtor | null {
  const w = window as Window & {
    SpeechRecognition?: RecognitionCtor;
    webkitSpeechRecognition?: RecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

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

function StreamParticipantStage() {
  const call = useCall();
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants();
  const [joinState, setJoinState] = useState<"joining" | "joined" | "failed">("joining");

  useEffect(() => {
    if (!call) {
      return;
    }

    setJoinState("joining");
    call.join({ create: true })
      .then(async () => {
        setJoinState("joined");
        // Enable media independently so one failure doesn't block the other
        try {
          await call.camera.enable();
        } catch (e) {
          console.warn("Camera failed to enable:", e);
        }
        try {
          await call.microphone.enable();
        } catch (e) {
          console.warn("Microphone failed to enable:", e);
        }
      })
      .catch((err) => {
        console.error("Failed to join call:", err);
        setJoinState("failed");
      });

    return () => {
      call.leave().catch(() => undefined);
    };
  }, [call]);

  if (joinState === "failed") {
    return (
      <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", background: "linear-gradient(135deg, #0d0d1a 0%, #111126 100%)" }}>
        <p style={{ color: G.accent3, fontSize: "0.85rem" }}>Failed to join Stream call. Continue with text mode.</p>
      </div>
    );
  }

  if (participants.length === 0) {
    return (
      <div style={{ width: "100%", height: "100%", display: "grid", placeItems: "center", background: "linear-gradient(135deg, #0d0d1a 0%, #111126 100%)" }}>
        <p style={{ color: G.muted, fontSize: "0.82rem" }}>
          {joinState === "joining" ? "Joining Stream call..." : "Camera ready. Waiting for participant feed."}
        </p>
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <ParticipantView participant={participants[0]} />
      <div style={{
        position: "absolute",
        top: 12,
        right: 12,
        padding: "4px 10px",
        background: "rgba(0, 0, 0, 0.4)",
        backdropFilter: "blur(4px)",
        borderRadius: "20px",
        border: `1px solid ${G.accent}44`,
        display: "flex",
        alignItems: "center",
        gap: 6,
        zIndex: 10
      }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: G.accent, boxShadow: `0 0 8px ${G.accent}` }} />
        <span style={{ color: "#fff", fontSize: "0.65rem", fontWeight: 600, letterSpacing: "0.03em", textTransform: "uppercase" }}>
          AI Observing
        </span>
      </div>
    </div>
  );
}

export function InterviewScreen({
  config,
  onEnd,
  streamEnabled,
}: {
  config: LiveSessionConfig;
  onEnd: () => void;
  streamEnabled: boolean;
}) {
  const [question, setQuestion] = useState(config.first_question);
  const [questionIndex, setQuestionIndex] = useState(config.question_index);
  const [transcript, setTranscript] = useState("");
  const [draft, setDraft] = useState("");
  const [aiMsg, setAiMsg] = useState("Let's begin. Give me your best answer and think out loud.");
  const [confidence, setConfidence] = useState(68);
  const [emotion, setEmotion] = useState("neutral");
  const [fillers, setFillers] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [micSupported, setMicSupported] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState(false);
  const [livePartial, setLivePartial] = useState("");
  const [micError, setMicError] = useState<string | null>(null);
  const [recognitionReady, setRecognitionReady] = useState(false);
  const recognitionRef = useRef<InstanceType<RecognitionCtor> | null>(null);
  const shouldListenRef = useRef(false);
  const autoMicStartedRef = useRef(false);
  const introAnnouncedRef = useRef(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const timer = setInterval(() => setElapsed((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    // If stream is enabled, we use Stream WebRTC for audio capture.
    // The browser SpeechRecognition API will cause a conflict and throw an error.
    if (streamEnabled) {
      setMicSupported(false);
      setRecognitionReady(false);
      return;
    }

    const Recognition = getRecognitionCtor();
    if (!Recognition) {
      setMicSupported(false);
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      let interim = "";
      let finalText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const current = event.results[i];
        const text = current[0]?.transcript?.trim();
        if (!text) {
          continue;
        }
        if (current.isFinal) {
          finalText += ` ${text}`;
        } else {
          interim += ` ${text}`;
        }
      }

      if (finalText.trim()) {
        setDraft((prev) => `${prev} ${finalText}`.replace(/\s+/g, " ").trim());
      }
      setLivePartial(interim.trim());
    };

    recognition.onerror = (event) => {
      if (event.error && event.error !== "no-speech") {
        setMicError(`Mic error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      if (shouldListenRef.current) {
        try {
          recognition.start();
          return;
        } catch (_err) {
          setMicError("Unable to restart microphone capture.");
        }
      }
      setIsListening(false);
      setLivePartial("");
    };

    recognitionRef.current = recognition;
    setRecognitionReady(true);

    return () => {
      shouldListenRef.current = false;
      recognition.abort();
      recognitionRef.current = null;
      setRecognitionReady(false);
    };
  }, [streamEnabled]);

  useEffect(() => {
    let es: EventSource | null = null;
    let mounted = true;

    const connect = async () => {
      try {
        es = await getEventSource(config.session_id);
        
        es.addEventListener("transcript", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [transcript]:", data);
          if (data.text) {
            setDraft((prev) => `${prev} ${data.text}`.replace(/\s+/g, " ").trim());
            setLivePartial(""); // Clear interim if we get a server-side final
          }
        });

        es.addEventListener("agent_transcript", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [agent_transcript]:", data);
          if (data.text) {
            setAiMsg(data.text);
            setIsAiSpeaking(true);
          }
        });

        es.addEventListener("agent_message", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [agent_message]:", data);
          if (data.text) {
            setAiMsg(data.text);
            setIsAiSpeaking(false);
            
            // Sync question state if the agent is asking a new question
            // We now broadcast explicit "next_question" and "question_scored" events
            // but keep this for standard agent messages if they have question index
            if (data.question_index !== undefined) {
                setQuestionIndex(data.question_index);
            }
          }
        });

        es.addEventListener("next_question", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [next_question]:", data);
          if (data.question) {
            setQuestion(data.question);
            setQuestionIndex(data.question_index);
          }
        });

        es.addEventListener("question_scored", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [question_scored]:", data);
          // Optional: Display score briefly if desired
        });

        es.addEventListener("interrupt", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          console.log("SSE [interrupt]:", data);
          setAiMsg(data.spoken);
          setIsAiSpeaking(false);
        });

        es.addEventListener("interview_complete", (e: any) => {
          if (!mounted) return;
          console.log("SSE [interview_complete]:", e.data);
          onEnd();
        });

        es.addEventListener("vision", (e: any) => {
          if (!mounted) return;
          const data = JSON.parse(e.data);
          if (data.confidence !== undefined) setConfidence(data.confidence);
          if (data.emotion) setEmotion(data.emotion);
        });

        es.onerror = () => {
          if (mounted) {
            console.error("SSE Connection failed. Retrying...");
            es?.close();
            setTimeout(connect, 3000);
          }
        };
      } catch (err) {
        console.error("Failed to connect to event stream:", err);
      }
    };

    connect();

    return () => {
      mounted = false;
      es?.close();
    };
  }, [config.session_id, onEnd]);

  const speakText = useCallback(
    (text: string) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) {
        return;
      }
      const cleanText = text.trim();
      if (!cleanText) {
        return;
      }

      window.speechSynthesis.cancel();
      
      // If stream is enabled, we rely on the agent's native voice via Stream audio track.
      // We only use speechSynthesis as a fallback for the opening line if the agent isn't ready,
      // or if stream is disabled entirely.
      if (streamEnabled && introAnnouncedRef.current) {
        return;
      }

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = config.mode === "strict" ? 0.96 : 1.02;
      utterance.pitch = config.mode === "strict" ? 0.9 : 1.03;
      utterance.onstart = () => setIsAiSpeaking(true);
      utterance.onend = () => setIsAiSpeaking(false);
      utterance.onerror = () => setIsAiSpeaking(false);
      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [config.mode, streamEnabled]
  );

  useEffect(() => {
    if (introAnnouncedRef.current) {
      return;
    }
    introAnnouncedRef.current = true;

    const openingLine =
      config.mode === "strict"
        ? `Welcome. We begin now. Question one: ${question}`
        : `Welcome to your interview session. Let's start with your first question: ${question}`;

    setAiMsg(openingLine);
    speakText(openingLine);
  }, [config.mode, question, speakText]);

  useEffect(() => {
    if (!recognitionReady || !micSupported || !recognitionRef.current || autoMicStartedRef.current) {
      return;
    }

    autoMicStartedRef.current = true;
    shouldListenRef.current = true;
    setMicError(null);
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (_err) {
      shouldListenRef.current = false;
      setIsListening(false);
      setMicError("Auto mic start blocked. Click Start Mic to continue.");
    }
  }, [micSupported, recognitionReady]);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      utteranceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let audioCtx: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let source: MediaStreamAudioSourceNode | null = null;
    let raf = 0;

    const initAudio = async () => {
      // 1. Try to get local audio track from Stream call
      // In a real scenario, we'd use the call's participant track. 
      // For now, let's use the browser's getUserMedia if available, 
      // or just fallback to the visualizer if it's already active.
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => null);
        if (!stream) return;

        audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
      } catch (e) {
        console.warn("Real-time audio visualization failed to init:", e);
      }
    };

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const bars = 38;
      const width = canvas.width / bars - 2;
      
      let dataArray: Uint8Array | null = null;
      if (analyser) {
        dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray as any);
      }

      for (let i = 0; i < bars; i += 1) {
        let pulse = 0;
        if (dataArray) {
          // Map frequency data to bar height
          const idx = Math.floor((i / bars) * dataArray.length);
          pulse = (dataArray[idx] / 255) * 35 + 5;
        } else {
          // Fallback to fake pulse if mic is active but no analyzer
          pulse = isListening || isSubmitting ? Math.random() * 25 + 5 : Math.sin(Date.now() / 200 + i * 0.6) * 3 + 6;
        }
        
        ctx.fillStyle = isListening ? G.accent : G.muted;
        ctx.globalAlpha = 0.75;
        ctx.fillRect(i * (width + 2), (canvas.height - pulse) / 2, width, pulse);
      }
      raf = requestAnimationFrame(draw);
    };

    initAudio().then(() => {
      draw();
    });

    return () => {
      cancelAnimationFrame(raf);
      if (audioCtx) audioCtx.close();
    };
  }, [isListening, isSubmitting]);

  const fmt = (seconds: number) =>
    `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;

  const toggleMic = () => {
    if (!micSupported || !recognitionRef.current) {
      setMicError("Speech recognition is not supported in this browser.");
      return;
    }

    if (isListening) {
      shouldListenRef.current = false;
      recognitionRef.current.stop();
      setIsListening(false);
      setLivePartial("");
      return;
    }

    setMicError(null);
    shouldListenRef.current = true;
    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (_err) {
      setMicError("Unable to start microphone. Check browser mic permissions.");
    }
  };

  const handleSubmitAnswer = async () => {
    if (!draft.trim() || isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const answer = draft.trim();
      const response = await submitAnswer(config.session_id, { transcript: answer });
      setTranscript(answer);
      setDraft("");
      setLivePartial("");
      setAiMsg(response.message);

      if (response.stats) {
        setConfidence(response.stats.confidence);
        setEmotion(response.stats.emotion);
        setFillers(response.stats.fillers);
      }

      if (response.question) {
        setQuestion(response.question);
        speakText(`${response.message} Next question. ${response.question}`);
      } else {
        speakText(response.message);
      }
      setQuestionIndex(response.question_index);

      if (response.is_finished) {
        shouldListenRef.current = false;
        recognitionRef.current?.stop();
        await endSession(config.session_id);
        onEnd();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answer.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEnd = async () => {
    shouldListenRef.current = false;
    recognitionRef.current?.stop();
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
              ● LIVE COACH
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
          {streamEnabled ? (
            <StreamParticipantStage />
          ) : (
            <div style={{ width: "100%", height: "100%", background: "linear-gradient(135deg, #0d0d1a 0%, #111126 100%)", display: "flex", alignItems: "center", justifyContent: "center", position: "relative" }}>
              <div style={{ width: 110, height: 110, borderRadius: "50%", background: `linear-gradient(135deg, ${G.surface2}, ${G.border})`, border: `2px solid ${G.border}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "2.6rem" }}>
                C
              </div>
              <p style={{ position: "absolute", bottom: "1.2rem", color: G.muted, fontSize: "0.82rem" }}>
                Stream not configured. Running in transcript-only mode.
              </p>
            </div>
          )}

          <div style={{ position: "absolute", top: "1rem", left: "1rem", display: "flex", alignItems: "center", gap: "0.5rem", background: "rgba(0,0,0,0.7)", padding: "0.4rem 0.8rem", border: `1px solid ${emotionColor(emotion)}30` }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: emotionColor(emotion), boxShadow: `0 0 6px ${emotionColor(emotion)}` }} />
            <span style={{ fontFamily: G.mono, fontSize: "0.68rem", color: emotionColor(emotion), textTransform: "capitalize" }}>{emotion}</span>
          </div>
          <div style={{ position: "absolute", top: "1rem", right: "1rem", background: "rgba(0,0,0,0.7)", padding: "0.4rem 0.8rem", border: `1px solid ${G.border}`, fontFamily: G.mono, fontSize: "0.68rem", color: fillers > 8 ? G.accent3 : G.muted }}>
            {fillers} filler words
          </div>
          <div style={{ position: "absolute", bottom: "1rem", left: "50%", transform: "translateX(-50%)", fontFamily: G.mono, fontSize: "0.65rem", color: `${G.muted}80`, letterSpacing: "0.1em" }}>
            {streamEnabled ? "STREAM WEBRTC · LIVE CALL" : "TRANSCRIPT LOOP · TEXT MODE"}
          </div>
        </div>

        <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "1rem 1.5rem", display: "flex", alignItems: "center", gap: "0.8rem" }}>
          <canvas ref={canvasRef} width={300} height={40} style={{ flex: 1 }} />
          {!streamEnabled && (
            <button onClick={toggleMic} disabled={!micSupported} style={{ padding: "0 1rem", height: 40, background: isListening ? "rgba(110,231,183,0.15)" : G.surface2, border: `1px solid ${isListening ? G.accent : G.border}`, color: isListening ? G.accent : G.muted, fontFamily: G.font, fontSize: "0.8rem", cursor: micSupported ? "pointer" : "not-allowed", opacity: micSupported ? 1 : 0.5 }}>
              {isListening ? "Stop Mic" : "Start Mic"}
            </button>
          )}
          {!streamEnabled && (
            <button onClick={handleSubmitAnswer} disabled={!draft.trim() || isSubmitting} style={{ padding: "0 1.2rem", height: 40, background: !draft.trim() || isSubmitting ? G.surface2 : "rgba(110,231,183,0.12)", border: `1px solid ${!draft.trim() || isSubmitting ? G.border : G.accent}`, color: !draft.trim() || isSubmitting ? G.muted : G.accent, fontFamily: G.font, fontSize: "0.82rem", cursor: !draft.trim() || isSubmitting ? "not-allowed" : "pointer" }}>
              {isSubmitting ? "Analyzing..." : "Submit Answer"}
            </button>
          )}
        </div>

        <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1rem 1.2rem" }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Live Transcript
          </div>
          
          {streamEnabled ? (
            <div style={{ padding: "1.5rem", textAlign: "center", color: G.muted, fontSize: "0.85rem", border: `1px dashed ${G.border}` }}>
              The Interviewer Agent is listening via your microphone. <br/>Speak naturally to answer questions.
            </div>
          ) : (
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              rows={5}
              placeholder="Start mic to transcribe, or type manually. Include constraints, trade-offs, and decisions."
              style={{ width: "100%", resize: "vertical", background: G.surface, color: G.text, border: `1px solid ${G.border}`, fontFamily: G.font, fontSize: "0.9rem", padding: "0.8rem", outline: "none" }}
            />
          )}

          {draft && streamEnabled && <p style={{ fontSize: "0.8rem", color: G.accent, marginTop: "0.55rem" }}>You: {draft.split(" ").slice(-15).join(" ")}...</p>}
          {livePartial && !streamEnabled && <p style={{ fontSize: "0.8rem", color: G.accent, marginTop: "0.55rem" }}>Listening: {livePartial}</p>}
          
          {transcript && !streamEnabled && (
            <p style={{ fontSize: "0.78rem", color: G.muted, marginTop: "0.55rem" }}>
              Last submitted: {transcript.slice(0, 180)}{transcript.length > 180 ? "..." : ""}
            </p>
          )}
          {micError && !streamEnabled && (
            <p style={{ marginTop: "0.55rem", color: G.accent3, fontSize: "0.78rem" }}>
              {micError}
            </p>
          )}
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
              <div style={{ fontSize: "0.85rem", fontWeight: 600, color: G.text }}>AI Interviewer</div>
              <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: isSubmitting ? G.accent : G.muted }}>
                {isSubmitting ? "analyzing" : isAiSpeaking ? "speaking" : isListening ? "listening" : "ready"}
              </div>
            </div>
          </div>
          <div style={{ background: G.surface2, padding: "1rem", borderRadius: "2px" }}>
            <p style={{ fontSize: "0.83rem", color: G.text, lineHeight: 1.6 }}>{aiMsg}</p>
          </div>
        </div>

        <div style={{ padding: "1.5rem", borderBottom: `1px solid ${G.border}` }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.accent, letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "0.7rem" }}>
            Question {questionIndex}
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
            ["Filler words", fillers],
            ["Time elapsed", fmt(elapsed)],
            ["Transport", streamEnabled ? "Stream" : "Text"],
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
