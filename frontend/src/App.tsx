import React, { useEffect, useState } from "react";
import { SetupScreen } from "./screens/SetupScreen";
import { InterviewScreen } from "./screens/InterviewScreen";
import { ReportScreen } from "./screens/ReportScreen";
import { G } from "./theme";
import { LiveSessionConfig } from "./types";

export default function App() {
  const [screen, setScreen] = useState<"setup" | "interview" | "report">("setup");
  const [config, setConfig] = useState<LiveSessionConfig | null>(null);

  useEffect(() => {
    const link = document.createElement("link");
    link.href = "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=DM+Mono:wght@300;400;500&display=swap";
    link.rel = "stylesheet";
    document.head.appendChild(link);

    const style = document.createElement("style");
    style.innerHTML = `
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body {
        background-color: ${G.bg};
        color: ${G.text};
        font-family: ${G.font};
        overflow-x: hidden;
      }
      ::selection { background: ${G.accent}; color: ${G.bg}; }
      ::-webkit-scrollbar { width: 6px; }
      ::-webkit-scrollbar-track { background: ${G.bg}; }
      ::-webkit-scrollbar-thumb { background: ${G.border}; border-radius: 10px; }
      ::-webkit-scrollbar-thumb:hover { background: ${G.muted}; }
    `;
    document.head.appendChild(style);
  }, []);

  const handleStart = (cfg: LiveSessionConfig) => {
    setConfig(cfg);
    setScreen("interview");
  };

  const handleEnd = () => {
    setScreen("report");
  };

  const handleRestart = () => {
    setConfig(null);
    setScreen("setup");
  };

  return (
    <div className="app-container">
      {screen === "setup" && <SetupScreen onStart={handleStart} />}

      {screen === "interview" && config && (
        <InterviewScreen config={config} onEnd={handleEnd} />
      )}

      {screen === "report" && config && (
        <ReportScreen 
          sessionId={config.session_id} 
          onRestart={handleRestart} 
        />
      )}
    </div>
  );
}
