import React, { useEffect, useState } from "react";
import { G } from "../theme";
import { Label, Input, Btn, Spinner, GhostBtn } from "../components/UI";
import { startSession, prepareSession, fetchProfile, updateProfile } from "../api";
import { LiveSessionConfig } from "../types";
import { useScreenShare } from "../services/screenShare/useScreenShare";
import {
  AuthUser,
  getCurrentUser,
  isLegacyDevAuthEnabled,
  isNeonAuthConfigured,
  signInWithEmail,
  signOut as signOutAuth,
  signUpWithEmail,
} from "../auth";

const TOPICS = [
  "Data Structures & Algorithms",
  "System Design",
  "Behavioral / HR",
  "JavaScript / Frontend",
  "Python / Backend",
  "Database & SQL",
  "Machine Learning",
  "Operating Systems",
];

const ROLES = [
  "SDE-1 (Junior)",
  "SDE-2 (Mid)",
  "SDE-3 (Senior)",
  "Frontend Engineer",
  "Backend Engineer",
  "Full Stack",
  "Data Scientist",
  "ML Engineer",
  "Product Manager",
];

export function SetupScreen({ onStart }: { onStart: (cfg: LiveSessionConfig) => void }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [topics, setTopics] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");
  const [mode, setMode] = useState<"buddy" | "strict">("buddy");
  const [videoSource, setVideoSource] = useState<"camera" | "screen" | "none">("camera");
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [authReady, setAuthReady] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);

  const { stream: screenStream, start: startScreenCapture } = useScreenShare();

  const neonConfigured = isNeonAuthConfigured();
  const legacyAuthEnabled = isLegacyDevAuthEnabled();
  const authConfigured = neonConfigured || legacyAuthEnabled;

  useEffect(() => {
    let mounted = true;
    (async () => {
      const user = await getCurrentUser();
      if (!mounted) return;
      setAuthUser(user);
      
      if (user) {
        try {
          const profile = await fetchProfile();
          if (profile.name) setName(profile.name);
        } catch (e) {
          console.warn("Could not fetch profile", e);
        }
      }
      
      setAuthReady(true);
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const toggleTopic = (t: string) =>
    setTopics((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  const handleAuthSubmit = async () => {
    setAuthError(null);
    if (!authEmail.trim() || !authPassword.trim()) {
      setAuthError("Email and password are required.");
      return;
    }

    setAuthLoading(true);
    try {
      const result =
        authMode === "signin"
          ? await signInWithEmail(authEmail.trim(), authPassword)
          : await signUpWithEmail(authEmail.trim(), authPassword);

      if (!result.ok) {
        setAuthError(result.error || "Authentication failed.");
        return;
      }

      if (!result.user) {
        setAuthError(
          authMode === "signup"
            ? "Account created, but no active session yet. Verify your email if required, then sign in."
            : "Signed in, but no active session token was returned."
        );
        return;
      }

      setAuthUser(result.user);
      setAuthPassword("");

      // Fetch profile after auth
      try {
        const profile = await fetchProfile();
        if (profile.name) setName(profile.name);
      } catch (e) {
        console.warn("Could not fetch profile details", e);
      }
    } finally {
      setAuthLoading(false);
    }
  };

  const handleAuthSignOut = async () => {
    await signOutAuth();
    setAuthUser(null);
    setAuthPassword("");
    setAuthError(null);
    setAuthMode("signin");
  };


  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Save profile name if it exists and changed
      try {
        await updateProfile({ name });
      } catch (e) {
        console.warn("Failed to update profile", e);
      }

      // 2. Prepare the session (generates custom question bank via LLM)
      const payload = {
        user_id: authUser?.id,
        name,
        role,
        topics,
        difficulty,
        mode,
      };

      const prepData = await prepareSession(payload);
      
      // 3. Handle Screen Capture if needed (Phase 5)
      let externalStream = null;
      if (videoSource === 'screen') {
        try {
          setLoading(true);
          setError("Please select the window/screen you want to share...");
          externalStream = await startScreenCapture();
          setError(null);
        } catch (err) {
          throw new Error("Screen share was canceled or failed.");
        }
      }

      // 4. Start the session using the pre-prepared session_id
      const data = await startSession(payload, prepData.session_id);

      onStart({
        name,
        role,
        topics,
        difficulty,
        mode,
        videoSource,
        externalStream,
        ...data,
      });
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Error starting interview. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: G.bg,
        fontFamily: G.font,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background grid */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage: `linear-gradient(${G.border} 1px, transparent 1px), linear-gradient(90deg, ${G.border} 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
          opacity: 0.3,
          pointerEvents: "none",
        }}
      />
      {/* Glow */}
      <div
        style={{
          position: "fixed",
          top: "-20%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "600px",
          height: "400px",
          background: `radial-gradient(ellipse, rgba(110,231,183,0.08) 0%, transparent 70%)`,
          pointerEvents: "none",
        }}
      />

      <div style={{ width: "100%", maxWidth: "560px", position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "3rem" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.6rem",
              background: G.surface,
              border: `1px solid ${G.border}`,
              padding: "0.5rem 1.2rem",
              borderRadius: "2px",
              marginBottom: "1.5rem",
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: G.accent,
                boxShadow: `0 0 8px ${G.accent}`,
              }}
            />
            <span
              style={{
                fontFamily: G.mono,
                fontSize: "0.7rem",
                letterSpacing: "0.2em",
                color: G.muted,
                textTransform: "uppercase",
              }}
            >
              Interview Simulator
            </span>
          </div>
          <h1 style={{ fontSize: "3.5rem", fontWeight: 800, color: G.text, letterSpacing: "-0.04em", lineHeight: 1 }}>
            Round<span style={{ color: G.accent }}>Zero</span>
          </h1>
          <p style={{ color: G.muted, marginTop: "0.7rem", fontSize: "0.95rem" }}>
            Your AI interviewer. Practice before the real thing.
          </p>
        </div>

        {/* Card */}
        <div style={{ background: G.surface, border: `1px solid ${G.border}`, padding: "2.5rem" }}>
          {/* Error banner */}
          {error && (
            <div
              style={{
                background: "rgba(244,63,94,0.08)",
                border: "1px solid rgba(244,63,94,0.3)",
                color: "#f43f5e",
                padding: "0.75rem 1rem",
                marginBottom: "1rem",
                fontFamily: G.font,
                fontSize: "0.9rem",
              }}
            >
              {error}
            </div>
          )}

          {!authConfigured && (
            <div
              style={{
                background: "rgba(245,158,11,0.08)",
                border: `1px solid rgba(245,158,11,0.35)`,
                color: G.accent2,
                padding: "0.9rem 1rem",
                fontSize: "0.85rem",
                lineHeight: 1.5,
              }}
            >
              Neon Auth is not configured yet. Add <code>REACT_APP_NEON_AUTH_URL</code> to <code>frontend/.env</code>{" "}
              to enable sign-in.
            </div>
          )}

          {authConfigured && !authReady && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.65rem",
                color: G.muted,
                fontSize: "0.85rem",
              }}
            >
              <Spinner /> Loading authentication session...
            </div>
          )}

          {authConfigured && authReady && !authUser && (
            <div>
              <Label style={{ marginBottom: "0.75rem" }}>Authenticate to continue</Label>

              {legacyAuthEnabled && !neonConfigured && (
                <div
                  style={{
                    background: "rgba(245,158,11,0.08)",
                    border: `1px solid rgba(245,158,11,0.35)`,
                    color: G.accent2,
                    padding: "0.75rem 0.9rem",
                    marginBottom: "0.9rem",
                    fontSize: "0.8rem",
                  }}
                >
                  Running in legacy local auth mode.
                </div>
              )}

              {authError && (
                <div
                  style={{
                    background: "rgba(244,63,94,0.08)",
                    border: "1px solid rgba(244,63,94,0.3)",
                    color: "#f43f5e",
                    padding: "0.75rem 1rem",
                    marginBottom: "0.85rem",
                    fontFamily: G.font,
                    fontSize: "0.82rem",
                  }}
                >
                  {authError}
                </div>
              )}

              <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
                <button
                  onClick={() => setAuthMode("signin")}
                  style={{
                    flex: 1,
                    padding: "0.6rem",
                    background: authMode === "signin" ? "rgba(110,231,183,0.12)" : G.surface2,
                    border: `1px solid ${authMode === "signin" ? G.accent : G.border}`,
                    color: authMode === "signin" ? G.accent : G.muted,
                    fontFamily: G.font,
                    cursor: "pointer",
                    fontSize: "0.82rem",
                  }}
                >
                  Sign in
                </button>
                <button
                  onClick={() => setAuthMode("signup")}
                  style={{
                    flex: 1,
                    padding: "0.6rem",
                    background: authMode === "signup" ? "rgba(110,231,183,0.12)" : G.surface2,
                    border: `1px solid ${authMode === "signup" ? G.accent : G.border}`,
                    color: authMode === "signup" ? G.accent : G.muted,
                    fontFamily: G.font,
                    cursor: "pointer",
                    fontSize: "0.82rem",
                  }}
                >
                  Create account
                </button>
              </div>

              <Label>Email</Label>
              <Input
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="you@example.com"
                type="email"
              />

              <Label style={{ marginTop: "1rem" }}>Password</Label>
              <Input
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                type="password"
              />

              <Btn
                onClick={handleAuthSubmit}
                disabled={authLoading || !authEmail.trim() || !authPassword.trim()}
                style={{ marginTop: "1.2rem" }}
              >
                {authLoading ? (
                  <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", justifyContent: "center" }}>
                    <Spinner /> Authenticating...
                  </span>
                ) : authMode === "signin" ? (
                  "Sign in"
                ) : (
                  "Create account"
                )}
              </Btn>
            </div>
          )}

          {authConfigured && authReady && authUser && (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "1.2rem",
                  gap: "1rem",
                  flexWrap: "wrap",
                  border: `1px solid ${G.border}`,
                  background: G.surface2,
                  padding: "0.75rem 0.9rem",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
                  <span style={{ color: G.muted, fontSize: "0.72rem", fontFamily: G.mono, letterSpacing: "0.08em" }}>
                    AUTHENTICATED AS
                  </span>
                  <span style={{ color: G.text, fontSize: "0.84rem" }}>{authUser.email || authUser.id}</span>
                </div>
                <GhostBtn onClick={handleAuthSignOut}>Sign out</GhostBtn>
              </div>

              {/* Step indicator */}
              <div style={{ display: "flex", gap: "0.5rem", marginBottom: "2rem" }}>
                {[1, 2, 3].map((s) => (
                  <div
                    key={s}
                    style={{
                      flex: 1,
                      height: 3,
                      background: step >= s ? G.accent : G.border,
                      transition: "background 0.3s",
                      borderRadius: "2px",
                    }}
                  />
                ))}
              </div>

              {step === 1 && (
                <div>
                  <Label>Your name</Label>
                  <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Arjun Sharma" />
                  <Label style={{ marginTop: "1.5rem" }}>Target role</Label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginTop: "0.5rem" }}>
                    {ROLES.map((r) => (
                      <button
                        key={r}
                        onClick={() => setRole(r)}
                        style={{
                          padding: "0.6rem 0.8rem",
                          background: role === r ? "rgba(110,231,183,0.1)" : G.surface2,
                          border: `1px solid ${role === r ? G.accent : G.border}`,
                          color: role === r ? G.accent : G.muted,
                          fontFamily: G.font,
                          fontSize: "0.78rem",
                          cursor: "pointer",
                          textAlign: "left",
                          transition: "all 0.15s",
                        }}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                  <Btn disabled={!name || !role} onClick={() => setStep(2)} style={{ marginTop: "2rem" }}>
                    Continue →
                  </Btn>
                </div>
              )}

              {step === 2 && (
                <div>
                  <Label>
                    Topics to cover <span style={{ color: G.muted, fontWeight: 400 }}>(pick up to 3)</span>
                  </Label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.8rem" }}>
                    {TOPICS.map((t) => (
                      <button
                        key={t}
                        onClick={() => toggleTopic(t)}
                        disabled={!topics.includes(t) && topics.length >= 3}
                        style={{
                          padding: "0.5rem 1rem",
                          background: topics.includes(t) ? "rgba(110,231,183,0.1)" : G.surface2,
                          border: `1px solid ${topics.includes(t) ? G.accent : G.border}`,
                          color: topics.includes(t) ? G.accent : G.muted,
                          fontFamily: G.font,
                          fontSize: "0.8rem",
                          cursor: "pointer",
                          borderRadius: "2px",
                          transition: "all 0.15s",
                          opacity: !topics.includes(t) && topics.length >= 3 ? 0.4 : 1,
                        }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>

                  <Label style={{ marginTop: "2rem" }}>Difficulty</Label>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                    {["easy", "medium", "hard"].map((d) => (
                      <button
                        key={d}
                        onClick={() => setDifficulty(d as "easy" | "medium" | "hard")}
                        style={{
                          flex: 1,
                          padding: "0.7rem",
                          background:
                            difficulty === d
                              ? d === "easy"
                                ? "rgba(110,231,183,0.1)"
                                : d === "medium"
                                ? "rgba(245,158,11,0.1)"
                                : "rgba(244,63,94,0.1)"
                              : G.surface2,
                          border: `1px solid ${
                            difficulty === d
                              ? d === "easy"
                                ? G.accent
                                : d === "medium"
                                ? G.accent2
                                : G.accent3
                              : G.border
                          }`,
                          color:
                            difficulty === d
                              ? d === "easy"
                                ? G.accent
                                : d === "medium"
                                ? G.accent2
                                : G.accent3
                              : G.muted,
                          fontFamily: G.font,
                          fontSize: "0.85rem",
                          cursor: "pointer",
                          textTransform: "capitalize",
                          transition: "all 0.15s",
                        }}
                      >
                        {d}
                      </button>
                    ))}
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "2rem" }}>
                    <GhostBtn onClick={() => setStep(1)}>← Back</GhostBtn>
                    <Btn disabled={topics.length === 0} onClick={() => setStep(3)} style={{ flex: 1 }}>
                      Continue →
                    </Btn>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div>
                  <Label>Interview mode</Label>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginTop: "0.8rem" }}>
                    {[
                      {
                        key: "buddy",
                        label: "🤝 Buddy Mode",
                        desc: "Friendly, encouraging. Gets easier on low confidence.",
                      },
                      {
                        key: "strict",
                        label: "🎯 Strict Mode",
                        desc: "Cold, formal. FAANG-style pressure. No mercy.",
                      },
                    ].map(({ key, label, desc }) => (
                      <button
                        key={key}
                        onClick={() => setMode(key as "buddy" | "strict")}
                        style={{
                          padding: "1.2rem",
                          background: mode === key ? "rgba(110,231,183,0.06)" : G.surface2,
                          border: `1px solid ${mode === key ? G.accent : G.border}`,
                          color: G.text,
                          fontFamily: G.font,
                          cursor: "pointer",
                          textAlign: "left",
                          transition: "all 0.2s",
                        }}
                      >
                        <div style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "0.4rem" }}>{label}</div>
                        <div style={{ fontSize: "0.75rem", color: G.muted, lineHeight: 1.4 }}>{desc}</div>
                      </button>
                    ))}
                  </div>

                  <Label style={{ marginTop: "2rem" }}>Vision (Optional)</Label>
                  <p style={{ color: G.muted, fontSize: "0.75rem", marginBottom: "0.8rem", lineHeight: 1.4 }}>
                    Allow the AI to see your face or screen for better context and non-verbal feedback. 
                    Processed securely at 1 frame every 5 seconds.
                  </p>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem" }}>
                    {[
                      { id: "camera", label: "Camera" },
                      { id: "screen", label: "Screen Share" },
                      { id: "none", label: "Audio Only" },
                    ].map((vs) => (
                      <button
                        key={vs.id}
                        onClick={() => setVideoSource(vs.id as any)}
                        style={{
                          padding: "0.8rem",
                          background: videoSource === vs.id ? "rgba(110,231,183,0.1)" : G.surface2,
                          border: `1px solid ${videoSource === vs.id ? G.accent : G.border}`,
                          color: videoSource === vs.id ? G.accent : G.muted,
                          fontFamily: G.font,
                          fontSize: "0.82rem",
                          cursor: "pointer",
                          transition: "all 0.15s",
                          textAlign: "center"
                        }}
                      >
                       {vs.label}
                      </button>
                    ))}
                  </div>

                  <div style={{ background: G.surface2, border: `1px solid ${G.border}`, padding: "1.2rem", marginTop: "2rem" }}>
                    <div
                      style={{
                        fontFamily: G.mono,
                        fontSize: "0.65rem",
                        color: G.accent,
                        letterSpacing: "0.15em",
                        textTransform: "uppercase",
                        marginBottom: "0.8rem",
                      }}
                    >
                      Session Summary
                    </div>
                    {[
                      ["Candidate", name],
                      ["Role", role],
                      ["Topics", topics.join(", ")],
                      ["Difficulty", difficulty],
                      ["Mode", mode],
                      ["Vision", videoSource === 'none' ? 'Audio Only' : videoSource],
                    ].map(([k, v]) => (
                      <div
                        key={k}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: "0.82rem",
                          marginBottom: "0.4rem",
                        }}
                      >
                        <span style={{ color: G.muted }}>{k}</span>
                        <span style={{ color: G.text, textTransform: "capitalize" }}>{v}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "1.5rem" }}>
                    <GhostBtn onClick={() => setStep(2)}>← Back</GhostBtn>
                    <Btn onClick={handleStart} style={{ flex: 1 }}>
                      {loading ? (
                        <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", justifyContent: "center" }}>
                          <Spinner /> Preparing your session...
                        </span>
                      ) : (
                        "Start Interview →"
                      )}
                    </Btn>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        <p style={{ textAlign: "center", marginTop: "1.5rem", color: G.muted, fontSize: "0.75rem", fontFamily: G.mono }}>
          Powered by Gemini Live API · Google ADK · Pinecone · Neon
        </p>
      </div>
    </div>
  );
}
