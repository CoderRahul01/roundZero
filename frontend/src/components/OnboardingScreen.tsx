import React, { useState, useEffect, useRef } from "react";
import { G } from "../theme";

interface OnboardingScreenProps {
  firstName?: string;
  questionCount: number;
  onReady: () => void;
  onCancel: () => void;
}

type OnboardingStep = "greeting" | "introduction" | "readiness" | "countdown";

export function OnboardingScreen({
  firstName,
  questionCount,
  onReady,
  onCancel,
}: OnboardingScreenProps) {
  const [step, setStep] = useState<OnboardingStep>("greeting");
  const [greetingText, setGreetingText] = useState("");
  const [introductionText, setIntroductionText] = useState("");
  const [isPlaying, setIsPlaying] = useState(false);
  const [userResponse, setUserResponse] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [error, setError] = useState<string | null>(null);
  
  const recognitionRef = useRef<any>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Generate greeting and introduction on mount
  useEffect(() => {
    const timeOfDay = getTimeOfDay();
    const name = firstName || "there";
    const greeting = `Hey ${name}, nice to meet you. ${timeOfDay}.`;
    const introduction = `We have an interview with ${questionCount} questions lined up for you today. I'll ask you each question, and you can take your time to answer. I might ask follow-up questions if I need clarification or want to dive deeper. Just speak naturally, and I'll be listening.`;
    
    setGreetingText(greeting);
    setIntroductionText(introduction);
    
    // Auto-play greeting
    speakText(greeting);
  }, [firstName, questionCount]);

  const getTimeOfDay = (): string => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return "Good morning";
    if (hour >= 12 && hour < 17) return "Good afternoon";
    if (hour >= 17 && hour < 21) return "Good evening";
    return "Hello";
  };

  const speakText = (text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onstart = () => setIsPlaying(true);
    utterance.onend = () => {
      setIsPlaying(false);
      // Auto-advance to next step
      if (step === "greeting") {
        setTimeout(() => {
          setStep("introduction");
          speakText(introductionText);
        }, 1000);
      } else if (step === "introduction") {
        setTimeout(() => {
          setStep("readiness");
          speakText("Are you ready to start?");
        }, 1000);
      }
    };
    utterance.onerror = () => setIsPlaying(false);
    
    window.speechSynthesis.speak(utterance);
  };

  const startListening = () => {
    const Recognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!Recognition) {
      setError("Speech recognition not supported in this browser");
      return;
    }

    const recognition = new Recognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setUserResponse(transcript);
      handleReadinessResponse(transcript);
    };

    recognition.onerror = (event: any) => {
      setError(`Microphone error: ${event.error}`);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
    setError(null);
  };

  const handleReadinessResponse = (response: string) => {
    // Simple client-side interpretation
    const affirmative = /yes|yeah|sure|ready|let's go|okay|ok|yep|absolutely/i;
    const negative = /no|not yet|wait|hold on|give me a minute/i;

    if (affirmative.test(response)) {
      speakText("Great! Let's begin.");
      setTimeout(() => {
        setStep("countdown");
        startCountdown();
      }, 2000);
    } else if (negative.test(response)) {
      speakText("No problem. Take your time. Let me know when you're ready.");
      setStep("readiness");
    } else {
      speakText("I didn't quite catch that. Are you ready to start?");
      setTimeout(() => startListening(), 2000);
    }
  };

  const startCountdown = () => {
    let count = 5;
    setCountdown(count);
    
    const interval = setInterval(() => {
      count -= 1;
      setCountdown(count);
      
      if (count === 0) {
        clearInterval(interval);
        setTimeout(() => {
          onReady();
        }, 500);
      }
    }, 1000);
  };

  const handleManualReady = () => {
    speakText("Great! Let's begin.");
    setTimeout(() => {
      setStep("countdown");
      startCountdown();
    }, 2000);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: G.bg,
        fontFamily: G.font,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
      }}
    >
      <div
        style={{
          maxWidth: "600px",
          width: "100%",
          background: G.surface,
          border: `1px solid ${G.border}`,
          padding: "3rem",
          textAlign: "center",
        }}
      >
        {/* Logo */}
        <div style={{ marginBottom: "2rem" }}>
          <span
            style={{
              fontWeight: 800,
              fontSize: "1.8rem",
              color: G.text,
              letterSpacing: "-0.02em",
            }}
          >
            Round<span style={{ color: G.accent }}>Zero</span>
          </span>
        </div>

        {/* Greeting Step */}
        {step === "greeting" && (
          <div style={{ animation: "fadeIn 0.5s ease-in" }}>
            <div
              style={{
                width: "120px",
                height: "120px",
                margin: "0 auto 2rem",
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`,
                border: `2px solid ${G.accent}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "3rem",
              }}
            >
              👋
            </div>
            <p
              style={{
                fontSize: "1.5rem",
                color: G.text,
                lineHeight: 1.6,
                marginBottom: "1rem",
              }}
            >
              {greetingText}
            </p>
            {isPlaying && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: G.accent,
                  fontSize: "0.9rem",
                  marginTop: "1rem",
                }}
              >
                <div className="pulse-dot" />
                Speaking...
              </div>
            )}
          </div>
        )}

        {/* Introduction Step */}
        {step === "introduction" && (
          <div style={{ animation: "fadeIn 0.5s ease-in" }}>
            <div
              style={{
                width: "120px",
                height: "120px",
                margin: "0 auto 2rem",
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`,
                border: `2px solid ${G.accent}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "3rem",
              }}
            >
              📋
            </div>
            <p
              style={{
                fontSize: "1.2rem",
                color: G.text,
                lineHeight: 1.8,
                marginBottom: "1rem",
              }}
            >
              {introductionText}
            </p>
            {isPlaying && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: G.accent,
                  fontSize: "0.9rem",
                  marginTop: "1rem",
                }}
              >
                <div className="pulse-dot" />
                Speaking...
              </div>
            )}
          </div>
        )}

        {/* Readiness Step */}
        {step === "readiness" && (
          <div style={{ animation: "fadeIn 0.5s ease-in" }}>
            <div
              style={{
                width: "120px",
                height: "120px",
                margin: "0 auto 2rem",
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`,
                border: `2px solid ${G.accent}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "3rem",
              }}
            >
              🎯
            </div>
            <p
              style={{
                fontSize: "1.8rem",
                color: G.text,
                fontWeight: 600,
                marginBottom: "2rem",
              }}
            >
              Are you ready to start?
            </p>
            
            <div style={{ display: "flex", gap: "1rem", justifyContent: "center", marginBottom: "1.5rem" }}>
              <button
                onClick={handleManualReady}
                disabled={isListening}
                style={{
                  padding: "1rem 2rem",
                  background: `${G.accent}20`,
                  border: `2px solid ${G.accent}`,
                  color: G.accent,
                  fontFamily: G.font,
                  fontSize: "1rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = `${G.accent}30`;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = `${G.accent}20`;
                }}
              >
                Yes, Let's Go!
              </button>
              
              <button
                onClick={startListening}
                disabled={isListening}
                style={{
                  padding: "1rem 2rem",
                  background: G.surface2,
                  border: `1px solid ${G.border}`,
                  color: G.text,
                  fontFamily: G.font,
                  fontSize: "1rem",
                  cursor: "pointer",
                }}
              >
                {isListening ? "Listening..." : "Use Voice"}
              </button>
            </div>

            {userResponse && (
              <p style={{ fontSize: "0.9rem", color: G.muted, marginTop: "1rem" }}>
                You said: "{userResponse}"
              </p>
            )}

            {error && (
              <p style={{ fontSize: "0.9rem", color: G.accent3, marginTop: "1rem" }}>
                {error}
              </p>
            )}

            <button
              onClick={onCancel}
              style={{
                marginTop: "2rem",
                padding: "0.5rem 1rem",
                background: "transparent",
                border: "none",
                color: G.muted,
                fontFamily: G.font,
                fontSize: "0.9rem",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Cancel
            </button>
          </div>
        )}

        {/* Countdown Step */}
        {step === "countdown" && (
          <div style={{ animation: "fadeIn 0.5s ease-in" }}>
            <div
              style={{
                width: "200px",
                height: "200px",
                margin: "0 auto",
                borderRadius: "50%",
                background: `linear-gradient(135deg, ${G.accent}10, ${G.accent}30)`,
                border: `3px solid ${G.accent}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "6rem",
                fontWeight: 800,
                color: G.accent,
                animation: "pulse 1s ease-in-out infinite",
              }}
            >
              {countdown > 0 ? countdown : "🚀"}
            </div>
            <p
              style={{
                fontSize: "1.5rem",
                color: G.text,
                marginTop: "2rem",
                fontWeight: 600,
              }}
            >
              {countdown > 0 ? "Get ready..." : "Let's begin!"}
            </p>
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }

        .pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: ${G.accent};
          animation: pulse 1.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
