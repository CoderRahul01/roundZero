import React, { useEffect, useState } from "react";
import {
  Call,
  StreamCall,
  StreamVideo,
  StreamVideoClient,
  User,
} from "@stream-io/video-react-sdk";
import { SetupScreen } from "./screens/SetupScreen";
import { InterviewScreen } from "./screens/InterviewScreen";
import { ReportScreen } from "./screens/ReportScreen";
import { G } from "./theme";
import { LiveSessionConfig } from "./types";

export default function App() {
  const [screen, setScreen] = useState<"setup" | "interview" | "report">("setup");
  const [config, setConfig] = useState<LiveSessionConfig | null>(null);
  const [streamClient, setStreamClient] = useState<StreamVideoClient | null>(null);
  const [streamCall, setStreamCall] = useState<Call | null>(null);

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

  const cleanupStream = () => {
    if (streamCall) {
      streamCall.leave().catch(() => undefined);
    }
    if (streamClient) {
      streamClient.disconnectUser().catch(() => undefined);
    }
    setStreamCall(null);
    setStreamClient(null);
  };

  const handleStart = (cfg: LiveSessionConfig) => {
    cleanupStream();
    setConfig(cfg);

    if (cfg.stream_api_key && cfg.token && cfg.call_id) {
      const user: User = { id: cfg.user_id, name: cfg.name };
      const client = new StreamVideoClient({
        apiKey: cfg.stream_api_key,
        token: cfg.token,
        user,
      });

      const call = client.call("default", cfg.call_id);
      setStreamClient(client);
      setStreamCall(call);
    }

    setScreen("interview");
  };

  const handleEnd = () => {
    cleanupStream();
    setScreen("report");
  };

  const handleRestart = () => {
    cleanupStream();
    setConfig(null);
    setScreen("setup");
  };

  return (
    <div className="app-container">
      {screen === "setup" && <SetupScreen onStart={handleStart} />}

      {/* DEMO MODE: Force text mode with browser TTS */}
      {screen === "interview" && config && (
        <InterviewScreen config={config} onEnd={handleEnd} streamEnabled={false} />
      )}

      {screen === "report" && config && <ReportScreen config={config} onRestart={handleRestart} />}
    </div>
  );
}
