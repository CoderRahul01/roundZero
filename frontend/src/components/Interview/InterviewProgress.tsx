import React from "react";
import { G } from "../../theme";

interface InterviewProgressProps {
  current: number;
  total: number;
}

export const InterviewProgress: React.FC<InterviewProgressProps> = ({ current, total }) => {
  const progress = (current / total) * 100;

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <span style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
          Interview Progress
        </span>
        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: G.accent }}>
          {current} / {total}
        </span>
      </div>
      
      <div style={{ 
        height: 6, 
        background: G.surface2, 
        border: `1px solid ${G.border}`,
        borderRadius: 3, 
        overflow: "hidden",
        position: "relative"
      }}>
        <div 
          style={{ 
            height: "100%", 
            width: `${progress}%`, 
            background: G.accent, 
            boxShadow: `0 0 10px ${G.accent}44`,
            transition: "width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)" 
          }} 
        />
        
        {/* Step Indicators */}
        {Array.from({ length: total - 1 }).map((_, i) => (
          <div key={i} style={{
            position: "absolute",
            left: `${((i + 1) / total) * 100}%`,
            top: 0,
            width: 1,
            height: "100%",
            background: G.bg,
            opacity: 0.3
          }} />
        ))}
      </div>
    </div>
  );
};
