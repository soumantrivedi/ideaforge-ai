import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { apiFetch, setUnauthorizedHandler } from "../lib/api-client";
import { clearAllSessionStorage } from "../lib/session-storage";

interface User {
  id: string;
  email: string;
  full_name?: string;
  tenant_id: string;
  tenant_name: string;
  persona: string;
  avatar_url?: string;
  mckinsey_subject?: string; // Present if user logged in via McKinsey SSO
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
  // McKinsey SSO methods
  loginWithMcKinsey: () => Promise<void>;
  handleMcKinseyCallback: (code: string, state: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

import { getValidatedApiUrl } from "../lib/runtime-config";
const API_URL = getValidatedApiUrl();

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedToken = localStorage.getItem("auth_token");
    const storedUserId = localStorage.getItem("user_id");
    const storedTenantId = localStorage.getItem("tenant_id");

    if (storedToken && storedUserId) {
      setToken(storedToken);
      // Set basic user info from localStorage immediately
      setUser({
        id: storedUserId,
        email: "", // Will be fetched
        tenant_id: storedTenantId || "",
        tenant_name: "",
        persona: "product_manager",
      });
      fetchUserInfo(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const handleUnauthorized = () => {
    // Clear all auth data
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_id");
    localStorage.removeItem("tenant_id");
    // Clear session storage (chat history, app state, etc.)
    clearAllSessionStorage();
    setToken(null);
    setUser(null);
    setIsLoading(false); // Ensure loading state is cleared so login page shows
  };

  useEffect(() => {
    // Register unauthorized handler
    setUnauthorizedHandler(handleUnauthorized);

    return () => {
      setUnauthorizedHandler(null);
    };
  }, []);

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await apiFetch("/api/auth/me", {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Update localStorage with latest info
        if (userData.id) localStorage.setItem("user_id", userData.id);
        if (userData.tenant_id)
          localStorage.setItem("tenant_id", userData.tenant_id);
      } else {
        // Token invalid, clear storage (silently - this is expected after pod restart)
        handleUnauthorized();
      }
    } catch (error) {
      // Only log non-401 errors (401 is expected when token expires/backend restarts)
      if (error instanceof Error && !error.message.includes("Unauthorized")) {
        console.error("Failed to fetch user info:", error);
      }
      // handleUnauthorized is already called by apiFetch for 401, but call it here too for other errors
      handleUnauthorized();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await apiFetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }

    localStorage.setItem("auth_token", data.token);
    localStorage.setItem("user_id", data.user_id);
    localStorage.setItem("tenant_id", data.tenant_id);

    setToken(data.token);

    // Set user immediately from login response
    setUser({
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      tenant_id: data.tenant_id,
      tenant_name: data.tenant_name,
      persona: "product_manager", // Will be fetched from /api/auth/me
    });

    // Fetch full user info to get complete profile
    try {
      await fetchUserInfo(data.token);
    } catch (error) {
      console.error("Failed to fetch user info after login:", error);
      // Continue anyway, we have basic user info from login
    }
  };

  const logout = async () => {
    try {
      // Detect if user logged in via McKinsey SSO
      const isMcKinseyUser =
        user?.mckinsey_subject !== undefined && user?.mckinsey_subject !== null;

      if (isMcKinseyUser) {
        // McKinsey SSO logout flow
        const response = await apiFetch("/api/auth/mckinsey/logout", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (response.ok) {
          const data = await response.json();

          // Clear session storage and local auth data first
          clearAllSessionStorage();
          handleUnauthorized();

          // Redirect to McKinsey logout URL for RP-initiated logout
          if (data.logout_url) {
            window.location.href = data.logout_url;
            return; // Don't continue execution after redirect
          }
        } else {
          // If McKinsey logout fails, still clear local session
          console.error("McKinsey logout failed, clearing local session");
        }
      } else {
        // Regular password-based logout flow
        await apiFetch("/api/auth/logout", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
      }
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Clear session storage before clearing auth
      // (only reached if not redirected to McKinsey logout)
      clearAllSessionStorage();
      handleUnauthorized();
    }
  };

  const loginWithMcKinsey = async () => {
    try {
      // Call the McKinsey authorize endpoint to get the authorization URL
      const response = await apiFetch("/api/auth/mckinsey/authorize", {
        method: "GET",
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to initiate McKinsey SSO");
      }

      const data = await response.json();

      // Store the state in sessionStorage for validation in callback
      if (data.state) {
        sessionStorage.setItem("mckinsey_oauth_state", data.state);
      }

      // Redirect to McKinsey authorization URL
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        throw new Error("No authorization URL returned");
      }
    } catch (error) {
      console.error("McKinsey SSO initiation error:", error);
      throw error;
    }
  };

  const handleMcKinseyCallback = async (code: string, state: string) => {
    try {
      // Validate state matches what we stored
      const storedState = sessionStorage.getItem("mckinsey_oauth_state");
      if (storedState && storedState !== state) {
        throw new Error("Invalid state parameter - possible CSRF attack");
      }

      // Clear the stored state
      sessionStorage.removeItem("mckinsey_oauth_state");

      // Exchange the authorization code for tokens
      const response = await apiFetch(
        `/api/auth/mckinsey/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
        {
          method: "GET",
        },
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "McKinsey SSO callback failed");
      }

      const data = await response.json();

      // Store auth data (same format as regular login)
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("user_id", data.user_id);
      localStorage.setItem("tenant_id", data.tenant_id);

      setToken(data.token);

      // Set user immediately from callback response
      setUser({
        id: data.user_id,
        email: data.email,
        full_name: data.full_name,
        tenant_id: data.tenant_id,
        tenant_name: data.tenant_name,
        persona: "product_manager",
      });

      // Fetch full user info to get complete profile
      try {
        await fetchUserInfo(data.token);
      } catch (error) {
        console.error("Failed to fetch user info after McKinsey SSO:", error);
        // Continue anyway, we have basic user info from callback
      }
    } catch (error) {
      console.error("McKinsey SSO callback error:", error);
      // Clear any partial auth state
      handleUnauthorized();
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        logout,
        isAuthenticated: !!user,
        isLoading,
        loginWithMcKinsey,
        handleMcKinseyCallback,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
