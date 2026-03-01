import React, { useState, useEffect } from "react";
import { G } from "../theme";

interface CountdownTimerProps {
  duration?: number; // Duration in seconds (default: 5)
  onComplete: () => void;
}

export function CountdownTimer({ duration = 5, onComplete }: CountdownTimerProps) {
  const [count, setCount] = useState(duration);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (count === 0) {
      setIsComplete(true);
      setTimeout(() => {
        onComplete();
      }, 1000); // Show "Let's begin!" for 1 second before completing
      return;
    }

    const timer = setTimeout(() => {
      setCount(count - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [count, onComplete]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0a0a1a 0%, #0f0f2a 50%, #1a1a3a 100%)",
        fontFamily: G.font,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
      }}
    >
      <div style={{ textAlign: "center" }}>
        {/* Countdown Number */}
        <div
          style={{
            width: "280px",
            height: "280px",
            margin: "0 auto",
            borderRadius: "50%",
            background: isComplete
              ? `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`
              : `radial-gradient(circle, rgba(110, 231, 183, 0.1) 0%, rgba(110, 231, 183, 0.05) 100%)`,
            border: `4px solid ${isComplete ? G.accent : `rgba(110, 231, 183, 0.3)`}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: isComplete ? "4rem" : "8rem",
            fontWeight: 800,
            color: G.accent,
            animation: isComplete ? "pulse 0.5s ease-in-out" : "fadeScale 1s ease-in-out",
            boxShadow: isComplete
              ? `0 0 60px ${G.accent}40, 0 0 120px ${G.accent}20`
              : `0 0 40px rgba(110, 231, 183, 0.2)`,
            transition: "all 0.3s ease",
          }}
        >
          {isComplete ? "🚀" : count}
        </div>

        {/* Message */}
        <p
          style={{
            fontSize: "2rem",
            color: G.text,
            marginTop: "3rem",
            fontWeight: 600,
            animation: "fadeIn 0.5s ease-in",
          }}
        >
          {isComplete ? "Let's begin!" : "Get ready..."}
        </p>

        {/* Subtitle */}
        {!isComplete && (
          <p
            style={{
              fontSize: "1.1rem",
              color: G.muted,
              marginTop: "1rem",
              animation: "fadeIn 0.5s ease-in 0.2s both",
            }}
          >
            Your interview starts in {count} second{count !== 1 ? "s" : ""}
          </p>
        )}

        {/* Progress Dots */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            justifyContent: "center",
            marginTop: "3rem",
          }}
        >
          {Array.from({ length: duration }).map((_, index) => (
            <div
              key={index}
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background:
                  index < duration - count
                    ? G.accent
                    : `rgba(110, 231, 183, 0.2)`,
                transition: "all 0.3s ease",
                boxShadow:
                  index < duration - count
                    ? `0 0 10px ${G.accent}`
                    : "none",
              }}
            />
          ))}
        </div>
      </div>

      <style>{`
        @keyframes fadeScale {
          0% {
            opacity: 0;
            transform: scale(0.8);
          }
          50% {
            opacity: 1;
            transform: scale(1.05);
          }
          100% {
            opacity: 1;
            transform: scale(1);
          }
        }

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
            transform: scale(1.1);
          }
        }
      `}</style>
    </div>
  );
}
