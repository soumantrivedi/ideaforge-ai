import { X, AlertCircle, CreditCard, Settings, RefreshCw, ExternalLink } from 'lucide-react';

interface ErrorModalProps {
  isOpen: boolean;
  onClose: () => void;
  error: {
    title: string;
    message: string;
    type?: 'quota' | 'rate_limit' | 'auth' | 'server' | 'network' | 'generic';
    actionUrl?: string;
    actionText?: string;
    onAction?: () => void;
  };
}

export function ErrorModal({ isOpen, onClose, error }: ErrorModalProps) {
  if (!isOpen) return null;

  const getIcon = () => {
    switch (error.type) {
      case 'quota':
      case 'rate_limit':
        return <CreditCard className="w-12 h-12 text-amber-500" />;
      case 'auth':
        return <Settings className="w-12 h-12 text-red-500" />;
      case 'server':
        return <AlertCircle className="w-12 h-12 text-red-500" />;
      case 'network':
        return <RefreshCw className="w-12 h-12 text-blue-500" />;
      default:
        return <AlertCircle className="w-12 h-12 text-gray-500" />;
    }
  };

  const getBackgroundColor = () => {
    switch (error.type) {
      case 'quota':
      case 'rate_limit':
        return 'bg-amber-50 border-amber-200';
      case 'auth':
        return 'bg-red-50 border-red-200';
      case 'server':
        return 'bg-red-50 border-red-200';
      case 'network':
        return 'bg-blue-50 border-blue-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getTextColor = () => {
    switch (error.type) {
      case 'quota':
      case 'rate_limit':
        return 'text-amber-800';
      case 'auth':
        return 'text-red-800';
      case 'server':
        return 'text-red-800';
      case 'network':
        return 'text-blue-800';
      default:
        return 'text-gray-800';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              {getIcon()}
              <h2 className="text-xl font-bold text-gray-900">{error.title}</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className={`rounded-lg p-4 border-2 ${getBackgroundColor()} mb-4`}>
            <p className={`text-sm ${getTextColor()} whitespace-pre-wrap`}>
              {error.message}
            </p>
          </div>

          <div className="flex gap-3">
            {error.actionUrl && (
              <a
                href={error.actionUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition flex items-center justify-center gap-2"
              >
                <ExternalLink className="w-4 h-4" />
                {error.actionText || 'Open Link'}
              </a>
            )}
            {error.onAction && (
              <button
                onClick={error.onAction}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition flex items-center justify-center gap-2"
              >
                <Settings className="w-4 h-4" />
                {error.actionText || 'Go to Settings'}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

