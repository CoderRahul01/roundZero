import React from "react";

interface State { error: Error | null }

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: "100vh",
          background: "#050508",
          color: "#e8e8f0",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
          fontFamily: "'DM Mono', monospace",
          textAlign: "center",
        }}>
          <div style={{ color: "#f43f5e", fontSize: "1.2rem", marginBottom: "1rem" }}>
            ⚠ Application Error
          </div>
          <div style={{ color: "#5a5a78", fontSize: "0.85rem", maxWidth: 500 }}>
            {this.state.error.message}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: "2rem",
              padding: "0.75rem 2rem",
              background: "rgba(110,231,183,0.1)",
              border: "1px solid #6ee7b7",
              color: "#6ee7b7",
              fontFamily: "inherit",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            Reload
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
