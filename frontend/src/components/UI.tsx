import React, { CSSProperties } from "react";
import { G } from "../theme";

// ── LABEL ────────────────────────────────────
export function Label({ children, style }: { children: React.ReactNode; style?: CSSProperties }) {
  return (
    <div style={{
      fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, 
      textTransform: "uppercase", letterSpacing: "0.12em", 
      marginBottom: "0.5rem", ...style 
    }}>
      {children}
    </div>
  );
}

// ── INPUT ────────────────────────────────────
export function Input({
  value, onChange, placeholder, type = "text",
}: {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      style={{
        width: "100%", background: G.surface2,
        border: `1px solid ${G.border}`, color: G.text,
        fontFamily: G.font, fontSize: "0.9rem",
        padding: "0.75rem 1rem", outline: "none",
        boxSizing: "border-box", transition: "border-color 0.2s"
      }}
      onFocus={(e) => (e.target.style.borderColor = G.accent)}
      onBlur={(e) => (e.target.style.borderColor = G.border)}
    />
  );
}

// ── PRIMARY BUTTON ────────────────────────────
export function Btn({
  children, onClick, disabled = false, style,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  style?: CSSProperties;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: "100%", padding: "0.9rem",
        background: disabled ? G.surface2 : "rgba(110,231,183,0.12)",
        border: `1px solid ${disabled ? G.border : G.accent}`,
        color: disabled ? G.muted : G.accent,
        fontFamily: G.font, fontSize: "0.9rem",
        fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
        transition: "all 0.2s", ...style
      }}
      onMouseEnter={(e) => {
        if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(110,231,183,0.18)";
      }}
      onMouseLeave={(e) => {
        if (!disabled) (e.currentTarget as HTMLButtonElement).style.background = "rgba(110,231,183,0.12)";
      }}
    >
      {children}
    </button>
  );
}

// ── SECONDARY BUTTON ─────────────────────────
export function GhostBtn({
  children, onClick, style,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  style?: CSSProperties;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "0.75rem 1.1rem",
        background: "transparent",
        border: `1px solid ${G.border}`,
        color: G.muted,
        fontFamily: G.font,
        fontSize: "0.85rem",
        fontWeight: 600,
        cursor: "pointer",
        transition: "all 0.15s",
        ...style,
      }}
    >
      {children}
    </button>
  );
}

// ── SPINNER ──────────────────────────────────
export function Spinner() {
  return (
    <div style={{
      width: 14, height: 14,
      border: `2px solid rgba(110,231,183,0.3)`,
      borderTop: `2px solid ${G.accent}`,
      borderRadius: "50%",
      animation: "spin 0.7s linear infinite"
    }} />
  );
}
