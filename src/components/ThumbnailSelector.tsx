import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';

interface ThumbnailPreview {
  index: number;
  thumbnail_url?: string;
  project_url?: string;
  prompt: string;
  metadata?: Record<string, any>;
}

interface ThumbnailSelectorProps {
  previews: ThumbnailPreview[];
  isOpen: boolean;
  onClose: () => void;
  onSelect: (index: number) => void;
  provider: 'v0' | 'lovable';
}

export function ThumbnailSelector({
  previews,
  isOpen,
  onClose,
  onSelect,
  provider,
}: ThumbnailSelectorProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  if (!isOpen) return null;

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    // Don't call onSelect here - wait for "Confirm Selection" button
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h3 className="text-2xl font-bold text-gray-900">
              Select Your Preferred {provider === 'v0' ? 'V0' : 'Lovable'} Design
            </h3>
            <p className="text-sm text-gray-600 mt-2">
              Choose one of the {previews.length} design variations generated. Click on a thumbnail to select it.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {previews.map((preview, idx) => (
              <div
                key={idx}
                onClick={() => handleSelect(idx)}
                className={`cursor-pointer border-2 rounded-xl overflow-hidden transition-all ${
                  selectedIndex === idx
                    ? 'border-purple-600 shadow-lg scale-105'
                    : 'border-gray-200 hover:border-purple-400 hover:shadow-md'
                }`}
              >
                {preview.thumbnail_url ? (
                  <div className="aspect-video bg-gray-100 relative">
                    <img
                      src={preview.thumbnail_url}
                      alt={`Preview ${idx + 1}`}
                      className="w-full h-full object-cover"
                    />
                    {selectedIndex === idx && (
                      <div className="absolute inset-0 bg-purple-600/20 flex items-center justify-center">
                        <div className="bg-purple-600 text-white px-4 py-2 rounded-full font-semibold">
                          Selected
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="aspect-video bg-gray-100 flex items-center justify-center">
                    <div className="text-center">
                      <Loader2 className="w-8 h-8 text-gray-400 animate-spin mx-auto mb-2" />
                      <span className="text-gray-400 text-sm">Loading Preview {idx + 1}...</span>
                    </div>
                  </div>
                )}
                <div className="p-4 bg-white">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-gray-900">Option {idx + 1}</span>
                    {preview.project_url && (
                      <span className="text-xs text-gray-500">Project Available</span>
                    )}
                  </div>
                  {selectedIndex === idx && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (preview.project_url) {
                          window.open(preview.project_url, '_blank');
                        }
                      }}
                      className="mt-2 w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 transition"
                      disabled={!preview.project_url}
                    >
                      {preview.project_url ? 'Open Project' : 'Generating...'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="p-6 border-t bg-gray-50 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {selectedIndex !== null
              ? `Option ${selectedIndex + 1} selected. Click "Confirm Selection" to proceed.`
              : 'Please select a design option above.'}
          </p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (selectedIndex !== null) {
                  onSelect(selectedIndex);
                }
              }}
              disabled={selectedIndex === null}
              className="px-6 py-2 text-sm font-medium text-white bg-purple-600 rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Confirm Selection
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

