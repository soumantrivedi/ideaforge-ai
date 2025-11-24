import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiFetch, setUnauthorizedHandler } from '../lib/api-client';

interface User {
  id: string;
  email: string;
  full_name?: string;
  tenant_id: string;
  tenant_name: string;
  persona: string;
  avatar_url?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const storedToken = localStorage.getItem('auth_token');
    const storedUserId = localStorage.getItem('user_id');
    const storedTenantId = localStorage.getItem('tenant_id');
    
    if (storedToken && storedUserId) {
      setToken(storedToken);
      // Set basic user info from localStorage immediately
      setUser({
        id: storedUserId,
        email: '', // Will be fetched
        tenant_id: storedTenantId || '',
        tenant_name: '',
        persona: 'product_manager',
      });
      fetchUserInfo(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const handleUnauthorized = () => {
    // Clear all auth data
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('tenant_id');
    setToken(null);
    setUser(null);
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
      const response = await apiFetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Update localStorage with latest info
        if (userData.id) localStorage.setItem('user_id', userData.id);
        if (userData.tenant_id) localStorage.setItem('tenant_id', userData.tenant_id);
      } else {
        // Token invalid, clear storage
        handleUnauthorized();
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error);
      handleUnauthorized();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await apiFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    localStorage.setItem('auth_token', data.token);
    localStorage.setItem('user_id', data.user_id);
    localStorage.setItem('tenant_id', data.tenant_id);
    
    setToken(data.token);
    
    // Set user immediately from login response
    setUser({
      id: data.user_id,
      email: data.email,
      full_name: data.full_name,
      tenant_id: data.tenant_id,
      tenant_name: data.tenant_name,
      persona: 'product_manager', // Will be fetched from /api/auth/me
    });

    // Fetch full user info to get complete profile
    try {
      await fetchUserInfo(data.token);
    } catch (error) {
      console.error('Failed to fetch user info after login:', error);
      // Continue anyway, we have basic user info from login
    }
  };

  const logout = async () => {
    try {
      await apiFetch('/api/auth/logout', {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      handleUnauthorized();
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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

