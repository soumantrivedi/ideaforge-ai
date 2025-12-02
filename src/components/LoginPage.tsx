import { useState, useEffect } from "react";
import { LogIn, Mail, Lock, AlertCircle, Building2 } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

interface LoginPageProps {
  onLoginSuccess?: (user: any) => void;
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { login, loginWithMcKinsey, handleMcKinseyCallback } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSSOLoading, setIsSSOLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ssoError, setSSOError] = useState<string | null>(null);

  // Handle OAuth callback on component mount
  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Check if we're on the callback route
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get("code");
      const state = urlParams.get("state");
      const error = urlParams.get("error");
      const errorDescription = urlParams.get("error_description");

      // If there's an OAuth error in the URL
      if (error) {
        setSSOError(errorDescription || `Authentication failed: ${error}`);
        // Clean up URL
        window.history.replaceState(
          {},
          document.title,
          window.location.pathname,
        );
        return;
      }

      // If we have both code and state, this is a callback
      if (code && state) {
        setIsSSOLoading(true);
        setSSOError(null);

        try {
          await handleMcKinseyCallback(code, state);
          // Clean up URL after successful callback
          window.history.replaceState(
            {},
            document.title,
            window.location.pathname,
          );
          onLoginSuccess?.({ sso: true });
        } catch (err) {
          setSSOError(
            err instanceof Error
              ? err.message
              : "McKinsey SSO authentication failed",
          );
          // Clean up URL even on error
          window.history.replaceState(
            {},
            document.title,
            window.location.pathname,
          );
        } finally {
          setIsSSOLoading(false);
        }
      }
    };

    handleOAuthCallback();
  }, [handleMcKinseyCallback, onLoginSuccess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await login(email, password);
      onLoginSuccess?.({ email, password }); // Optional callback
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMcKinseyLogin = async () => {
    setIsSSOLoading(true);
    setSSOError(null);

    try {
      await loginWithMcKinsey();
      // The loginWithMcKinsey function will redirect to McKinsey, so we won't reach here
    } catch (err) {
      setSSOError(
        err instanceof Error ? err.message : "Failed to initiate McKinsey SSO",
      );
      setIsSSOLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ backgroundColor: "var(--bg-secondary)" }}
    >
      <div className="max-w-md w-full mx-4">
        <div
          className="rounded-lg border shadow-sm p-8"
          style={{
            backgroundColor: "var(--card-bg)",
            borderColor: "var(--border-color)",
            color: "var(--text-primary)",
          }}
        >
          <div className="text-center mb-8">
            <h1
              className="text-2xl font-semibold mb-1 tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              IdeaForge AI
            </h1>
            <p
              className="text-sm mb-6"
              style={{ color: "var(--text-secondary)" }}
            >
              Agentic Product Management Platform
            </p>
            <h2
              className="text-xl font-medium mb-2"
              style={{ color: "var(--text-primary)" }}
            >
              Welcome Back
            </h2>
            <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
              Sign in to your account
            </p>
          </div>

          {/* Loading indicator for SSO callback */}
          {isSSOLoading && (
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <p className="text-sm text-blue-700">
                Completing McKinsey SSO authentication...
              </p>
            </div>
          )}

          {/* Error display for email/password login */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Error display for McKinsey SSO */}
          {ssoError && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-700 mb-1">
                  McKinsey SSO Error
                </p>
                <p className="text-sm text-red-600">{ssoError}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium mb-2"
                style={{ color: "var(--text-primary)" }}
              >
                Email Address
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <Mail className="w-5 h-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium mb-2"
                style={{ color: "var(--text-primary)" }}
              >
                Password
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2">
                  <Lock className="w-5 h-5 text-gray-400" />
                </div>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || isSSOLoading}
              className="w-full py-3 px-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: "var(--button-primary-bg)",
                color: "var(--button-primary-text)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor =
                  "var(--button-primary-hover)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor =
                  "var(--button-primary-bg)";
              }}
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          {/* Divider */}
          <div className="mt-6 mb-6 flex items-center">
            <div
              className="flex-1 border-t"
              style={{ borderColor: "var(--border-color)" }}
            ></div>
            <span
              className="px-4 text-sm"
              style={{ color: "var(--text-secondary)" }}
            >
              or
            </span>
            <div
              className="flex-1 border-t"
              style={{ borderColor: "var(--border-color)" }}
            ></div>
          </div>

          {/* McKinsey SSO Button */}
          <button
            type="button"
            onClick={handleMcKinseyLogin}
            disabled={isLoading || isSSOLoading}
            className="w-full py-3 px-4 font-medium rounded-md border-2 focus:outline-none focus:ring-2 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            style={{
              borderColor: "var(--border-color)",
              backgroundColor: "var(--card-bg)",
              color: "var(--text-primary)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = "var(--bg-secondary)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "var(--card-bg)";
            }}
          >
            <Building2 className="w-5 h-5" />
            {isSSOLoading
              ? "Redirecting to McKinsey..."
              : "Sign in with McKinsey SSO"}
          </button>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-900 font-medium mb-2">
              Demo Accounts (Password: password123):
            </p>
            <div className="text-xs text-blue-700 space-y-1">
              <div className="mb-2">
                <p className="font-semibold text-blue-900 mb-1">
                  Admin Accounts:
                </p>
                <p>• admin@ideaforge.ai</p>
                <p>• admin2@ideaforge.ai</p>
                <p>• admin3@ideaforge.ai</p>
              </div>
              <div>
                <p className="font-semibold text-blue-900 mb-1">
                  User Accounts:
                </p>
                <p>• user1@ideaforge.ai</p>
                <p>• user2@ideaforge.ai</p>
                <p>• user3@ideaforge.ai</p>
                <p>• user4@ideaforge.ai</p>
                <p>• user5@ideaforge.ai</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
