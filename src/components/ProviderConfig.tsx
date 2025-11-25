import { useState } from 'react';
import { Settings, Key, Eye, EyeOff, CheckCircle2, XCircle, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import type { AIProvider } from '../lib/ai-providers';
import { apiFetch } from '../lib/api-client';

interface ProviderConfigProps {
  onSaveConfig: (config: {
    openaiKey?: string;
    claudeKey?: string;
    geminiKey?: string;
    v0Key?: string;
    lovableKey?: string;
  }) => void;
  configuredProviders: AIProvider[];
  apiKeysStatus?: Record<string, boolean>;
}

type VerificationState = 'idle' | 'verifying' | 'success' | 'error';

interface VerificationStatus {
  status: VerificationState;
  message?: string;
}

export function ProviderConfig({ onSaveConfig, configuredProviders, apiKeysStatus = {} }: ProviderConfigProps) {
  const { token } = useAuth();
  const [openaiKey, setOpenaiKey] = useState('');
  const [claudeKey, setClaudeKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [v0Key, setV0Key] = useState('');
  const [lovableKey, setLovableKey] = useState('');
  const [verifySsl, setVerifySsl] = useState(false); // Default to false for SSL verification
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [verificationStatus, setVerificationStatus] = useState<Record<AIProvider | 'v0' | 'lovable', VerificationStatus>>({
    openai: { status: 'idle' },
    claude: { status: 'idle' },
    gemini: { status: 'idle' },
    v0: { status: 'idle' },
    lovable: { status: 'idle' },
  });
  const [verificationInfoVisible, setVerificationInfoVisible] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    const payload = {
      openaiKey: openaiKey.trim() || null,
      claudeKey: claudeKey.trim() || null,
      geminiKey: geminiKey.trim() || null,
      v0Key: v0Key.trim() || null,
      lovableKey: lovableKey.trim() || null,
    };

    try {
      const response = await apiFetch('/api/providers/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result?.detail || 'Failed to save provider configuration.');
      }

      onSaveConfig({
        openaiKey: payload.openaiKey || undefined,
        claudeKey: payload.claudeKey || undefined,
        geminiKey: payload.geminiKey || undefined,
        v0Key: payload.v0Key || undefined,
        lovableKey: payload.lovableKey || undefined,
      });

      setSaveSuccess('Provider configuration updated successfully.');
      
      // Refresh API keys status after saving
      // Trigger a reload by calling the parent's refresh if available
      // For now, we'll rely on the parent component to refresh
      window.dispatchEvent(new CustomEvent('apiKeysUpdated'));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const updateVerificationStatus = (provider: AIProvider, status: VerificationStatus) => {
    setVerificationStatus((prev) => ({
      ...prev,
      [provider]: status,
    }));
  };

  const verifyProviderKey = async (provider: AIProvider | 'v0' | 'lovable') => {
    const key =
      provider === 'openai'
        ? openaiKey.trim()
        : provider === 'claude'
        ? claudeKey.trim()
        : provider === 'gemini'
        ? geminiKey.trim()
        : provider === 'v0'
        ? v0Key.trim()
        : lovableKey.trim();

    if (!key) {
      updateVerificationStatus(provider, {
        status: 'error',
        message: 'Enter an API key before verifying.',
      });
      return;
    }

    updateVerificationStatus(provider, { status: 'verifying' });
    setVerificationInfoVisible(true);

    try {
      // For V0 provider, include verify_ssl parameter
      const requestBody: any = { provider, api_key: key };
      if (provider === 'v0') {
        requestBody.verify_ssl = verifySsl;
      }

      const response = await apiFetch('/api/providers/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result?.detail || 'Verification failed');
      }

      updateVerificationStatus(provider, {
        status: 'success',
        message: result?.message || 'API key verified successfully.',
      });
    } catch (error) {
      updateVerificationStatus(provider, {
        status: 'error',
        message:
          error instanceof Error ? error.message : 'Verification failed. Please try again.',
      });
    }
  };

  const toggleShowKey = (provider: string) => {
    setShowKeys((prev) => ({ ...prev, [provider]: !prev[provider] }));
  };

  const isConfigured = (provider: AIProvider | 'v0' | 'lovable') => {
    // First check apiKeysStatus (from database), then fallback to configuredProviders (in-memory)
    // Map frontend provider names to backend provider names
    const providerKey = provider === 'claude' ? 'anthropic' : provider === 'gemini' ? 'google' : provider;
    return apiKeysStatus[providerKey] === true || configuredProviders.includes(provider as AIProvider);
  };

  const renderVerificationFeedback = (provider: AIProvider | 'v0' | 'lovable') => {
    const status = verificationStatus[provider];
    if (!status || status.status === 'idle') return null;

    if (status.status === 'verifying') {
      return (
        <span className="text-xs text-blue-600 flex items-center gap-1">
          <Loader2 className="w-3 h-3 animate-spin" />
          Verifying with {provider === 'claude' ? 'Claude' : provider === 'gemini' ? 'Gemini' : provider === 'v0' ? 'V0' : provider === 'lovable' ? 'Lovable' : 'OpenAI'}...
        </span>
      );
    }

    if (status.status === 'success') {
      return (
        <span className="text-xs text-green-600 flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3" />
          {status.message || 'API key verified successfully.'}
        </span>
      );
    }

    return (
      <span className="text-xs text-red-600 flex items-center gap-1">
        <XCircle className="w-3 h-3" />
        {status.message || 'Verification failed'}
      </span>
    );
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-2 mb-6">
        <Settings className="w-5 h-5 text-gray-700" />
        <h3 className="text-lg font-bold text-gray-900">AI Provider Setup</h3>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              OpenAI API Key
            </label>
            {isConfigured('openai') ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">Configured</span>
              </div>
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
          </div>
          {isConfigured('openai') && !openaiKey && (
            <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
              ✓ API key is already configured. Leave blank to keep existing key, or enter a new key to update.
            </div>
          )}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <Key className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type={showKeys.openai ? 'text' : 'password'}
              value={openaiKey}
              onChange={(e) => setOpenaiKey(e.target.value)}
              placeholder={isConfigured('openai') ? "Leave blank to keep existing key, or enter new key..." : "sk-..."}
              className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <button
              type="button"
              onClick={() => toggleShowKey('openai')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKeys.openai ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your API key from{' '}
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700"
            >
              OpenAI Platform
            </a>
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => verifyProviderKey('openai')}
              className="px-3 py-2 text-xs font-medium text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-50 flex items-center gap-2"
              disabled={!openaiKey.trim() || verificationStatus.openai.status === 'verifying'}
            >
              {verificationStatus.openai.status === 'verifying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Verify Key
            </button>
            {renderVerificationFeedback('openai')}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              Anthropic Claude API Key
            </label>
            {isConfigured('claude') ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">Configured</span>
              </div>
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
          </div>
          {isConfigured('claude') && !claudeKey && (
            <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
              ✓ API key is already configured. Leave blank to keep existing key, or enter a new key to update.
            </div>
          )}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <Key className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type={showKeys.claude ? 'text' : 'password'}
              value={claudeKey}
              onChange={(e) => setClaudeKey(e.target.value)}
              placeholder={isConfigured('claude') ? "Leave blank to keep existing key, or enter new key..." : "sk-ant-..."}
              className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <button
              type="button"
              onClick={() => toggleShowKey('claude')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKeys.claude ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your API key from{' '}
            <a
              href="https://console.anthropic.com/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700"
            >
              Anthropic Console
            </a>
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => verifyProviderKey('claude')}
              className="px-3 py-2 text-xs font-medium text-purple-700 border border-purple-200 rounded-lg hover:bg-purple-50 disabled:opacity-50 flex items-center gap-2"
              disabled={!claudeKey.trim() || verificationStatus.claude.status === 'verifying'}
            >
              {verificationStatus.claude.status === 'verifying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Verify Key
            </button>
            {renderVerificationFeedback('claude')}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              Google Gemini API Key
            </label>
            {isConfigured('gemini') ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">Configured</span>
              </div>
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
          </div>
          {isConfigured('gemini') && !geminiKey && (
            <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
              ✓ API key is already configured. Leave blank to keep existing key, or enter a new key to update.
            </div>
          )}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <Key className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type={showKeys.gemini ? 'text' : 'password'}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder={isConfigured('gemini') ? "Leave blank to keep existing key, or enter new key..." : "AIza..."}
              className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <button
              type="button"
              onClick={() => toggleShowKey('gemini')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKeys.gemini ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your API key from{' '}
            <a
              href="https://ai.google.dev/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700"
            >
              Google AI Studio
            </a>
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => verifyProviderKey('gemini')}
              className="px-3 py-2 text-xs font-medium text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 disabled:opacity-50 flex items-center gap-2"
              disabled={!geminiKey.trim() || verificationStatus.gemini.status === 'verifying'}
            >
              {verificationStatus.gemini.status === 'verifying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Verify Key
            </button>
            {renderVerificationFeedback('gemini')}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              V0 (Vercel) API Key
            </label>
            {isConfigured('v0') ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">Configured</span>
              </div>
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
          </div>
          {isConfigured('v0') && !v0Key && (
            <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
              ✓ API key is already configured. Leave blank to keep existing key, or enter a new key to update.
            </div>
          )}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <Key className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type={showKeys.v0 ? 'text' : 'password'}
              value={v0Key}
              onChange={(e) => setV0Key(e.target.value)}
              placeholder={isConfigured('v0') ? "Leave blank to keep existing key, or enter new key..." : "Enter V0 API key"}
              className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <button
              type="button"
              onClick={() => toggleShowKey('v0')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKeys.v0 ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your API key from{' '}
            <a
              href="https://v0.dev"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700"
            >
              V0 Platform
            </a>
          </p>
          <div className="mt-3 flex items-center gap-2">
            <input
              type="checkbox"
              id="verify-ssl-v0"
              checked={verifySsl}
              onChange={(e) => setVerifySsl(e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="verify-ssl-v0" className="text-xs text-gray-700 cursor-pointer">
              Verify SSL certificate (recommended for production)
            </label>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => verifyProviderKey('v0')}
              className="px-3 py-2 text-xs font-medium text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-50 flex items-center gap-2"
              disabled={!v0Key.trim() || verificationStatus.v0.status === 'verifying'}
            >
              {verificationStatus.v0.status === 'verifying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Verify Key
            </button>
            {renderVerificationFeedback('v0')}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-semibold text-gray-700">
              Lovable API Key
            </label>
            {isConfigured('lovable') ? (
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-xs text-green-600 font-medium">Configured</span>
              </div>
            ) : (
              <XCircle className="w-5 h-5 text-gray-300" />
            )}
          </div>
          {isConfigured('lovable') && !lovableKey && (
            <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
              ✓ API key is already configured. Leave blank to keep existing key, or enter a new key to update.
            </div>
          )}
          <div className="relative">
            <div className="absolute left-3 top-1/2 -translate-y-1/2">
              <Key className="w-4 h-4 text-gray-400" />
            </div>
            <input
              type={showKeys.lovable ? 'text' : 'password'}
              value={lovableKey}
              onChange={(e) => setLovableKey(e.target.value)}
              placeholder={isConfigured('lovable') ? "Leave blank to keep existing key, or enter new key..." : "Enter Lovable API key"}
              className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <button
              type="button"
              onClick={() => toggleShowKey('lovable')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showKeys.lovable ? (
                <EyeOff className="w-4 h-4" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Get your API key from{' '}
            <a
              href="https://lovable.dev"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-700"
            >
              Lovable Platform
            </a>
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => verifyProviderKey('lovable')}
              className="px-3 py-2 text-xs font-medium text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-50 disabled:opacity-50 flex items-center gap-2"
              disabled={!lovableKey.trim() || verificationStatus.lovable.status === 'verifying'}
            >
              {verificationStatus.lovable.status === 'verifying' && <Loader2 className="w-3 h-3 animate-spin" />}
              Verify Key
            </button>
            {renderVerificationFeedback('lovable')}
          </div>
        </div>

        <button
          type="submit"
          className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          disabled={isSaving}
        >
          {isSaving && <Loader2 className="w-5 h-5 animate-spin" />}
          Save Configuration
        </button>

        {saveError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            {saveError}
          </div>
        )}

        {saveSuccess && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800">
            {saveSuccess}
          </div>
        )}

        {verificationInfoVisible && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex gap-3 text-sm text-yellow-900">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p>
              Verification temporarily sends your API key to the backend so it can call the selected
              provider and confirm the key is valid. Keys are never stored or logged.
            </p>
          </div>
        )}

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-900">
            <strong>Privacy Note:</strong> Your API keys are stored locally in your browser
            and never sent to any server except the AI providers themselves.
          </p>
        </div>

        {configuredProviders.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm font-medium text-green-900 mb-2">
              Configured Providers ({configuredProviders.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {configuredProviders.map((provider) => (
                <span
                  key={provider}
                  className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full"
                >
                  {provider.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
