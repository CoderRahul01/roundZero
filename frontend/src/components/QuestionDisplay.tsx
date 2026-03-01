import React from "react";
import { G } from "../theme";

interface QuestionDisplayProps {
  questionNumber: number;
  totalQuestions: number;
  questionText: string;
  isListening: boolean;
}

export function QuestionDisplay({
  questionNumber,
  totalQuestions,
  questionText,
  isListening,
}: QuestionDisplayProps) {
  const progress = (questionNumber / totalQuestions) * 100;

  return (
    <div
      style={{
        background: G.surface,
        border: `1px solid ${G.border}`,
        padding: "2rem",
        marginBottom: "1.5rem",
      }}
    >
      {/* Progress Bar */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "0.5rem",
          }}
        >
          <span
            style={{
              fontFamily: G.mono,
              fontSize: "0.75rem",
              color: G.accent,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            Question {questionNumber} of {totalQuestions}
          </span>
          <span
            style={{
              fontFamily: G.mono,
              fontSize: "0.75rem",
              color: G.muted,
            }}
          >
            {Math.round(progress)}%
          </span>
        </div>
        <div
          style={{
            height: "6px",
            background: G.surface2,
            borderRadius: "3px",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progress}%`,
              background: `linear-gradient(90deg, ${G.accent}, ${G.accent}dd)`,
              transition: "width 0.5s ease",
              borderRadius: "3px",
            }}
          />
        </div>
      </div>

      {/* Question Text */}
      <div
        style={{
          background: G.surface2,
          padding: "1.5rem",
          borderLeft: `4px solid ${G.accent}`,
        }}
      >
        <p
          style={{
            fontSize: "1.2rem",
            color: G.text,
            lineHeight: 1.7,
            fontWeight: 500,
            margin: 0,
          }}
        >
          {questionText}
        </p>
      </div>

      {/* Listening Indicator */}
      {isListening && (
        <div
          style={{
            marginTop: "1rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            color: G.accent,
            fontSize: "0.9rem",
          }}
        >
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: G.accent,
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
          <span>Listening for your answer...</span>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
            transform: scale(1.2);
          }
        }
      `}</style>
    </div>
  );
}
