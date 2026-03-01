import React, { useEffect, useState } from "react";
import { G } from "../theme";

interface TransitionScreenProps {
  nextQuestionNumber: number;
  feedback?: string;
  duration?: number; // Duration in milliseconds (default: 2000)
  onComplete: () => void;
}

export function TransitionScreen({
  nextQuestionNumber,
  feedback,
  duration = 2000,
  onComplete,
}: TransitionScreenProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Animate progress bar
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          return 100;
        }
        return prev + (100 / (duration / 50)); // Update every 50ms
      });
    }, 50);

    // Complete after duration
    const timeout = setTimeout(() => {
      onComplete();
    }, duration);

    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [duration, onComplete]);

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
      <div style={{ maxWidth: "600px", width: "100%", textAlign: "center" }}>
        {/* Feedback (if provided) */}
        {feedback && (
          <div
            style={{
              background: `${G.accent}10`,
              border: `1px solid ${G.accent}30`,
              padding: "1.5rem",
              marginBottom: "2rem",
              borderRadius: "4px",
              animation: "fadeIn 0.5s ease-in",
            }}
          >
            <p
              style={{
                fontSize: "1.1rem",
                color: G.text,
                lineHeight: 1.6,
                margin: 0,
              }}
            >
              {feedback}
            </p>
          </div>
        )}

        {/* Transition Icon */}
        <div
          style={{
            width: "120px",
            height: "120px",
            margin: "0 auto 2rem",
            borderRadius: "50%",
            background: `linear-gradient(135deg, ${G.accent}20, ${G.accent}40)`,
            border: `3px solid ${G.accent}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "3rem",
            animation: "rotate 2s linear infinite",
          }}
        >
          ➡️
        </div>

        {/* Transition Message */}
        <p
          style={{
            fontSize: "1.5rem",
            color: G.text,
            fontWeight: 600,
            marginBottom: "0.5rem",
          }}
        >
          Moving to Question {nextQuestionNumber}
        </p>

        <p
          style={{
            fontSize: "1rem",
            color: G.muted,
            marginBottom: "2rem",
          }}
        >
          Get ready for the next question...
        </p>

        {/* Progress Bar */}
        <div
          style={{
            height: "4px",
            background: G.surface2,
            borderRadius: "2px",
            overflow: "hidden",
            maxWidth: "400px",
            margin: "0 auto",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${G.accent}, ${G.accent}dd)`,
              transition: "width 0.05s linear",
              borderRadius: "2px",
            }}
          />
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes rotate {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
