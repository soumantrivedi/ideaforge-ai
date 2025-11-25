import { useState, useEffect, useCallback } from 'react';
import { X, Maximize2, Minimize2, Sparkles } from 'lucide-react';

interface DesignMockup {
  id: string;
  provider: 'v0' | 'lovable';
  prompt: string;
  image_url: string;
  thumbnail_url: string;
  project_url?: string;
  created_at: string;
  metadata?: Record<string, any>;
}

interface DesignMockupGalleryProps {
  productId: string;
  phaseSubmissionId?: string;
  onSelectMockup?: (mockup: DesignMockup) => void;
  refreshTrigger?: number; // Increment this to trigger refresh
}

export function DesignMockupGallery({
  productId,
  phaseSubmissionId,
  onSelectMockup,
  refreshTrigger,
}: DesignMockupGalleryProps) {
  const [mockups, setMockups] = useState<DesignMockup[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedMockup, setExpandedMockup] = useState<DesignMockup | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<'v0' | 'lovable' | 'all'>('all');

  const loadMockups = useCallback(async () => {
    if (!productId) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const providerParam = selectedProvider !== 'all' ? `?provider=${selectedProvider}` : '';
      const response = await fetch(`${API_URL}/api/design/mockups/${productId}${providerParam}`);
      
      if (!response.ok) {
        // If 500 error, table might not exist - return empty array
        if (response.status === 500) {
          console.warn('Design mockups table may not exist yet');
          setMockups([]);
          return;
        }
        throw new Error('Failed to load mockups');
      }
      
      const data = await response.json();
      setMockups(data.mockups || []);
    } catch (error) {
      console.error('Error loading mockups:', error);
      setMockups([]);
    } finally {
      setLoading(false);
    }
  }, [productId, selectedProvider]);

  useEffect(() => {
    loadMockups();
  }, [loadMockups, refreshTrigger]);

  const handleMockupClick = (mockup: DesignMockup) => {
    if (expandedMockup?.id === mockup.id) {
      setExpandedMockup(null);
    } else {
      setExpandedMockup(mockup);
      if (onSelectMockup) {
        onSelectMockup(mockup);
      }
    }
  };

  const handleDelete = async (mockupId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this mockup?')) {
      return;
    }

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/design/mockups/${mockupId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete mockup');
      }

      setMockups(Array.isArray(mockups) ? mockups.filter(m => m.id !== mockupId) : []);
      if (expandedMockup?.id === mockupId) {
        setExpandedMockup(null);
      }
    } catch (error) {
      console.error('Error deleting mockup:', error);
      alert('Failed to delete mockup');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading design mockups...</div>
      </div>
    );
  }

  if (mockups.length === 0) {
    return (
      <div className="text-center p-8 text-gray-500">
        <Sparkles className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>No design mockups yet.</p>
        <p className="text-sm mt-2">Generate prompts and create mockups using V0 or Lovable.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Filter by provider:</span>
        <button
          onClick={() => setSelectedProvider('all')}
          className={`px-3 py-1 text-xs rounded-lg transition ${
            selectedProvider === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setSelectedProvider('v0')}
          className={`px-3 py-1 text-xs rounded-lg transition ${
            selectedProvider === 'v0'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          V0
        </button>
        <button
          onClick={() => setSelectedProvider('lovable')}
          className={`px-3 py-1 text-xs rounded-lg transition ${
            selectedProvider === 'lovable'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Lovable
        </button>
      </div>

      {/* Expanded View */}
      {expandedMockup && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <div>
                <h3 className="font-semibold text-lg">
                  {expandedMockup.provider === 'v0' ? 'V0' : 'Lovable'} Design Mockup
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  {new Date(expandedMockup.created_at).toLocaleString()}
                </p>
              </div>
              <button
                onClick={() => setExpandedMockup(null)}
                className="p-2 hover:bg-gray-100 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {expandedMockup.image_url || expandedMockup.thumbnail_url ? (
                <img
                  src={expandedMockup.image_url || expandedMockup.thumbnail_url}
                  alt="Design mockup"
                  className="w-full h-auto rounded-lg shadow-lg"
                />
              ) : (
                <div className="flex items-center justify-center h-64 bg-gray-100 rounded-lg">
                  <p className="text-gray-500">Image not available</p>
                </div>
              )}
              {expandedMockup.prompt && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-semibold mb-2">Prompt Used:</h4>
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">{expandedMockup.prompt}</p>
                </div>
              )}
              {expandedMockup.project_url && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                  <h4 className="font-semibold mb-2">Project URL:</h4>
                  <a
                    href={expandedMockup.project_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline break-all"
                  >
                    {expandedMockup.project_url}
                  </a>
                  <button
                    onClick={() => window.open(expandedMockup.project_url, '_blank')}
                    className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                  >
                    Open in Browser
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Thumbnail Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {mockups.map((mockup) => (
          <div
            key={mockup.id}
            className="relative group cursor-pointer bg-white rounded-lg border border-gray-200 overflow-hidden hover:shadow-lg transition shadow-sm"
            onClick={() => handleMockupClick(mockup)}
          >
            {/* Thumbnail */}
            {mockup.thumbnail_url ? (
              <div className="aspect-video bg-gray-100 relative">
                <img
                  src={mockup.thumbnail_url}
                  alt={`${mockup.provider} mockup`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition" />
              </div>
            ) : (
              <div className="aspect-video bg-gray-100 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-gray-400" />
              </div>
            )}

            {/* Overlay Info */}
            <div className="absolute top-2 right-2">
              <span
                className={`px-2 py-1 text-xs rounded-full font-medium ${
                  mockup.provider === 'v0'
                    ? 'bg-blue-500 text-white'
                    : 'bg-purple-500 text-white'
                }`}
              >
                {mockup.provider === 'v0' ? 'V0' : 'Lovable'}
              </span>
            </div>

            {/* Delete Button */}
            <button
              onClick={(e) => handleDelete(mockup.id, e)}
              className="absolute top-2 left-2 p-1.5 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition hover:bg-red-600"
              title="Delete mockup"
            >
              <X className="w-3 h-3" />
            </button>

            {/* Expand Icon */}
            <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition">
              <div className="p-1.5 bg-white/90 rounded-full">
                <Maximize2 className="w-4 h-4 text-gray-700" />
              </div>
            </div>

            {/* Footer */}
            <div className="p-2">
              <p className="text-xs text-gray-500 truncate">
                {new Date(mockup.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

