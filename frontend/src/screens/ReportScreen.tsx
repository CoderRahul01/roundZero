import React, { useEffect, useState } from "react";
import { G } from "../theme";
import { Btn, Spinner } from "../components/UI";
import { fetchReport } from "../api";
import { SessionReport } from "../types";

function ScoreRing({ value, color, size = 80 }: { value: number; color: string; size?: number }) {
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - value / 100);
  return (
    <svg width={size} height={size} style={{ display: "block", margin: "0 auto" }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={`${color}20`} strokeWidth={7} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth={7}
        strokeDasharray={circ} strokeDashoffset={fill}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dashoffset 1s ease" }}
      />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
        fill={color} fontSize={size < 60 ? 13 : 17} fontWeight={800} fontFamily={G.mono}>
        {value}
      </text>
    </svg>
  );
}

function scoreColor(s: number) {
  if (s >= 70) return G.accent;
  if (s >= 45) return G.accent2;
  return G.accent3;
}

function ScoreTrendChart({ scores, trend }: { scores: number[]; trend?: string }) {
  if (!scores || scores.length < 2) return null;
  const w = 280, h = 64, pad = 20;
  const color = trend === "improving" ? "#10b981" : trend === "declining" ? "#f43f5e" : G.accent2;
  const step = (w - 2 * pad) / (scores.length - 1);
  const points = scores.map((s, i) => ({
    x: pad + i * step,
    y: h - pad - (s / 10) * (h - 2 * pad),
  }));
  const polyline = points.map(p => `${p.x},${p.y}`).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={polyline} fill="none" stroke={`${color}40`} strokeWidth={2} />
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4} fill={color} />
      ))}
      {points.map((p, i) => (
        <text key={i} x={p.x} y={h - 2} textAnchor="middle"
          fontSize={9} fill={G.muted} fontFamily={G.mono}>
          Q{i + 1}
        </text>
      ))}
    </svg>
  );
}

export function ReportScreen({
  sessionId,
  onRestart,
}: {
  sessionId: string;
  onRestart: () => void;
}) {
  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      // Brief delay so backend has time to finalise the report after session end
      await new Promise(r => setTimeout(r, 1200));
      try {
        const data = await fetchReport(sessionId) as SessionReport;
        setReport(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load your interview report. Please try again.");
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
          <p style={{ color: G.muted, marginTop: "1.2rem", fontFamily: G.mono, fontSize: "0.8rem" }}>
            Compiling your performance report…
          </p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ minHeight: "100vh", background: G.bg, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "1.5rem" }}>
        <p style={{ color: G.accent3, fontFamily: G.mono, fontSize: "0.85rem" }}>{error || "Report not found."}</p>
        <Btn onClick={onRestart}>Start New Interview</Btn>
      </div>
    );
  }

  const overall = report.overallScore ?? 0;
  const confidence = report.confidenceAvg ?? 0;

  return (
    <div style={{ minHeight: "100vh", background: G.bg, color: G.text, fontFamily: G.font }}>
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "3rem 1.5rem 5rem" }}>

        {/* ── Header ── */}
        <div style={{ textAlign: "center", marginBottom: "3rem" }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.accent, letterSpacing: "0.25em", textTransform: "uppercase", marginBottom: "0.7rem" }}>
            RoundZero · Session Report
          </div>
          <h1 style={{ fontSize: "clamp(2rem, 5vw, 3.2rem)", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "0.4rem" }}>
            Performance <span style={{ color: G.accent }}>Report</span>
          </h1>
          <p style={{ color: G.muted, fontFamily: G.mono, fontSize: "0.62rem", letterSpacing: "0.08em" }}>
            SESSION {sessionId.toUpperCase()}
          </p>
        </div>

        {/* ── Score strip ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "1rem", marginBottom: "2.5rem" }}>
          {[
            { label: "Overall", value: overall, color: scoreColor(overall), unit: "/100" },
            { label: "Confidence", value: confidence, color: G.accent2, unit: "%" },
            { label: "Fillers", value: report.totalFillers ?? 0, color: G.accent3, unit: "", noRing: true },
            { label: "Questions", value: report.questionsAnswered ?? 0, color: "#818cf8", unit: "/5", noRing: true },
          ].map(({ label, value, color, unit, noRing }) => (
            <div key={label} style={{
              background: G.surface, border: `1px solid ${G.border}`,
              padding: "1.5rem 1rem", textAlign: "center", position: "relative", overflow: "hidden",
            }}>
              <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.18em", marginBottom: "0.7rem" }}>
                {label}
              </div>
              {noRing ? (
                <div style={{ fontSize: "2.5rem", fontWeight: 800, color }}>{value}<small style={{ fontSize: "0.9rem", color: G.muted }}>{unit}</small></div>
              ) : (
                <>
                  <ScoreRing value={value} color={color} size={72} />
                  <div style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted, marginTop: "0.4rem" }}>{unit}</div>
                </>
              )}
              <div style={{ position: "absolute", bottom: 0, left: 0, height: 3, width: noRing ? "100%" : `${Math.min(100, value)}%`, background: color, opacity: 0.7, transition: "width 1s ease" }} />
            </div>
          ))}
        </div>

        {/* ── Score Trajectory ── */}
        {report.scoresByQuestion && report.scoresByQuestion.length > 1 && (
          <div style={{
            background: G.surface, border: `1px solid ${G.border}`,
            padding: "1.2rem 1.5rem", marginBottom: "2rem",
            display: "flex", alignItems: "center", gap: "2rem", flexWrap: "wrap",
          }}>
            <div>
              <div style={{ fontFamily: G.mono, fontSize: "0.55rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.18em", marginBottom: "0.5rem" }}>
                Score Trajectory
              </div>
              <ScoreTrendChart scores={report.scoresByQuestion} trend={report.scoreTrend} />
            </div>
            {report.scoreTrendNote && (
              <p style={{ fontSize: "0.82rem", color: G.muted, flex: 1, minWidth: 180, margin: 0, lineHeight: 1.6 }}>
                {report.scoreTrendNote}
              </p>
            )}
          </div>
        )}

        {/* ── Coach's summary ── */}
        <div style={{
          background: G.surface, border: `1px solid ${G.border}`,
          padding: "2rem 2.5rem", marginBottom: "2rem",
          borderLeft: `3px solid ${G.accent}`,
        }}>
          <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: G.accent, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "0.9rem" }}>
            Coach's Analysis
          </div>
          <p style={{ fontSize: "1rem", lineHeight: 1.75, color: G.text }}>{report.summary}</p>
        </div>

        {/* ── Strengths + Weaknesses ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.2rem", marginBottom: "2.5rem" }}>
          <div style={{ background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.2)", padding: "1.5rem" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: "#10b981", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "1rem" }}>
              Key Strengths
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {report.strengths.map((s, i) => (
                <li key={i} style={{ display: "flex", gap: "0.6rem", fontSize: "0.88rem", lineHeight: 1.5 }}>
                  <span style={{ color: "#10b981", fontWeight: 700, flexShrink: 0 }}>✓</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
          <div style={{ background: "rgba(244,63,94,0.05)", border: "1px solid rgba(244,63,94,0.2)", padding: "1.5rem" }}>
            <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: "#f43f5e", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "1rem" }}>
              Areas to Improve
            </div>
            <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {report.weaknesses.map((w, i) => (
                <li key={i} style={{ display: "flex", gap: "0.6rem", fontSize: "0.88rem", lineHeight: 1.5 }}>
                  <span style={{ color: "#f43f5e", fontWeight: 700, flexShrink: 0 }}>→</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* ── Per-question breakdown ── */}
        {report.breakdown.length > 0 && (
          <>
            <div style={{ fontFamily: G.mono, fontSize: "0.58rem", color: G.muted, textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1rem" }}>
              Detailed Breakdown
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {report.breakdown.map((item, idx) => {
                const sc = item.score ?? 0;
                const col = scoreColor(sc);
                return (
                  <div key={idx} style={{
                    background: G.surface, border: `1px solid ${G.border}`,
                    padding: "1.5rem", position: "relative", overflow: "hidden",
                  }}>
                    {/* Score bar at bottom */}
                    <div style={{ position: "absolute", bottom: 0, left: 0, height: 3, width: `${sc}%`, background: col }} />

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.8rem" }}>
                      <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
                        <span style={{
                          fontFamily: G.mono, fontSize: "0.55rem", color: G.muted,
                          background: G.surface2, border: `1px solid ${G.border}`,
                          padding: "2px 7px", letterSpacing: "0.1em", textTransform: "uppercase", flexShrink: 0,
                        }}>Q{idx + 1}</span>
                        {item.topic && (
                          <span style={{
                            fontFamily: G.mono, fontSize: "0.52rem", color: "#818cf8",
                            background: "rgba(129,140,248,0.1)", border: "1px solid rgba(129,140,248,0.25)",
                            padding: "2px 8px", letterSpacing: "0.08em", textTransform: "uppercase", flexShrink: 0,
                          }}>{item.topic}</span>
                        )}
                        {item.correctnessPercent !== undefined && item.correctnessPercent > 0 && (
                          <span style={{
                            fontFamily: G.mono, fontSize: "0.52rem",
                            color: scoreColor(item.correctnessPercent),
                            background: `${scoreColor(item.correctnessPercent)}14`,
                            border: `1px solid ${scoreColor(item.correctnessPercent)}30`,
                            padding: "2px 8px", letterSpacing: "0.08em", flexShrink: 0,
                          }}>{item.correctnessPercent}% correct</span>
                        )}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexShrink: 0 }}>
                        <ScoreRing value={sc} color={col} size={44} />
                        <span style={{ fontFamily: G.mono, fontSize: "0.6rem", color: G.muted }}>%</span>
                      </div>
                    </div>

                    <p style={{ fontWeight: 700, fontSize: "0.95rem", marginBottom: "0.7rem", lineHeight: 1.4 }}>
                      {item.q}
                    </p>

                    <div style={{
                      fontSize: "0.82rem", color: G.muted, lineHeight: 1.65,
                      padding: "0.8rem 1rem", background: "rgba(0,0,0,0.18)",
                      borderLeft: `2px solid ${col}40`,
                    }}>
                      {item.feedback}
                    </div>

                    {(item.whatWasRight || item.whatWasWrong) && (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", marginTop: "0.8rem" }}>
                        {item.whatWasRight && (
                          <div style={{
                            fontSize: "0.78rem", color: "#10b981", lineHeight: 1.55,
                            background: "rgba(16,185,129,0.05)", border: "1px solid rgba(16,185,129,0.15)",
                            padding: "0.5rem 0.7rem",
                          }}>
                            <span style={{ fontFamily: G.mono, fontSize: "0.5rem", letterSpacing: "0.1em", display: "block", marginBottom: "0.3rem", opacity: 0.7 }}>WHAT WORKED</span>
                            {item.whatWasRight}
                          </div>
                        )}
                        {item.whatWasWrong && (
                          <div style={{
                            fontSize: "0.78rem", color: "#f59e0b", lineHeight: 1.55,
                            background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.15)",
                            padding: "0.5rem 0.7rem",
                          }}>
                            <span style={{ fontFamily: G.mono, fontSize: "0.5rem", letterSpacing: "0.1em", display: "block", marginBottom: "0.3rem", opacity: 0.7 }}>WHAT TO FIX</span>
                            {item.whatWasWrong}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* ── CTA ── */}
        <div style={{ textAlign: "center", marginTop: "3.5rem" }}>
          <Btn onClick={onRestart}>Start New Interview →</Btn>
          <p style={{ color: G.muted, fontFamily: G.mono, fontSize: "0.58rem", marginTop: "1rem", letterSpacing: "0.05em" }}>
            Your progress is saved. Each session builds on the last.
          </p>
        </div>

      </div>
    </div>
  );
}
