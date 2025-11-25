import { useState } from 'react';
import { LogIn, Mail, Lock, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface LoginPageProps {
  onLoginSuccess?: (user: any) => void;
}

export function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await login(email, password);
      onLoginSuccess?.({ email, password }); // Optional callback
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg-secondary)' }}>
      <div className="max-w-md w-full mx-4">
        <div className="rounded-lg border shadow-sm p-8" style={{ backgroundColor: 'var(--card-bg)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold mb-1 tracking-tight" style={{ color: 'var(--text-primary)' }}>IdeaForge AI</h1>
            <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>Agentic Product Management Platform</p>
            <h2 className="text-xl font-medium mb-2" style={{ color: 'var(--text-primary)' }}>Welcome Back</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Sign in to your account</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
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
              <label htmlFor="password" className="block text-sm font-medium mb-2" style={{ color: 'var(--text-primary)' }}>
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
              disabled={isLoading}
              className="w-full py-3 px-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ 
                backgroundColor: 'var(--button-primary-bg)', 
                color: 'var(--button-primary-text)' 
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-primary-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--button-primary-bg)';
              }}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 p-4 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-900 font-medium mb-2">Demo Accounts (Password: password123):</p>
            <div className="text-xs text-blue-700 space-y-1">
              <div className="mb-2">
                <p className="font-semibold text-blue-900 mb-1">Admin Accounts:</p>
                <p>• admin@ideaforge.ai</p>
                <p>• admin2@ideaforge.ai</p>
                <p>• admin3@ideaforge.ai</p>
              </div>
              <div>
                <p className="font-semibold text-blue-900 mb-1">User Accounts:</p>
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

