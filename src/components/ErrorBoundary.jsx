import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Arogya Nexus ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    try {
      localStorage.removeItem("arogya_auth_token");
      localStorage.removeItem("arogya_patient_profile");
    } catch {
      // ignore
    }
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#0d1520",
            color: "#e2e8f0",
            fontFamily: "Inter, system-ui, sans-serif",
            padding: "24px",
            boxSizing: "border-box",
          }}
        >
          <div
            style={{
              maxWidth: "520px",
              width: "100%",
              background: "rgba(255, 255, 255, 0.05)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "16px",
              padding: "32px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "rgba(239, 68, 68, 0.15)",
                color: "#ef4444",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px",
              }}
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h2 style={{ fontSize: "20px", fontWeight: "700", margin: "0 0 8px", color: "#fff" }}>
              Application Recovery
            </h2>
            <p style={{ fontSize: "14px", color: "#94a3b8", margin: "0 0 24px", lineHeight: "1.5" }}>
              Arogya Nexus encountered an unexpected issue while rendering this view. You can reload or reset the session to recover safely.
            </p>
            <div style={{ display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                onClick={this.handleReload}
                style={{
                  padding: "10px 20px",
                  background: "#0ea5e9",
                  color: "#fff",
                  border: "none",
                  borderRadius: "8px",
                  fontWeight: "600",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                Reload Page
              </button>
              <button
                onClick={this.handleReset}
                style={{
                  padding: "10px 20px",
                  background: "rgba(255, 255, 255, 0.1)",
                  color: "#e2e8f0",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "8px",
                  fontWeight: "500",
                  cursor: "pointer",
                  fontSize: "14px",
                }}
              >
                Reset Session
              </button>
            </div>
            {this.state.error && (
              <details style={{ marginTop: "24px", textAlign: "left", fontSize: "12px", color: "#64748b" }}>
                <summary style={{ cursor: "pointer", color: "#94a3b8" }}>Technical Details</summary>
                <pre
                  style={{
                    marginTop: "8px",
                    padding: "12px",
                    background: "rgba(0,0,0,0.3)",
                    borderRadius: "6px",
                    overflowX: "auto",
                    whiteSpace: "pre-wrap",
                    color: "#f87171",
                  }}
                >
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
