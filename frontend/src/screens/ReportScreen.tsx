import React, { useEffect, useState } from "react";
import { fetchReport, SessionReport as BackendSessionReport } from "../api";
import { G } from "../theme";
import { LiveSessionConfig, SessionReport } from "../types";

function emotionColor(emotion: string) {
  const map: Record<string, string> = {
    confident: G.accent,
    neutral: "#94a3b8",
    confused: G.accent2,
    focused: "#818cf8",
    nervous: G.accent3,
  };
  return map[emotion] || "#94a3b8";
}

function toViewModel(report: BackendSessionReport): SessionReport {
  return {
    overallScore: report.overall_score,
    confidenceAvg: report.confidence_avg,
    duration: `${Math.max(1, Math.round(report.duration_seconds / 60))} min`,
    questionsAnswered: report.questions_answered,
    breakdown: report.breakdown.map((item) => ({
      q: item.question,
      score: item.score,
      emotion: item.emotion,
      fillers: item.fillers,
      feedback: item.feedback,
    })),
    strengths: report.strengths,
    weaknesses: report.weaknesses,
    emotionTimeline: report.emotion_timeline,
  };
}

export function ReportScreen({ config, onRestart }: { config: LiveSessionConfig; onRestart: () => void }) {
  const [activeQ, setActiveQ] = useState<number | null>(null);
  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const response = await fetchReport(config.session_id);
        if (mounted) {
          setReport(toViewModel(response));
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load report");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, [config.session_id]);

  if (loading) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: G.bg, color: G.text }}>
        Generating your report...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ height: "100vh", display: "grid", placeItems: "center", background: G.bg, color: G.text, fontFamily: G.font }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ marginBottom: "0.8rem", color: G.accent3 }}>{error || "Report unavailable"}</p>
          <button onClick={onRestart} style={{ padding: "0.65rem 1.1rem", border: `1px solid ${G.border}`, background: G.surface, color: G.text, cursor: "pointer" }}>
            Start New Interview
          </button>
        </div>
      </div>
    );
  }

  const scoreColor = (score: number) => (score >= 80 ? G.accent : score >= 60 ? G.accent2 : G.accent3);

  return (
    <div style={{ minHeight: "100vh", background: G.bg, fontFamily: G.font, padding: "2rem" }}>
      <div style={{ maxWidth: "960px", margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "2.5rem" }}>
          <div>
            <div style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.accent, letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "0.5rem" }}>
              Session Complete
            </div>
            <h1 style={{ fontSize: "2.2rem", fontWeight: 800, color: G.text, letterSpacing: "-0.03em" }}>
              Your Report, <span style={{ color: G.accent }}>{config.name}</span>
            </h1>
            <p style={{ color: G.muted, marginTop: "0.4rem", fontSize: "0.88rem" }}>
              {config.role} · {config.topics.join(", ")}
            </p>
          </div>
          <button onClick={onRestart} style={{ padding: "0.7rem 1.5rem", background: "rgba(110,231,183,0.08)", border: "1px solid rgba(110,231,183,0.3)", color: G.accent, fontFamily: G.font, fontSize: "0.85rem", cursor: "pointer" }}>
            New Interview →
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: "1rem", marginBottom: "2rem" }}>
          {[
            { label: "Overall Score", value: `${report.overallScore}`, unit: "/100", color: scoreColor(report.overallScore) },
            { label: "Avg Confidence", value: `${report.confidenceAvg}`, unit: "/100", color: scoreColor(report.confidenceAvg) },
            { label: "Duration", value: report.duration, unit: "", color: "#94a3b8" },
            { label: "Questions", value: `${report.questionsAnswered}`, unit: ` / ${config.total_questions}`, color: G.accent },
          ].map((item) => (
            <div key={item.label} style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "1.5rem", position: "relative", overflow: "hidden" }}>
              <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: item.color }} />
              <div style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.5rem" }}>{item.label}</div>
              <div style={{ fontSize: "2rem", fontWeight: 800, color: item.color, letterSpacing: "-0.03em", lineHeight: 1 }}>
                {item.value}
                <span style={{ fontSize: "0.85rem", fontWeight: 400, color: G.muted }}>{item.unit}</span>
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "1.5rem", marginBottom: "2rem" }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1.2rem" }}>
            Confidence Timeline
          </div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: "8px", height: "90px" }}>
            {report.emotionTimeline.map((value, index) => (
              <div key={index} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "100%", height: `${Math.max(6, value)}%`, background: scoreColor(value), opacity: 0.85, borderRadius: "2px 2px 0 0", minHeight: 4 }} />
                <span style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted }}>Q{index + 1}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "2rem" }}>
          <div style={{ background: G.surface, border: "1px solid rgba(110,231,183,0.2)", padding: "1.5rem" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.accent, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem" }}>✓ Strengths</div>
            {report.strengths.map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.6rem", fontSize: "0.85rem", color: G.text }}>
                <div style={{ width: 4, height: 4, borderRadius: "50%", background: G.accent, flexShrink: 0 }} />
                {item}
              </div>
            ))}
          </div>

          <div style={{ background: G.surface, border: "1px solid rgba(244,63,94,0.2)", padding: "1.5rem" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.accent3, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "1rem" }}>⚠ Areas to Improve</div>
            {report.weaknesses.map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.6rem", fontSize: "0.85rem", color: G.text }}>
                <div style={{ width: 4, height: 4, borderRadius: "50%", background: G.accent3, flexShrink: 0 }} />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div style={{ background: G.surface, border: `1px solid ${G.border}` }}>
          <div style={{ padding: "1.2rem 1.5rem", borderBottom: `1px solid ${G.border}` }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.65rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em" }}>
              Question-by-Question Breakdown
            </div>
          </div>

          {report.breakdown.map((item, index) => (
            <div key={`${item.q}-${index}`}>
              <div
                onClick={() => setActiveQ(activeQ === index ? null : index)}
                style={{ padding: "1rem 1.5rem", display: "flex", alignItems: "center", gap: "1rem", cursor: "pointer", borderBottom: `1px solid ${G.border}` }}
              >
                <div style={{ width: 34, height: 34, borderRadius: "50%", background: `${scoreColor(item.score)}15`, border: `1px solid ${scoreColor(item.score)}40`, display: "grid", placeItems: "center", fontFamily: G.mono, fontSize: "0.74rem", color: scoreColor(item.score), flexShrink: 0 }}>
                  {item.score}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.85rem", color: G.text, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.q}</div>
                  <div style={{ display: "flex", gap: "1rem", marginTop: "0.3rem" }}>
                    <span style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted }}>
                      emotion: <span style={{ color: emotionColor(item.emotion) }}>{item.emotion}</span>
                    </span>
                    <span style={{ fontFamily: G.mono, fontSize: "0.62rem", color: G.muted }}>fillers: {item.fillers}</span>
                  </div>
                </div>
                <div style={{ color: G.muted, fontSize: "0.75rem", transform: activeQ === index ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}>▼</div>
              </div>

              {activeQ === index && (
                <div style={{ padding: "1rem 1.5rem 1.2rem 3.5rem", background: G.surface2, borderBottom: `1px solid ${G.border}`, borderLeft: `3px solid ${scoreColor(item.score)}` }}>
                  <div style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.5rem" }}>AI Feedback</div>
                  <p style={{ fontSize: "0.85rem", color: G.text, lineHeight: 1.6 }}>{item.feedback}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
