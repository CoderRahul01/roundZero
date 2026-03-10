import React, { useEffect, useState } from "react";
import { G } from "../theme";
import { Btn, Spinner, GhostBtn } from "../components/UI";
import { fetchReport } from "../api";
import { SessionReport } from "../types";

export function ReportScreen({ 
  sessionId, 
  onRestart 
}: { 
  sessionId: string; 
  onRestart: () => void;
}) {
  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchReport(sessionId) as SessionReport;
        setReport(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load your interview report.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [sessionId]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: G.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <Spinner />
          <p style={{ color: G.muted, marginTop: "1rem" }}>Compiling your performance report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ minHeight: "100vh", background: G.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: G.accent3 }}>{error || "Report not found."}</p>
        <Btn onClick={onRestart}>Go Back</Btn>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: G.bg, color: G.text, padding: "4rem 2rem", fontFamily: G.font }}>
      <div style={{ maxWidth: "900px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: "4rem" }}>
          <h1 style={{ fontSize: "3.5rem", fontWeight: 800, marginBottom: "0.5rem", letterSpacing: "-0.03em" }}>
            Performance <span style={{ color: G.accent }}>Report</span>
          </h1>
          <p style={{ color: G.muted, fontFamily: G.mono, fontSize: "0.8rem", letterSpacing: "0.1em" }}>SESSION ID: {sessionId}</p>
        </div>

        {/* Score Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.5rem", marginBottom: "3rem" }}>
          <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "2.5rem", textAlign: "center", position: "relative", overflow: "hidden" }}>
             <div style={{ fontSize: "0.7rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "0.8rem", fontFamily: G.mono }}>Overall Score</div>
             <div style={{ fontSize: "4rem", fontWeight: 800, color: G.accent }}>{report.overallScore}<small style={{ fontSize: "1.2rem", color: G.muted }}>/100</small></div>
             <div style={{ position: "absolute", bottom: 0, left: 0, height: 4, width: `${report.overallScore}%`, background: G.accent }} />
          </div>
          <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "2.5rem", textAlign: "center", position: "relative", overflow: "hidden" }}>
             <div style={{ fontSize: "0.7rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "0.8rem", fontFamily: G.mono }}>Confidence Avg</div>
             <div style={{ fontSize: "4rem", fontWeight: 800, color: G.accent2 }}>{report.confidenceAvg}%</div>
             <div style={{ position: "absolute", bottom: 0, left: 0, height: 4, width: `${report.confidenceAvg}%`, background: G.accent2 }} />
          </div>
          <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "2.5rem", textAlign: "center", position: "relative", overflow: "hidden" }}>
             <div style={{ fontSize: "0.7rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "0.8rem", fontFamily: G.mono }}>Fillers Count</div>
             <div style={{ fontSize: "4rem", fontWeight: 800, color: G.accent3 }}>{report.totalFillers || 0}</div>
             <div style={{ position: "absolute", bottom: 0, left: 0, height: 4, width: "100%", background: G.accent3, opacity: 0.2 }} />
          </div>
        </div>

        {/* Analysis Card */}
        <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "3rem", marginBottom: "3rem", borderRadius: "4px", boxShadow: `0 20px 40px rgba(0,0,0,0.3)` }}>
           <h2 style={{ fontSize: "0.8rem", fontFamily: G.mono, color: G.accent, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1.5rem" }}>Coach's Analysis</h2>
           <p style={{ lineHeight: 1.8, color: G.text, fontSize: "1.1rem" }}>{report.summary}</p>
        </div>

        {/* Breakdown */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginBottom: "4rem" }}>
           <div style={{ background: "rgba(16,185,129,0.05)", border: `1px solid rgba(16,185,129,0.2)`, padding: "2rem" }}>
              <h3 style={{ color: "#10b981", marginBottom: "1rem" }}>Key Strengths</h3>
              <ul style={{ paddingLeft: "1.2rem", lineHeight: 2 }}>
                {report.strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
           </div>
           <div style={{ background: "rgba(244,63,94,0.05)", border: `1px solid rgba(244,63,94,0.2)`, padding: "2rem" }}>
              <h3 style={{ color: "#f43f5e", marginBottom: "1rem" }}>Areas for Improvement</h3>
              <ul style={{ paddingLeft: "1.2rem", lineHeight: 2 }}>
                {report.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
           </div>
        </div>

        {/* Question Breakdown List */}
        <h2 style={{ fontSize: "0.8rem", fontFamily: G.mono, color: G.muted, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1.5rem" }}>Detailed Breakdown</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {report.breakdown.map((item, idx) => (
            <div key={idx} style={{ 
              background: "rgba(255,255,255,0.02)", 
              backdropFilter: "blur(10px)", 
              border: `1px solid ${G.border}`, 
              padding: "2rem",
              transition: "transform 0.3s ease" 
            }}>
               <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
                  <span style={{ color: G.muted, fontSize: "0.65rem", fontFamily: G.mono, letterSpacing: "0.1em" }}>QUESTION {idx + 1}</span>
                  <span style={{ color: G.accent, fontWeight: 800, fontSize: "1.1rem" }}>{item.score}%</span>
               </div>
               <p style={{ fontWeight: 700, fontSize: "1.1rem", marginBottom: "1.2rem", color: G.text, letterSpacing: "-0.01em" }}>{item.q}</p>
               <div style={{ fontSize: "0.95rem", color: G.muted, lineHeight: 1.6, padding: "1.2rem", background: "rgba(0,0,0,0.2)", borderLeft: `2px solid ${G.accent}` }}>
                 {item.feedback}
               </div>
            </div>
          ))}
        </div>

        <div style={{ textAlign: "center", marginTop: "4rem" }}>
           <Btn onClick={onRestart}>Practice Again →</Btn>
        </div>
      </div>
    </div>
  );
}
