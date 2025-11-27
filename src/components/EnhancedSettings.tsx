import { useState, useEffect } from 'react';
import { Settings, Palette, Bell, Globe, Save, Loader2, Moon, Sun, Sparkles, Bot, CheckCircle2, AlertCircle, Github, BookOpen } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { ProviderConfig } from './ProviderConfig';

import { getValidatedApiUrl } from '../lib/runtime-config';
const API_URL = getValidatedApiUrl();

export function EnhancedSettings() {
  const { theme, setTheme } = useTheme();
  const { token } = useAuth();
  const [language, setLanguage] = useState('en');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [emailNotifications, setEmailNotifications] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [apiKeysStatus, setApiKeysStatus] = useState<Record<string, boolean>>({});
  const [agnoStatus, setAgnoStatus] = useState<{
    agno_available: boolean;
    agno_enabled: boolean;
    providers_configured: boolean;
    configured_providers: string[];
    can_initialize: boolean;
    message: string;
  } | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [githubPat, setGithubPat] = useState('');
  const [atlassianUrl, setAtlassianUrl] = useState('');
  const [atlassianEmail, setAtlassianEmail] = useState('');
  const [atlassianToken, setAtlassianToken] = useState('');
  const [isSavingIntegration, setIsSavingIntegration] = useState(false);
  const [isVerifyingIntegration, setIsVerifyingIntegration] = useState<Record<string, boolean>>({});
  const [verificationStatus, setVerificationStatus] = useState<Record<string, { status: 'idle' | 'success' | 'error'; message?: string }>>({});

  const verifyIntegration = async (provider: 'github' | 'atlassian') => {
    if (!token) return;
    
    setIsVerifyingIntegration(prev => ({ ...prev, [provider]: true }));
    setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'idle' } }));
    
    try {
      let config: Record<string, string> = {};
      
      if (provider === 'github') {
        if (!githubPat.trim()) {
          setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'error', message: 'Please enter a GitHub PAT first' } }));
          setIsVerifyingIntegration(prev => ({ ...prev, [provider]: false }));
          return;
        }
        config = { pat: githubPat.trim() };
      } else if (provider === 'atlassian') {
        if (!atlassianUrl.trim() || !atlassianEmail.trim() || !atlassianToken.trim()) {
          setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'error', message: 'Please fill in all Atlassian fields first' } }));
          setIsVerifyingIntegration(prev => ({ ...prev, [provider]: false }));
          return;
        }
        config = {
          url: atlassianUrl.trim(),
          email: atlassianEmail.trim(),
          api_token: atlassianToken.trim()
        };
      }
      
      const response = await fetch(`${API_URL}/api/integrations/verify`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ provider, config }),
      });
      
      const result = await response.json();
      
      if (response.ok && result.valid) {
        setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'success', message: result.message || 'Verification successful' } }));
      } else {
        setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'error', message: result.message || 'Verification failed' } }));
      }
    } catch (error) {
      console.error(`Failed to verify ${provider}:`, error);
      setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'error', message: 'Verification failed. Please check your credentials.' } }));
    } finally {
      setIsVerifyingIntegration(prev => ({ ...prev, [provider]: false }));
    }
  };

  const saveIntegrationConfig = async (provider: 'github' | 'atlassian') => {
    if (!token) return;
    
    setIsSavingIntegration(true);
    setMessage(null);
    
    try {
      let config: Record<string, string> = {};
      
      if (provider === 'github') {
        if (!githubPat.trim()) {
          setMessage({ type: 'error', text: 'GitHub PAT is required' });
          setIsSavingIntegration(false);
          return;
        }
        config = { pat: githubPat.trim() };
      } else if (provider === 'atlassian') {
        if (!atlassianUrl.trim() || !atlassianEmail.trim() || !atlassianToken.trim()) {
          setMessage({ type: 'error', text: 'All Atlassian fields (URL, Email, API Token) are required' });
          setIsSavingIntegration(false);
          return;
        }
        config = {
          url: atlassianUrl.trim(),
          email: atlassianEmail.trim(),
          api_token: atlassianToken.trim()
        };
      }
      
      const response = await fetch(`${API_URL}/api/integrations/configure`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ provider, config }),
      });
      
      const result = await response.json();
      
      if (response.ok) {
        setMessage({ type: 'success', text: result.message || `${provider === 'github' ? 'GitHub' : 'Atlassian'} configuration saved successfully.` });
        // Clear verification status after successful save
        setVerificationStatus(prev => ({ ...prev, [provider]: { status: 'idle' } }));
      } else {
        setMessage({ type: 'error', text: result.detail || `Failed to save ${provider} configuration.` });
      }
    } catch (error) {
      console.error(`Failed to save ${provider} config:`, error);
      setMessage({ type: 'error', text: `Failed to save ${provider} configuration.` });
    } finally {
      setIsSavingIntegration(false);
    }
  };

  useEffect(() => {
    if (token) {
      loadPreferences();
      loadAPIKeysStatus();
      loadAgnoStatus();
      loadIntegrationStatus();
    }
    
    // Listen for API keys updates
    const handleApiKeysUpdate = () => {
      loadAPIKeysStatus();
      loadAgnoStatus(); // Reload Agno status when keys are updated
    };
    
    window.addEventListener('apiKeysUpdated', handleApiKeysUpdate);
    
    return () => {
      window.removeEventListener('apiKeysUpdated', handleApiKeysUpdate);
    };
  }, [token]);

  const loadIntegrationStatus = async () => {
    if (!token) return;
    
    try {
      const response = await fetch(`${API_URL}/api/integrations/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      
      if (response.ok) {
        const data = await response.json();
        const integrations = data.integrations || {};
        
        // Load existing GitHub PAT if configured
        if (integrations.github?.configured && integrations.github.metadata) {
          // Don't load the actual PAT (security), just mark as configured
          // The user will need to re-enter it if they want to change it
        }
        
        // Load existing Atlassian config if configured
        if (integrations.atlassian?.configured && integrations.atlassian.metadata) {
          const metadata = integrations.atlassian.metadata;
          setAtlassianUrl(metadata.url || '');
          setAtlassianEmail(metadata.email || '');
          // Don't load the actual token (security)
        }
      }
    } catch (error) {
      console.error('Failed to load integration status:', error);
    }
  };

  const loadPreferences = async () => {
    if (!token) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/users/preferences`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setTheme(data.theme || 'light');
        setLanguage(data.language || 'en');
        setNotificationsEnabled(data.notifications_enabled ?? true);
        setEmailNotifications(data.email_notifications ?? false);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadAPIKeysStatus = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/api-keys`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        const statusMap: Record<string, boolean> = {};
        if (Array.isArray(data.keys)) {
          data.keys.forEach((key: { provider: string; is_configured: boolean }) => {
            statusMap[key.provider] = key.is_configured;
          });
        }
        setApiKeysStatus(statusMap);
      }
    } catch (error) {
      console.error('Failed to load API keys status:', error);
    }
  };

  const loadAgnoStatus = async () => {
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/agno/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      if (response.ok) {
        const data = await response.json();
        setAgnoStatus(data);
      }
    } catch (error) {
      console.error('Failed to load Agno status:', error);
    }
  };

  const handleInitializeAgents = async () => {
    if (!token) return;

    setIsInitializing(true);
    try {
      const response = await fetch(`${API_URL}/api/agno/initialize`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setMessage({ type: 'success', text: data.message || 'Agno agents initialized successfully!' });
        await loadAgnoStatus(); // Reload status
      } else {
        setMessage({ type: 'error', text: data.message || 'Failed to initialize agents' });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to initialize agents',
      });
    } finally {
      setIsInitializing(false);
    }
  };

  const handleSave = async () => {
    if (!token) return;

    setIsSaving(true);
    setMessage(null);

    try {
      const response = await fetch(`${API_URL}/api/users/preferences`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          theme,
          language,
          notifications_enabled: notificationsEnabled,
          email_notifications: emailNotifications,
        }),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Preferences saved successfully' });
      } else {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to save preferences');
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to save preferences',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Visual Preferences */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Palette className="w-6 h-6 text-purple-600" />
          <div>
            <h3 className="text-lg font-bold text-gray-900">Visual Preferences</h3>
            <p className="text-sm text-gray-500">Customize the appearance</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Theme
            </label>
            <div className="grid grid-cols-3 gap-4">
              <button
                onClick={() => setTheme('light')}
                className={`p-4 rounded-xl border-2 transition ${
                  theme === 'light'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Sun className="w-8 h-8 mx-auto mb-2 text-yellow-600" />
                <p className="text-sm font-medium">Light</p>
              </button>
              <button
                onClick={() => setTheme('dark')}
                className={`p-4 rounded-xl border-2 transition ${
                  theme === 'dark'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Moon className="w-8 h-8 mx-auto mb-2 text-gray-800" />
                <p className="text-sm font-medium">Dark</p>
              </button>
              <button
                onClick={() => setTheme('retro')}
                className={`p-4 rounded-xl border-2 transition ${
                  theme === 'retro'
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Sparkles className="w-8 h-8 mx-auto mb-2 text-purple-600" />
                <p className="text-sm font-medium">Retro</p>
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Globe className="w-4 h-4 inline mr-2" />
              Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
            </select>
          </div>
        </div>
      </div>

      {/* Notification Preferences */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bell className="w-6 h-6 text-orange-600" />
          <div>
            <h3 className="text-lg font-bold text-gray-900">Notifications</h3>
            <p className="text-sm text-gray-500">Manage your notification preferences</p>
          </div>
        </div>

        <div className="space-y-4">
          <label className="flex items-center justify-between p-4 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition">
            <div>
              <p className="font-medium text-gray-900">Enable Notifications</p>
              <p className="text-sm text-gray-500">Receive in-app notifications</p>
            </div>
            <input
              type="checkbox"
              checked={notificationsEnabled}
              onChange={(e) => setNotificationsEnabled(e.target.checked)}
              className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
            />
          </label>

          <label className="flex items-center justify-between p-4 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100 transition">
            <div>
              <p className="font-medium text-gray-900">Email Notifications</p>
              <p className="text-sm text-gray-500">Receive notifications via email</p>
            </div>
            <input
              type="checkbox"
              checked={emailNotifications}
              onChange={(e) => setEmailNotifications(e.target.checked)}
              className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
            />
          </label>
        </div>
      </div>

      {/* AI Provider Configuration */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="w-6 h-6 text-blue-600" />
          <div>
            <h3 className="text-lg font-bold text-gray-900">AI Provider Configuration</h3>
            <p className="text-sm text-gray-500">Configure your AI API keys</p>
          </div>
        </div>
        <ProviderConfig
          onSaveConfig={(config) => {
            // Provider config is handled by ProviderConfig component
            console.log('Config saved:', config);
            // Reload API keys status and Agno status after saving
            loadAPIKeysStatus();
            loadAgnoStatus();
          }}
          configuredProviders={configuredProviders}
          apiKeysStatus={apiKeysStatus}
        />
      </div>

      {/* Integration Configuration */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <Settings className="w-6 h-6 text-indigo-600" />
          <div>
            <h3 className="text-lg font-bold text-gray-900">Integration Configuration</h3>
            <p className="text-sm text-gray-500">Configure GitHub and Atlassian integrations</p>
          </div>
        </div>

        <div className="space-y-6">
          {/* GitHub PAT */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-700">
                GitHub Personal Access Token (PAT)
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => verifyIntegration('github')}
                  disabled={isVerifyingIntegration.github || !githubPat.trim()}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  {isVerifyingIntegration.github ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify'
                  )}
                </button>
                <button
                  onClick={() => saveIntegrationConfig('github')}
                  disabled={isSavingIntegration || !githubPat.trim()}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSavingIntegration ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
            <input
              type="password"
              value={githubPat}
              placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              onChange={(e) => setGithubPat(e.target.value)}
            />
            {verificationStatus.github?.status === 'success' && (
              <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {verificationStatus.github.message}
              </p>
            )}
            {verificationStatus.github?.status === 'error' && (
              <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {verificationStatus.github.message}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Used for accessing GitHub repositories and files. Create a token at{' '}
              <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                GitHub Settings
              </a>
            </p>
          </div>

          {/* Atlassian SSO */}
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <label className="block text-sm font-medium text-gray-700">
                Atlassian SSO Configuration
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => verifyIntegration('atlassian')}
                  disabled={isVerifyingIntegration.atlassian || !atlassianUrl.trim() || !atlassianEmail.trim() || !atlassianToken.trim()}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  {isVerifyingIntegration.atlassian ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    'Verify'
                  )}
                </button>
                <button
                  onClick={() => saveIntegrationConfig('atlassian')}
                  disabled={isSavingIntegration || !atlassianUrl.trim() || !atlassianEmail.trim() || !atlassianToken.trim()}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSavingIntegration ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={atlassianUrl}
                placeholder="Atlassian Cloud URL (e.g., https://your-domain.atlassian.net)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                onChange={(e) => setAtlassianUrl(e.target.value)}
              />
              <input
                type="email"
                value={atlassianEmail}
                placeholder="Email address"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                onChange={(e) => setAtlassianEmail(e.target.value)}
              />
              <input
                type="password"
                value={atlassianToken}
                placeholder="API Token"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                onChange={(e) => setAtlassianToken(e.target.value)}
              />
            </div>
            {verificationStatus.atlassian?.status === 'success' && (
              <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {verificationStatus.atlassian.message}
              </p>
            )}
            {verificationStatus.atlassian?.status === 'error' && (
              <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {verificationStatus.atlassian.message}
              </p>
            )}
            <p className="text-xs text-gray-500 mt-1">
              Used for accessing Confluence documents via Atlassian MCP server. Get your API token from{' '}
              <a href="https://id.atlassian.com/manage-profile/security/api-tokens" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                Atlassian Account Settings
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Agno Framework Status */}
      {agnoStatus && (
        <div className="bg-white rounded-xl shadow-lg p-6">
          <div className="flex items-center gap-3 mb-6">
            <Bot className="w-6 h-6 text-purple-600" />
            <div>
              <h3 className="text-lg font-bold text-gray-900">Agno Framework Status</h3>
              <p className="text-sm text-gray-500">Multi-agent system status</p>
            </div>
          </div>

          <div className="space-y-4">
            {/* Status Indicators */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  {agnoStatus.agno_available ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-red-600" />
                  )}
                  <span className="font-medium text-gray-900">Framework Available</span>
                </div>
                <p className="text-sm text-gray-600">
                  {agnoStatus.agno_available ? 'Agno framework is installed' : 'Agno framework not available'}
                </p>
              </div>

              <div className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  {agnoStatus.agno_enabled ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-yellow-600" />
                  )}
                  <span className="font-medium text-gray-900">Framework Enabled</span>
                </div>
                <p className="text-sm text-gray-600">
                  {agnoStatus.agno_enabled ? 'Agno agents are active' : 'Agno agents are not initialized'}
                </p>
              </div>
            </div>

            {/* Status Message */}
            <div className={`p-4 rounded-lg ${
              agnoStatus.agno_enabled 
                ? 'bg-green-50 border border-green-200' 
                : agnoStatus.can_initialize
                ? 'bg-blue-50 border border-blue-200'
                : 'bg-yellow-50 border border-yellow-200'
            }`}>
              <p className={`text-sm ${
                agnoStatus.agno_enabled 
                  ? 'text-green-700' 
                  : agnoStatus.can_initialize
                  ? 'text-blue-700'
                  : 'text-yellow-700'
              }`}>
                {agnoStatus.message}
              </p>
            </div>

            {/* Configured Providers */}
            {agnoStatus.configured_providers.length > 0 && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm font-medium text-gray-900 mb-2">Configured Providers:</p>
                <div className="flex flex-wrap gap-2">
                  {agnoStatus.configured_providers.map((provider) => (
                    <span
                      key={provider}
                      className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium"
                    >
                      {provider.charAt(0).toUpperCase() + provider.slice(1)}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Initialize Button */}
            {agnoStatus.can_initialize && !agnoStatus.agno_enabled && (
              <button
                onClick={handleInitializeAgents}
                disabled={isInitializing}
                className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isInitializing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Initializing...
                  </>
                ) : (
                  <>
                    <Bot className="w-5 h-5" />
                    Initialize Agents
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Save Button */}
      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-700'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}
        >
          {message.text}
        </div>
      )}

      <button
        onClick={handleSave}
        disabled={isSaving}
        className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isSaving ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Saving...
          </>
        ) : (
          <>
            <Save className="w-5 h-5" />
            Save Preferences
          </>
        )}
      </button>
    </div>
  );
}

