import { useState, useEffect } from 'react';
import { Settings, Palette, Bell, Globe, Save, Loader2, Moon, Sun, Sparkles } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { ProviderConfig } from './ProviderConfig';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

  useEffect(() => {
    if (token) {
      loadPreferences();
      loadAPIKeysStatus();
    }
  }, [token]);

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
          }}
          configuredProviders={configuredProviders}
        />
      </div>

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

