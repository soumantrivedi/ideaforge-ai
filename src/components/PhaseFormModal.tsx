import { useState, useEffect } from 'react';
import { X, Send, Loader2, Sparkles, Wand2, Trash2, Play } from 'lucide-react';
import type { LifecyclePhase } from '../lib/product-lifecycle-service';
import { lifecycleService } from '../lib/product-lifecycle-service';
import { DesignMockupGallery } from './DesignMockupGallery';
import { useAuth } from '../contexts/AuthContext';

interface PhaseFormModalProps {
  phase: LifecyclePhase;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (formData: Record<string, string>) => Promise<void>;
  existingData?: Record<string, string>;
  productId?: string;
  sessionId?: string;
  onNavigateToSettings?: () => void;
}

export function PhaseFormModal({
  phase,
  isOpen,
  onClose,
  onSubmit,
  existingData,
  productId,
  sessionId,
  onNavigateToSettings,
}: PhaseFormModalProps) {
  const { user, token } = useAuth();
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentPromptIndex, setCurrentPromptIndex] = useState(0);
  const [isGeneratingAIHelp, setIsGeneratingAIHelp] = useState(false);
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState<{v0: boolean, lovable: boolean}>({v0: false, lovable: false});
  const [isGeneratingMockup, setIsGeneratingMockup] = useState<{v0: boolean, lovable: boolean}>({v0: false, lovable: false});
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | undefined>();
  const [mockupRefreshTrigger, setMockupRefreshTrigger] = useState(0);

  useEffect(() => {
    if (isOpen) {
      // Initialize form data with existing data or empty strings
      // This ensures ALL fields from ALL pages are captured
      const initialData: Record<string, string> = {};
      phase.required_fields.forEach((field) => {
        if (field === 'v0_lovable_prompts') {
          // Initialize as JSON string for v0_lovable_prompts
          const existing = existingData?.[field];
          if (existing && typeof existing === 'string') {
            try {
              JSON.parse(existing); // Validate it's valid JSON
              initialData[field] = existing;
            } catch {
              initialData[field] = JSON.stringify({ v0_prompt: '', lovable_prompt: '' });
            }
          } else {
            initialData[field] = JSON.stringify({ v0_prompt: '', lovable_prompt: '' });
          }
        } else {
          initialData[field] = existingData?.[field] || '';
        }
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
      filledFields: Object.keys(completeFormData || {}).filter(k => completeFormData[k]?.trim()).length,
      allFieldsFilled: allFieldsFilled(),
      completeFormData,
    });
    
    // Validate all fields are filled
    if (!allFieldsFilled()) {
      const missingFields = Array.isArray(phase.required_fields) ? phase.required_fields.filter(field => !completeFormData[field]?.trim()) : [];
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

  const handleAIHelp = async () => {
    if (!productId || !sessionId) {
      alert('Product ID and Session ID are required for AI help. Please ensure you have selected a phase.');
      return;
    }

    const currentField = phase.required_fields[currentPromptIndex];
    const currentPrompt = phase.template_prompts[currentPromptIndex];
    
    // Compute design phase section flags here
    const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
    const isV0LovablePromptsSection = isDesignPhase && currentField === 'v0_lovable_prompts';
    const isDesignMockupsSection = isDesignPhase && currentField === 'design_mockups';

    setIsGeneratingAIHelp(true);

    try {
      if (!user || !user.id) {
        throw new Error('User not authenticated. Please log in to use AI help.');
      }

      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      
      // Fetch conversation history for context
      const conversationHistory = await lifecycleService.getProductConversationHistory(productId);
      
      // Fetch all previous phase submissions for context
      const allSubmissions = await lifecycleService.getPhaseSubmissions(productId);
      
      // Build contextualized prompt
      const contextParts: string[] = [];
      
      // Add conversation history context
      if (conversationHistory.length > 0) {
        contextParts.push('## Previous Conversation Context');
        contextParts.push('');
        conversationHistory.slice(-10).forEach((entry, idx) => {
          if (entry.message_type === 'user' || entry.message_type === 'agent') {
            const role = entry.message_type === 'user' ? 'User' : (entry.agent_name || 'Agent');
            contextParts.push(`**${role}**: ${entry.content.substring(0, 500)}${entry.content.length > 500 ? '...' : ''}`);
            if (idx < conversationHistory.length - 1) contextParts.push('');
          }
        });
        contextParts.push('');
        contextParts.push('---');
        contextParts.push('');
      }

      // Add previous phase submissions context
      if (allSubmissions.length > 0) {
        contextParts.push('## Previous Phase Information');
        contextParts.push('');
        allSubmissions.forEach((submission) => {
          if (submission.form_data && Object.keys(submission.form_data).length > 0) {
            contextParts.push(`### Phase: ${submission.phase_id}`);
            Object.entries(submission.form_data).forEach(([key, value]) => {
              if (value && typeof value === 'string' && value.trim()) {
                const fieldName = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                contextParts.push(`- **${fieldName}**: ${value.substring(0, 300)}${value.length > 300 ? '...' : ''}`);
              }
            });
            contextParts.push('');
          }
        });
        contextParts.push('---');
        contextParts.push('');
      }

      // Add current phase context (other fields already filled)
      const otherFieldsData: string[] = [];
      phase.required_fields.forEach((field, idx) => {
        if (field !== currentField && formData[field]?.trim()) {
          const fieldName = field.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
          otherFieldsData.push(`- **${fieldName}**: ${formData[field]}`);
        }
      });

      if (otherFieldsData.length > 0) {
        contextParts.push('## Current Phase - Other Fields Already Filled');
        contextParts.push('');
        contextParts.push(...otherFieldsData);
        contextParts.push('');
        contextParts.push('---');
        contextParts.push('');
      }

      // Build the main prompt
      const mainPrompt = [
        `I'm working on the "${phase.phase_name}" phase of my product lifecycle.`,
        '',
        'Based on all the context provided above (previous conversations, previous phases, and other fields in this phase),',
        `please help me generate a comprehensive and contextualized response for the following question:`,
        '',
        `**Question**: ${currentPrompt}`,
        '',
        `**Field**: ${currentField.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}`,
        '',
        'Please generate a detailed, well-structured response that:',
        '- Takes into account all the previous information and context',
        '- Is specific and relevant to the product being developed',
        '- Provides actionable and comprehensive information',
        '- Maintains consistency with previously provided information',
        '- Is professional and well-formatted',
        '',
        'Generate only the content for this specific field, without repeating the question or adding extra formatting.',
      ].join('\n');

      const fullPrompt = [
        ...contextParts,
        mainPrompt,
      ].join('\n');

      // Call multi-agent API (API_URL already defined above)
      
      // Determine which agents to use based on phase and field
      let primaryAgent = 'ideation';
      let supportingAgents: string[] = ['research', 'analysis'];
      
      // Special handling for Design phase - V0/Lovable prompts
      if (isV0LovablePromptsSection) {
        // This will be handled by handleGeneratePrompt, not here
        // But we still need to set agents for the general Help with AI
        primaryAgent = 'strategy';
        supportingAgents = ['analysis', 'ideation'];
      } else if (phase.phase_name.toLowerCase().includes('research')) {
        primaryAgent = 'research';
        supportingAgents = ['analysis', 'strategy'];
      } else if (phase.phase_name.toLowerCase().includes('requirement')) {
        primaryAgent = 'analysis';
        supportingAgents = ['research', 'validation'];
      } else if (phase.phase_name.toLowerCase().includes('design')) {
        primaryAgent = 'strategy';
        supportingAgents = ['analysis', 'ideation'];
      } else if (phase.phase_name.toLowerCase().includes('development')) {
        primaryAgent = 'prd_authoring';
        supportingAgents = ['analysis', 'validation'];
      } else if (phase.phase_name.toLowerCase().includes('market')) {
        primaryAgent = 'strategy';
        supportingAgents = ['research', 'analysis'];
      }

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/api/multi-agent/process`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          user_id: user.id,
          query: fullPrompt,
          coordination_mode: 'collaborative',
          primary_agent: primaryAgent,
          supporting_agents: supportingAgents,
          context: {
            product_id: productId,
            phase_id: phase.id,
            phase_name: phase.phase_name,
            current_field: currentField,
            current_prompt: currentPrompt,
            form_data: formData,
          },
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = `Failed to generate AI help: ${response.status}`;
        
        try {
          const errorJson = JSON.parse(errorText);
          if (errorJson.detail) {
            if (errorJson.detail.includes('No AI provider configured')) {
              errorMessage = 'No AI provider is configured on the backend. Please go to Settings and configure at least one AI provider (OpenAI, Anthropic, or Google Gemini) before using "Help with AI".';
            } else {
              errorMessage = errorJson.detail;
            }
          }
        } catch {
          // If errorText is not JSON, use it as is
          if (errorText.includes('No AI provider configured')) {
            errorMessage = 'No AI provider is configured on the backend. Please go to Settings and configure at least one AI provider (OpenAI, Anthropic, or Google Gemini) before using "Help with AI".';
          } else {
            errorMessage = `${errorMessage} - ${errorText}`;
          }
        }
        
        throw new Error(errorMessage);
      }

      const result = await response.json();
      const generatedContent = result.response || '';

      // Pre-populate the current field with generated content
      setFormData({
        ...formData,
        [currentField]: generatedContent.trim(),
      });

    } catch (error) {
      console.error('Error generating AI help:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      
      // Show a more user-friendly error message
      if (errorMessage.includes('No AI provider')) {
        const shouldGoToSettings = confirm(
          `${errorMessage}\n\nWould you like to go to Settings to configure an AI provider now?`
        );
        if (shouldGoToSettings && onNavigateToSettings) {
          onClose();
          onNavigateToSettings();
        } else if (shouldGoToSettings) {
          alert('Please navigate to Settings from the main menu to configure AI providers.');
        }
      } else {
        alert(`Failed to generate AI help: ${errorMessage}`);
      }
    } finally {
      setIsGeneratingAIHelp(false);
    }
  };

  const handleClear = () => {
    const currentField = phase.required_fields[currentPromptIndex];
    setFormData({
      ...formData,
      [currentField]: '',
    });
  };

  // Get or create submission ID for design mockups
  useEffect(() => {
    const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
    if (isDesignPhase && productId) {
      const loadSubmission = async () => {
        try {
          const submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
          if (submission) {
            setSelectedSubmissionId(submission.id);
          }
        } catch (error) {
          console.error('Error loading submission:', error);
        }
      };
      loadSubmission();
    }
  }, [productId, phase.id, phase.phase_name]);

  const handleGeneratePrompt = async (provider: 'v0' | 'lovable') => {
    if (!productId) {
      alert('Product ID is required');
      return;
    }

    setIsGeneratingPrompt({ ...isGeneratingPrompt, [provider]: true });

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/design/generate-prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: productId,
          phase_submission_id: selectedSubmissionId,
          provider,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to generate prompt: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      const promptKey = provider === 'v0' ? 'v0_prompt' : 'lovable_prompt';
      
      // Store prompts in form data
      const currentPrompts = formData['v0_lovable_prompts'] || '';
      const promptsObj = currentPrompts ? JSON.parse(currentPrompts) : { v0_prompt: '', lovable_prompt: '' };
      promptsObj[promptKey] = result.prompt;
      
      setFormData({
        ...formData,
        v0_lovable_prompts: JSON.stringify(promptsObj),
      });
    } catch (error) {
      console.error(`Error generating ${provider} prompt:`, error);
      alert(`Failed to generate ${provider} prompt: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsGeneratingPrompt({ ...isGeneratingPrompt, [provider]: false });
    }
  };

  const handleGenerateMockup = async (provider: 'v0' | 'lovable') => {
    if (!productId) {
      alert('Product ID is required');
      return;
    }

    const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
    const prompt = promptsObj[`${provider}_prompt`] || '';

    if (!prompt.trim()) {
      alert(`Please generate a ${provider} prompt first using "Help with AI"`);
      return;
    }

    setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: true });

    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/api/design/generate-mockup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: productId,
          phase_submission_id: selectedSubmissionId,
          provider,
          prompt,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to generate mockup: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      alert(`${provider === 'v0' ? 'V0' : 'Lovable'} mockup generated successfully!`);
      
      // Trigger refresh of mockup gallery
      setMockupRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error(`Error generating ${provider} mockup:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (errorMessage.includes('API key is not configured')) {
        alert(`${provider === 'v0' ? 'V0' : 'Lovable'} API key is not configured. Please configure it in Settings.`);
      } else {
        alert(`Failed to generate ${provider} mockup: ${errorMessage}`);
      }
    } finally {
      setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: false });
    }
  };

  if (!isOpen) return null;

  const currentField = phase.required_fields[currentPromptIndex];
  const currentPrompt = phase.template_prompts[currentPromptIndex];
  const progress = ((currentPromptIndex + 1) / phase.template_prompts.length) * 100;
  
  // Compute design phase section flags (must be after currentField is defined)
  const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
  const isV0LovablePromptsSection = isDesignPhase && currentField === 'v0_lovable_prompts';
  const isDesignMockupsSection = isDesignPhase && currentField === 'design_mockups';

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
            {/* Special handling for Design phase - V0/Lovable Prompts Section */}
            {isV0LovablePromptsSection ? (
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-r-lg">
                  <Sparkles className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-blue-900 mb-1">
                      {currentPrompt}
                    </div>
                    <div className="text-xs text-blue-700">
                      Generate detailed prompts for V0 and Lovable. Use "Help with AI" to auto-generate contextualized prompts based on all previous phases.
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* V0 Prompt */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">V0 (Vercel) Prompt</label>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleGeneratePrompt('v0')}
                          disabled={isGeneratingPrompt.v0 || isSubmitting || !productId}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm flex items-center gap-1.5"
                        >
                          {isGeneratingPrompt.v0 ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Wand2 className="w-3 h-3" />
                              Help with AI
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                    <textarea
                      value={(() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                        return promptsObj['v0_prompt'] || '';
                      })()}
                      onChange={(e) => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : { v0_prompt: '', lovable_prompt: '' };
                        promptsObj['v0_prompt'] = e.target.value;
                        setFormData({
                          ...formData,
                          v0_lovable_prompts: JSON.stringify(promptsObj),
                        });
                      }}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      rows={10}
                      placeholder="V0 prompt will be generated here... Click 'Help with AI' to generate based on all previous phases"
                      disabled={isSubmitting || isGeneratingPrompt.v0}
                    />
                    <button
                      type="button"
                      onClick={() => handleGenerateMockup('v0')}
                      disabled={isGeneratingMockup.v0 || isSubmitting || !productId || (() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                        return !promptsObj['v0_prompt']?.trim();
                      })()}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                    >
                      {isGeneratingMockup.v0 ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Generating Mockup...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Generate V0 Mockup
                        </>
                      )}
                    </button>
                  </div>

                  {/* Lovable Prompt */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium text-gray-700">Lovable Prompt</label>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleGeneratePrompt('lovable')}
                          disabled={isGeneratingPrompt.lovable || isSubmitting || !productId}
                          className="px-3 py-1.5 text-xs font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm flex items-center gap-1.5"
                        >
                          {isGeneratingPrompt.lovable ? (
                            <>
                              <Loader2 className="w-3 h-3 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            <>
                              <Wand2 className="w-3 h-3" />
                              Help with AI
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                    <textarea
                      value={(() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                        return promptsObj['lovable_prompt'] || '';
                      })()}
                      onChange={(e) => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : { v0_prompt: '', lovable_prompt: '' };
                        promptsObj['lovable_prompt'] = e.target.value;
                        setFormData({
                          ...formData,
                          v0_lovable_prompts: JSON.stringify(promptsObj),
                        });
                      }}
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                      rows={10}
                      placeholder="Lovable prompt will be generated here... Click 'Help with AI' to generate based on all previous phases"
                      disabled={isSubmitting || isGeneratingPrompt.lovable}
                    />
                    <button
                      type="button"
                      onClick={() => handleGenerateMockup('lovable')}
                      disabled={isGeneratingMockup.lovable || isSubmitting || !productId || (() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                        return !promptsObj['lovable_prompt']?.trim();
                      })()}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                    >
                      {isGeneratingMockup.lovable ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Generating Mockup...
                        </>
                      ) : (
                        <>
                          <Play className="w-4 h-4" />
                          Generate Lovable Mockup
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ) : isDesignMockupsSection ? (
              /* Special handling for Design phase - Design Mockups Section */
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-r-lg">
                  <Sparkles className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-semibold text-blue-900 mb-1">
                      {currentPrompt}
                    </div>
                    <div className="text-xs text-blue-700">
                      View and select design mockups generated from V0 and Lovable. Click on thumbnails to expand.
                    </div>
                  </div>
                </div>
                {productId ? (
                  <DesignMockupGallery
                    productId={productId}
                    phaseSubmissionId={selectedSubmissionId}
                    refreshTrigger={mockupRefreshTrigger}
                    onSelectMockup={(mockup) => {
                      // Store selected mockup in form data
                      setFormData({
                        ...formData,
                        design_mockups: JSON.stringify({
                          selected_mockup_id: mockup.id,
                          selected_provider: mockup.provider,
                        }),
                      });
                    }}
                  />
                ) : (
                  <div className="text-center p-8 text-gray-500">
                    Product ID is required to view mockups
                  </div>
                )}
              </div>
            ) : (
              /* Standard form field */
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

                <div className="flex items-center justify-between mb-2">
                  <label
                    htmlFor={currentField}
                    className="block text-sm font-medium text-gray-700"
                  >
                    {currentField.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                  </label>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleAIHelp}
                      disabled={isGeneratingAIHelp || isSubmitting || !productId || !sessionId}
                      className="px-3 py-1.5 text-xs font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm flex items-center gap-1.5"
                      title="Get AI-generated content based on previous responses and conversation context"
                    >
                      {isGeneratingAIHelp ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Wand2 className="w-3 h-3" />
                          Help with AI
                        </>
                      )}
                    </button>
                    {formData[currentField]?.trim() && (
                      <button
                        type="button"
                        onClick={handleClear}
                        disabled={isSubmitting || isGeneratingAIHelp}
                        className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-1.5"
                        title="Clear this field"
                      >
                        <Trash2 className="w-3 h-3" />
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  id={currentField}
                  value={formData[currentField] || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, [currentField]: e.target.value })
                  }
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={8}
                  placeholder="Enter your detailed response here... or click 'Help with AI' to get AI-generated content based on your previous responses"
                  disabled={isSubmitting || isGeneratingAIHelp}
                />
                <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                  <span>{formData[currentField]?.length || 0} characters</span>
                  {isGeneratingAIHelp && (
                    <span className="text-purple-600 flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      AI is generating contextualized content...
                    </span>
                  )}
                </div>
              </div>
            )}

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
