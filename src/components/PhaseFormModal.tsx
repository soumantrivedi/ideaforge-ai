import { useState, useEffect } from 'react';
import { X, Send, Loader2, Sparkles } from 'lucide-react';
import type { LifecyclePhase } from '../lib/product-lifecycle-service';

interface PhaseFormModalProps {
  phase: LifecyclePhase;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (formData: Record<string, string>) => Promise<void>;
  existingData?: Record<string, string>;
}

export function PhaseFormModal({
  phase,
  isOpen,
  onClose,
  onSubmit,
  existingData,
}: PhaseFormModalProps) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      // Initialize form data with existing data or empty strings
      // This ensures ALL fields from ALL pages are captured
      const initialData: Record<string, string> = {};
      phase.required_fields.forEach((field) => {
        initialData[field] = existingData?.[field] || '';
      });
      setFormData(initialData);
      setCurrentPromptIndex(0);
      console.log('Form initialized with all fields:', {
        totalFields: phase.required_fields.length,
        fields: phase.required_fields,
        initialData,
      });
    }
  }, [isOpen, phase, existingData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Collect ALL form data from ALL pages
    const completeFormData: Record<string, string> = {};
    phase.required_fields.forEach((field) => {
      completeFormData[field] = formData[field] || '';
    });
    
    console.log('Form submit triggered', {
      totalFields: phase.required_fields.length,
      filledFields: Object.keys(completeFormData).filter(k => completeFormData[k]?.trim()).length,
      allFieldsFilled: allFieldsFilled(),
      completeFormData,
    });
    
    // Validate all fields are filled
    if (!allFieldsFilled()) {
      const missingFields = phase.required_fields.filter(field => !completeFormData[field]?.trim());
      alert(`Please fill in all required fields before generating. Missing: ${missingFields.map(f => f.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')).join(', ')}`);
      return;
    }
    
    setIsSubmitting(true);

    try {
      console.log('Submitting ALL form data from all pages:', completeFormData);
      await onSubmit(completeFormData);
      // Don't close immediately - let the parent handle it after processing
      // The parent will close the modal after successful generation
    } catch (error) {
      console.error('Error submitting form:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      alert(`Error processing your request: ${errorMessage}. Please check the console for details.`);
      // Don't close modal on error so user can retry
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    if (currentPromptIndex < phase.template_prompts.length - 1) {
      setCurrentPromptIndex(currentPromptIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentPromptIndex > 0) {
      setCurrentPromptIndex(currentPromptIndex - 1);
    }
  };

  const isCurrentFieldFilled = () => {
    const currentField = phase.required_fields[currentPromptIndex];
    return formData[currentField]?.trim().length > 0;
  };

  const allFieldsFilled = () => {
    return phase.required_fields.every((field) => formData[field]?.trim().length > 0);
  };

  if (!isOpen) return null;

  const currentField = phase.required_fields[currentPromptIndex];
  const currentPrompt = phase.template_prompts[currentPromptIndex];
  const progress = ((currentPromptIndex + 1) / phase.template_prompts.length) * 100;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="text-4xl">{phase.icon}</div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{phase.phase_name}</h2>
                <p className="text-sm text-gray-600">{phase.description}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white rounded-lg transition"
              disabled={isSubmitting}
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-600">
                Question {currentPromptIndex + 1} of {phase.template_prompts.length}
              </span>
              <span className="font-semibold text-gray-900">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-white rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Form Content */}
        <form onSubmit={handleSubmit} className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Current Question */}
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-r-lg">
                <Sparkles className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="font-semibold text-blue-900 mb-1">
                    {currentPrompt}
                  </div>
                  <div className="text-xs text-blue-700">
                    Provide detailed information to help AI agents generate comprehensive content
                  </div>
                </div>
              </div>

              <div>
                <label
                  htmlFor={currentField}
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  {currentField.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                </label>
                <textarea
                  id={currentField}
                  value={formData[currentField] || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, [currentField]: e.target.value })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={8}
                  placeholder="Enter your detailed response here..."
                  disabled={isSubmitting}
                />
                <div className="mt-2 text-xs text-gray-500">
                  {formData[currentField]?.length || 0} characters
                </div>
              </div>
            </div>

            {/* Navigation Hints */}
            <div className="flex items-center justify-between text-xs text-gray-500 border-t pt-4">
              <div>
                {currentPromptIndex > 0 ? (
                  <span>← Previous question: {phase.template_prompts[currentPromptIndex - 1]}</span>
                ) : (
                  <span>First question</span>
                )}
              </div>
              <div>
                {currentPromptIndex < phase.template_prompts.length - 1 ? (
                  <span>Next question: {phase.template_prompts[currentPromptIndex + 1]} →</span>
                ) : (
                  <span>Last question</span>
                )}
              </div>
            </div>
          </div>

          {/* Footer - Now inside form */}
          <div className="p-6 border-t border-gray-200 bg-gray-50 flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handlePrevious}
              disabled={currentPromptIndex === 0 || isSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>

            <div className="flex items-center gap-2 text-xs text-gray-600">
              {phase.required_fields.map((_, index) => (
                <div
                  key={index}
                  className={`w-2 h-2 rounded-full transition ${
                    index === currentPromptIndex
                      ? 'bg-blue-600 w-6'
                      : index < currentPromptIndex
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>

            {currentPromptIndex < phase.template_prompts.length - 1 ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={!isCurrentFieldFilled() || isSubmitting}
                className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                disabled={!allFieldsFilled() || isSubmitting}
                className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Generate with AI
                  </>
                )}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
