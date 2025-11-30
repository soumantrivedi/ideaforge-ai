import { useState, useEffect } from 'react';
import { X, Send, Loader2, Sparkles, Wand2, Trash2, Play, Lightbulb, RefreshCw, CheckCircle2 } from 'lucide-react';
import type { LifecyclePhase } from '../lib/product-lifecycle-service';
import { lifecycleService } from '../lib/product-lifecycle-service';
import { DesignMockupGallery } from './DesignMockupGallery';
import { ThumbnailSelector } from './ThumbnailSelector';
import { useAuth } from '../contexts/AuthContext';
import { getValidatedApiUrl } from '../lib/runtime-config';
import { ErrorModal } from './ErrorModal';
import { ContentFormatter } from '../lib/content-formatter';
// Using regular textarea for phase form fields (plain text, not HTML)

const API_URL = getValidatedApiUrl();

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
  const [isStreamingAIHelp, setIsStreamingAIHelp] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [responseLength, setResponseLength] = useState<'short' | 'verbose'>('verbose');
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState<{v0: boolean, lovable: boolean}>({v0: false, lovable: false});
  const [isGeneratingMockup, setIsGeneratingMockup] = useState<{v0: boolean}>({v0: false});
  const [isCheckingStatus, setIsCheckingStatus] = useState<{v0: boolean}>({v0: false});
  const [v0PrototypeStatus, setV0PrototypeStatus] = useState<{
    status: 'not_submitted' | 'in_progress' | 'completed';
    project_url?: string;
    message?: string;
    project_id?: string;
    last_prompt?: string; // Track last submitted prompt to detect changes
  } | null>(null);
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | undefined>();
  const [errorModal, setErrorModal] = useState<{
    isOpen: boolean;
    error: {
      title: string;
      message: string;
      type?: 'quota' | 'rate_limit' | 'auth' | 'server' | 'network' | 'generic';
      actionUrl?: string;
      actionText?: string;
      onAction?: () => void;
    };
  }>({
    isOpen: false,
    error: { title: '', message: '' }
  });
  const [mockupRefreshTrigger, setMockupRefreshTrigger] = useState(0);
  const [lovableThumbnails, setLovableThumbnails] = useState<any[]>([]);
  const [showThumbnailSelector, setShowThumbnailSelector] = useState(false);
  const [promptScores, setPromptScores] = useState<{v0: number | null, lovable: number | null}>({v0: null, lovable: null});
  const [showSaveToChatbot, setShowSaveToChatbot] = useState(false);
  const [phaseRecommendations, setPhaseRecommendations] = useState<Array<{
    section: string;
    importance: string;
    recommendation: string;
  }>>([]);

  useEffect(() => {
    if (isOpen) {
      // Load recommendations if phase has been completed at least once
      const loadRecommendations = async () => {
        if (productId && phase.id && token) {
          try {
            const response = await fetch(`${API_URL}/api/products/${productId}/progress-report`, {
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
            });
            
            if (response.ok) {
              const data = await response.json();
              if (data.exists && data.missing_sections) {
                const phaseRecs = data.missing_sections.filter((section: any) => 
                  section.phase_id === phase.id
                );
                setPhaseRecommendations(phaseRecs);
              }
            }
          } catch (error) {
            console.error('Error loading recommendations:', error);
          }
        }
      };
      
      // Load existing submission data if available
      const loadExistingData = async () => {
        if (productId && phase.id && token) {
          try {
            lifecycleService.setToken(token);
            const submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
            
            // Load recommendations if phase is completed
            if (submission && (submission.status === 'completed' || submission.status === 'reviewed')) {
              loadRecommendations();
            }
            
            if (submission && submission.form_data) {
              // Merge existing form_data with any passed existingData
              const mergedData = { ...(existingData || {}), ...submission.form_data };
              
              // Initialize form data with existing data or empty strings
              const initialData: Record<string, string> = {};
              phase.required_fields.forEach((field) => {
                if (field === 'v0_lovable_prompts') {
                  // Initialize as JSON string for v0_lovable_prompts
                  const existing = mergedData[field];
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
                  // For all other fields, use existing data from submission
                  initialData[field] = mergedData[field] || existingData?.[field] || '';
                }
              });
              
              setFormData(initialData);
              
              // Calculate the appropriate starting index based on filled fields
              // Find the first unfilled field, or go to the last field if all are filled
              const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
              const fieldsToCheck = isDesignPhase 
                ? phase.required_fields.filter(f => f !== 'design_mockups')
                : phase.required_fields;
              
              let startingIndex = 0;
              for (let i = 0; i < fieldsToCheck.length; i++) {
                const field = fieldsToCheck[i];
                const value = initialData[field];
                if (!value || (typeof value === 'string' && value.trim().length === 0)) {
                  startingIndex = i;
                  break;
                }
                // If all fields are filled, show the last field
                if (i === fieldsToCheck.length - 1) {
                  startingIndex = Math.min(i, phase.required_fields.length - 1);
                }
              }
              
              setCurrentPromptIndex(startingIndex);
              
              console.log('Form initialized with existing submission data:', {
                phaseName: phase.phase_name,
                totalFields: phase.required_fields.length,
                fields: phase.required_fields,
                initialData,
                submissionId: submission.id,
                startingIndex,
              });
            } else {
              // No existing submission, initialize with empty values
              const initialData: Record<string, string> = {};
              phase.required_fields.forEach((field) => {
                if (field === 'v0_lovable_prompts') {
                  initialData[field] = JSON.stringify({ v0_prompt: '', lovable_prompt: '' });
                } else {
                  initialData[field] = existingData?.[field] || '';
                }
              });
              setFormData(initialData);
              setCurrentPromptIndex(0);
              console.log('Form initialized with no existing data:', {
                phaseName: phase.phase_name,
                totalFields: phase.required_fields.length,
                initialData,
              });
            }
          } catch (error) {
            console.error('Error loading existing submission:', error);
            // Fallback to existingData prop
            const initialData: Record<string, string> = {};
            phase.required_fields.forEach((field) => {
              if (field === 'v0_lovable_prompts') {
                initialData[field] = JSON.stringify({ v0_prompt: '', lovable_prompt: '' });
              } else {
                initialData[field] = existingData?.[field] || '';
              }
            });
            setFormData(initialData);
            setCurrentPromptIndex(0);
          }
        } else {
          // No productId or phase.id, use existingData prop only
          const initialData: Record<string, string> = {};
          phase.required_fields.forEach((field) => {
            if (field === 'v0_lovable_prompts') {
              initialData[field] = JSON.stringify({ v0_prompt: '', lovable_prompt: '' });
            } else {
              initialData[field] = existingData?.[field] || '';
            }
          });
          setFormData(initialData);
          setCurrentPromptIndex(0);
        }
      };
      
      loadExistingData();
    } else {
      // When modal closes, reset state to prevent stale data
      setFormData({});
      setCurrentPromptIndex(0);
      setIsGeneratingAIHelp(false);
      setIsSubmitting(false);
      setShowSaveToChatbot(false);
    }
  }, [isOpen, phase?.id, existingData, productId, token]);

  // Fix index bounds - must be in useEffect to avoid hooks order issues
  // Removed currentPromptIndex from dependencies to prevent infinite loops
  useEffect(() => {
    if (isOpen && phase.required_fields && phase.template_prompts) {
      const maxIndex = Math.min(phase.required_fields.length, phase.template_prompts.length) - 1;
      setCurrentPromptIndex((prevIndex) => {
        if (prevIndex > maxIndex) {
        console.warn('currentPromptIndex was out of bounds, correcting:', {
            old: prevIndex,
          new: maxIndex,
          max: maxIndex
        });
          return Math.max(0, maxIndex);
      }
        return prevIndex;
      });
    }
  }, [isOpen, phase.required_fields, phase.template_prompts]);

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
    
    // Validate all fields are filled (except design_mockups for Design phase)
    const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
    const fieldsToCheck = isDesignPhase 
      ? phase.required_fields.filter(f => f !== 'design_mockups')
      : phase.required_fields;
    
    const allRequiredFilled = fieldsToCheck.every((field) => formData[field]?.trim().length > 0);
    
    if (!allRequiredFilled) {
      const missingFields = fieldsToCheck.filter(field => !completeFormData[field]?.trim());
      alert(`Please fill in all required fields before generating. Missing: ${missingFields.map(f => f.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')).join(', ')}`);
      return;
    }
    
    setIsSubmitting(true);

    try {
      // Special handling for Design phase: Only save prompts, don't auto-generate prototypes
      // Users can refine prompts using "Help with AI" or manually, then save to chatbot separately
      if (isDesignPhase && completeFormData['v0_lovable_prompts']) {
        const promptsObj = JSON.parse(completeFormData['v0_lovable_prompts'] || '{}');
        // Just ensure the prompts are saved - no auto-generation of prototypes
        completeFormData['v0_lovable_prompts'] = JSON.stringify(promptsObj);
      }
      
      console.log('Submitting ALL form data from all pages:', completeFormData);
      await onSubmit(completeFormData);
      // For design phase, show save to chatbot option after saving
      if (isDesignPhase) {
        setShowSaveToChatbot(true);
      }
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

  const handleSaveToChatbot = async () => {
    if (!productId || !sessionId || !token) {
      alert('Product ID, Session ID, and authentication token are required');
      return;
    }

    setIsSubmitting(true);

    try {
      // Check if all required fields are filled
      const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
      let allFieldsFilled = false;
      
      if (isDesignPhase) {
        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts'] || '{}') : {};
        const v0Prompt = promptsObj['v0_prompt'] || '';
        const lovablePrompt = promptsObj['lovable_prompt'] || '';
        allFieldsFilled = v0Prompt.trim().length > 0 || lovablePrompt.trim().length > 0;
      } else {
        // Check all required fields except design_mockups
        const fieldsToCheck = phase.required_fields.filter(f => f !== 'design_mockups');
        allFieldsFilled = fieldsToCheck.every((field) => {
          const value = formData[field];
          if (!value) return false;
          if (field === 'v0_lovable_prompts') {
            try {
              const parsed = JSON.parse(value);
              return (parsed.v0_prompt?.trim() || parsed.lovable_prompt?.trim()) ? true : false;
            } catch {
              return false;
            }
          }
          return value.trim().length > 0;
        });
      }

      if (!allFieldsFilled) {
        alert('Please fill in all required fields before saving to chat');
          setIsSubmitting(false);
          return;
        }

      // Build the message to save to chatbot - format all form data nicely
      // Content will be rendered with markdown formatting in the chat interface
      let chatbotMessage = `## ${phase.phase_name} Phase Content\n\n`;
      
      if (isDesignPhase) {
        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts'] || '{}') : {};
        const v0Prompt = promptsObj['v0_prompt'] || '';
        const lovablePrompt = promptsObj['lovable_prompt'] || '';

        // Get the highest score (or prompt user to score if not scored)
        const maxScore = Math.max(
          promptScores.v0 || 0,
          promptScores.lovable || 0
        );

        if (maxScore === 0 && !promptScores.v0 && !promptScores.lovable) {
          const shouldScore = confirm('You haven\'t scored the prompts yet. Would you like to score them now? (Click Cancel to save without scoring)');
          if (shouldScore) {
            // Show scoring UI - we'll add this
            setIsSubmitting(false);
            return;
          }
        }
        
        if (v0Prompt.trim()) {
          // Clean any raw HTML tags but preserve markdown formatting
          const cleanV0Prompt = v0Prompt.replace(/<[^>]*>/g, '').trim();
          chatbotMessage += `### V0 Vercel Prompt\n${cleanV0Prompt}\n\n`;
          if (promptScores.v0 !== null) {
            chatbotMessage += `**Score: ${promptScores.v0}/5**\n\n`;
          }
        }
        
        if (lovablePrompt.trim()) {
          // Clean any raw HTML tags but preserve markdown formatting
          const cleanLovablePrompt = lovablePrompt.replace(/<[^>]*>/g, '').trim();
          chatbotMessage += `### Lovable.dev Prompt\n${cleanLovablePrompt}\n\n`;
          if (promptScores.lovable !== null) {
            chatbotMessage += `**Score: ${promptScores.lovable}/5**\n\n`;
          }
        }

        if (maxScore > 0) {
          chatbotMessage += `**Design Phase Score: ${maxScore}/5**\n\n`;
        }
      } else {
        // For all other phases, format all form fields nicely
        phase.required_fields.forEach((field, index) => {
          const fieldValue = formData[field] || '';
          if (fieldValue.trim()) {
            const prompt = phase.template_prompts?.[index] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            // Clean any raw HTML tags but preserve markdown formatting
            const cleanValue = fieldValue.replace(/<[^>]*>/g, '').trim();
            chatbotMessage += `### ${prompt}\n${cleanValue}\n\n`;
          }
        });
      }

      // Build interaction metadata
      const interactionMetadata: any = {
        phase_name: phase.phase_name,
      };
      
      if (isDesignPhase) {
        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts'] || '{}') : {};
        const maxScore = Math.max(
          promptScores.v0 || 0,
          promptScores.lovable || 0
        );
        interactionMetadata.v0_prompt = promptsObj['v0_prompt'] || '';
        interactionMetadata.lovable_prompt = promptsObj['lovable_prompt'] || '';
        interactionMetadata.v0_score = promptScores.v0;
        interactionMetadata.lovable_score = promptScores.lovable;
        if (maxScore > 0) {
          interactionMetadata.design_phase_score = maxScore;
        }
      }

      // Save to conversation history
      const response = await fetch(`${API_URL}/api/db/conversation-history`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          product_id: productId,
          phase_id: phase.id,
          message_type: 'agent',
          agent_name: `${phase.phase_name} Phase`,
          agent_role: phase.phase_name.toLowerCase().replace(/\s+/g, '_'),
          content: chatbotMessage,
          formatted_content: chatbotMessage,
          interaction_metadata: interactionMetadata,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to save to chatbot: ${response.status} - ${errorText}`);
      }

      // Update phase submission status to 'completed' since all fields are filled
      if (productId) {
        try {
          // First, ensure we have a submission - create or update it
          let submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
          
          if (!submission) {
            // Create submission if it doesn't exist
            await lifecycleService.submitPhaseData(productId, phase.id, formData, user?.id || '');
            submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
          }
          
          if (submission) {
            const metadata: any = {
              ...(submission.metadata || {}),
              saved_to_chatbot: true,
              saved_at: new Date().toISOString(),
              all_fields_completed: true,
            };
            
            // Add design phase specific scores if available
            if (isDesignPhase) {
              const maxScore = Math.max(
                promptScores.v0 || 0,
                promptScores.lovable || 0
              );
              if (maxScore > 0) {
                metadata.design_phase_score = maxScore;
                metadata.v0_score = promptScores.v0;
                metadata.lovable_score = promptScores.lovable;
                metadata.prompts_saved_to_chatbot = true;
              }
            }
            
            // Update status to 'completed' since all fields are filled and saved to chat
            await lifecycleService.updatePhaseContent(
              submission.id,
              submission.generated_content || chatbotMessage,
              'completed', // Mark as completed
              metadata
            );
          }
        } catch (error) {
          console.error('Error updating phase submission:', error);
          // Don't fail the whole operation if this fails
        }
      }

      // Dispatch event to update chatbot UI with phase info for follow-up question
      window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
        detail: {
          message: chatbotMessage,
          productId,
          phaseName: phase.phase_name,
          phaseId: phase.id,
          allFieldsCompleted: allFieldsFilled,
        }
      }));

      // Dispatch event to refresh submissions in parent
      window.dispatchEvent(new CustomEvent('phaseSubmissionUpdated', {
        detail: { productId, phaseId: phase.id }
      }));

      // Close modal first
      onClose();
      
      // Dispatch event to switch to chat view and focus chatbot
      window.dispatchEvent(new CustomEvent('navigateToChat', {
        detail: { 
          productId,
          focusChat: true  // Signal to focus the chat input
        }
      }));
    } catch (error) {
      console.error('Error saving to chat:', error);
      alert(`Failed to save to chat: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleNext = () => {
    const maxIndex = Math.min(
      (phase.required_fields?.length || 0) - 1,
      (phase.template_prompts?.length || 0) - 1
    );
    
    // For Design phase, skip question 3 (design_mockups) since prototypes are auto-generated
    const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
    let nextIndex = currentPromptIndex + 1;
    
    if (isDesignPhase && nextIndex <= maxIndex && nextIndex < phase.required_fields.length) {
      const nextField = phase.required_fields[nextIndex];
      // Skip design_mockups field (question 3) in Design phase
      if (nextField === 'design_mockups') {
        nextIndex = maxIndex; // Jump to last question (which will trigger submit)
      }
    }
    
    if (nextIndex <= maxIndex) {
      console.log('Navigating to next question:', {
        current: currentPromptIndex,
        next: nextIndex,
        max: maxIndex,
        totalFields: phase.required_fields?.length,
        totalPrompts: phase.template_prompts?.length,
        isDesignPhase,
        skippedDesignMockups: isDesignPhase && nextIndex < phase.required_fields.length && phase.required_fields[nextIndex] === 'design_mockups'
      });
      setCurrentPromptIndex(nextIndex);
    } else {
      console.warn('Cannot navigate next: already at last question', {
        current: currentPromptIndex,
        max: maxIndex
      });
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

    setIsGeneratingAIHelp(true);
    setIsStreamingAIHelp(true);
    setStreamingContent('');

    try {
      if (!user || !user.id) {
        throw new Error('User not authenticated. Please log in to use AI help.');
      }

      // Fetch conversation history for summary
      const conversationHistory = await lifecycleService.getProductConversationHistory(productId);
      
      // Generate conversation summary (last 5 messages)
      const { generateConversationSummary } = await import('../lib/phase-form-help-client');
      const conversationSummary = generateConversationSummary(conversationHistory);
      
      // Get user input if any
      const userInput = formData[currentField]?.trim() || undefined;
      
      // Use new single-agent phase form help endpoint
      const { streamPhaseFormHelp } = await import('../lib/phase-form-help-client');
      
      let accumulatedText = '';
      
      await streamPhaseFormHelp(
        {
          product_id: productId,
          phase_id: phase.id,
          phase_name: phase.phase_name,
          current_field: currentField,
          current_prompt: currentPrompt,
          user_input: userInput,
          response_length: responseLength,
          conversation_summary: conversationSummary || undefined,
        },
        token || '',
        {
          onChunk: (chunk: string, accumulated: string) => {
            accumulatedText = accumulated;
            setStreamingContent(accumulated);
            // Update form data in real-time with plain text content (use functional update)
            setFormData((prev) => ({
              ...prev,
              [currentField]: accumulated,
            }));
          },
          onComplete: (textContent: string, wordCount: number, agent: string) => {
            accumulatedText = textContent;
            setStreamingContent(''); // Clear streaming content
            // Save plain text to formData - use functional update to ensure we have latest state
            setFormData((prev) => ({
              ...prev,
              [currentField]: textContent,
            }));
            setIsStreamingAIHelp(false);
            setIsGeneratingAIHelp(false);
            console.log('Phase form help completed:', { wordCount, agent });
          },
          onError: (error: string) => {
            setIsStreamingAIHelp(false);
            setIsGeneratingAIHelp(false);
            throw new Error(error);
          },
        }
      );
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
      setIsStreamingAIHelp(false);
      setStreamingContent('');
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
    if (!user || !user.id) {
      alert('User not authenticated. Please log in to generate prompts.');
      return;
    }

    setIsGeneratingPrompt({ ...isGeneratingPrompt, [provider]: true });

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/api/design/generate-prompt`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          product_id: productId,
          phase_submission_id: selectedSubmissionId,
          provider,
          force_new: true, // Always generate new prompt when "Help with AI" is clicked
          context: {
            phase_name: phase.phase_name,
            form_data: formData,
            all_form_fields: phase.required_fields,
          },
        }),
      });

      if (!response.ok) {
        let errorText = '';
        let errorDetails: any = null;
        
        try {
          errorText = await response.text();
          try {
            errorDetails = JSON.parse(errorText);
          } catch {
            // Not JSON, use as is
          }
        } catch (e) {
          errorText = 'Unknown error occurred';
        }

        // Parse error details
        const errorMessage = errorDetails?.detail || errorText || 'Unknown error';
        const statusCode = response.status;

        // Determine error type and create user-friendly message
        let errorType: 'quota' | 'rate_limit' | 'auth' | 'server' | 'network' | 'generic' = 'generic';
        let title = 'Error Generating Prompt';
        let message = errorMessage;
        let actionUrl: string | undefined;
        let actionText: string | undefined;
        let onAction: (() => void) | undefined;

        // Check for quota/rate limit errors
        const errorLower = errorMessage.toLowerCase();
        if (errorLower.includes('quota') || errorLower.includes('exceeded') || errorLower.includes('insufficient_quota') || statusCode === 429) {
          errorType = 'quota';
          title = 'API Quota Exceeded';
          message = errorMessage.includes('OpenAI') 
            ? 'Your OpenAI API quota has been exceeded. Please check your billing details or try using another AI provider (Anthropic Claude or Google Gemini).'
            : errorMessage.includes('Anthropic') || errorMessage.includes('Claude')
            ? 'Your Anthropic Claude API quota has been exceeded. Please check your billing details or try using another AI provider (OpenAI or Google Gemini).'
            : errorMessage;
          actionUrl = errorMessage.includes('OpenAI') 
            ? 'https://platform.openai.com/account/billing'
            : errorMessage.includes('Anthropic') || errorMessage.includes('Claude')
            ? 'https://console.anthropic.com/settings/billing'
            : undefined;
          actionText = 'Check Billing';
          onAction = onNavigateToSettings ? () => {
            setErrorModal({ isOpen: false, error: { title: '', message: '' } });
            onNavigateToSettings();
          } : undefined;
        } else if (errorLower.includes('rate limit') || statusCode === 429) {
          errorType = 'rate_limit';
          title = 'Rate Limit Exceeded';
          message = 'Too many requests. Please wait a moment and try again.';
        } else if (statusCode === 401 || errorLower.includes('authentication') || errorLower.includes('unauthorized') || errorLower.includes('api key')) {
          errorType = 'auth';
          title = 'Authentication Error';
          message = errorMessage.includes('API key') 
            ? 'Your API key is invalid or expired. Please check your API keys in Settings.'
            : errorMessage;
          onAction = onNavigateToSettings ? () => {
            setErrorModal({ isOpen: false, error: { title: '', message: '' } });
            onNavigateToSettings();
          } : undefined;
          actionText = 'Go to Settings';
        } else if (statusCode >= 500 && statusCode < 600) {
          errorType = 'server';
          title = 'Server Error';
          message = errorMessage || 'An internal server error occurred. Please try again later or contact support if the problem persists.';
        } else if (statusCode === 0 || errorLower.includes('network') || errorLower.includes('fetch')) {
          errorType = 'network';
          title = 'Network Error';
          message = 'Unable to connect to the server. Please check your internet connection and try again.';
        } else {
          title = 'Error Generating Prompt';
          message = errorMessage || `An error occurred (${statusCode}). Please try again.`;
        }

        setErrorModal({
          isOpen: true,
          error: {
            title,
            message,
            type: errorType,
            actionUrl,
            actionText,
            onAction
          }
        });
        return;
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
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Check if error modal is already showing (from response parsing)
      if (!errorModal.isOpen) {
        setErrorModal({
          isOpen: true,
          error: {
            title: 'Error Generating Prompt',
            message: errorMessage,
            type: 'generic'
          }
        });
      }
    } finally {
      setIsGeneratingPrompt({ ...isGeneratingPrompt, [provider]: false });
    }
  };

  const handleCreateProject = async (provider: 'v0' | 'lovable', prompt: string) => {
    if (!productId || !sessionId) {
      alert('Product ID and Session ID are required');
      return;
    }
    if (!user || !user.id) {
      alert('User not authenticated. Please log in to create projects.');
      return;
    }
    if (!prompt.trim()) {
      alert(`Please generate a ${provider} prompt first using "Help with AI"`);
      return;
    }

    setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: true });

    try {

      // Use the new create-project endpoint with multi-agent enhancement
      const response = await fetch(`${API_URL}/api/design/create-project`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_id: productId,
          phase_submission_id: selectedSubmissionId,
          provider,
          prompt,
          use_multi_agent: true, // Use multi-agent to enhance prompt
          context: {
            phase_name: phase.phase_name,
            form_data: formData,
            all_form_fields: phase.required_fields,
          },
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to create project: ${response.status} - ${errorText}`);
      }

      const result = await response.json();

      // For V0, show the generated code and project URL
      if (provider === 'v0' && result.project_url) {
        const v0Message = `V0 (Vercel) project created!\n\n**Project URL:** ${result.project_url}\n\n**Enhanced Prompt Used:**\n${result.enhanced_prompt || prompt}\n\n${result.code ? `**Generated Code:**\n\`\`\`\n${result.code.substring(0, 1000)}${result.code.length > 1000 ? '...' : ''}\n\`\`\`\n` : ''}Click the project URL to view your prototype.`;

        window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
          detail: {
            message: v0Message,
            productId,
          }
        }));
        
        // Open project URL in new tab
        if (result.project_url) {
          window.open(result.project_url, '_blank');
        }
      }

      // For Lovable, open project URL if available
      if (provider === 'lovable' && result.project_url) {
        const lovableMessage = `Lovable AI project created!\n\n**Project URL:** ${result.project_url}\n\n**Enhanced Prompt Used:**\n${result.enhanced_prompt || prompt}\n\nClick the project URL to view your prototype.`;

        window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
          detail: {
            message: lovableMessage,
            productId,
          }
        }));
        
        // Open project URL in new tab
        const url = result.project_url;
        if (url && url.startsWith('http')) {
          const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
          if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            // Popup blocked, show alert with link
            alert(`Popup blocked. Please click this link to open the prototype:\n${url}`);
          }
        } else {
          alert(`Invalid prototype URL: ${url}`);
        }
      }

      alert(`${provider === 'v0' ? 'V0' : 'Lovable'} project created successfully! ${result.project_url ? 'Opening project in new tab...' : ''}`);

      // Trigger refresh of mockup gallery
      setMockupRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error(`Error creating ${provider} project:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (errorMessage.includes('API key is not configured')) {
        if (provider === 'v0') {
          alert('V0 API key is not configured. Please configure it in Settings.');
        } else {
          // Lovable doesn't require API key - it uses link generator
          // This should not be reached, but if it is, just continue
        }
      } else {
        alert(`Failed to create ${provider} project: ${errorMessage}`);
      }
    } finally {
      setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: false });
    }
  };

  const handleGenerateMockup = async (provider: 'v0' | 'lovable') => {
    if (!productId || !sessionId) {
      alert('Product ID and Session ID are required');
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
      
      // Lovable prototype generation removed - users will copy prompt and paste manually in lovable.dev
      if (provider === 'lovable') {
        alert('Please copy the Lovable prompt above and paste it manually into lovable.dev UI.');
        setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: false });
        return;
      }
      
      // For V0, use new two-step workflow: create-project then submit-chat
      // This ensures immediate projectId return without waiting for generation
      if (provider === 'v0') {
        // Step 1: Create/get project (returns projectId immediately)
        const createProjectResponse = await fetch(`${API_URL}/api/design/create-project`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_id: productId,
            phase_submission_id: selectedSubmissionId,
            provider: 'v0',
            prompt: prompt, // Prompt is optional for create-project, but we pass it for storage
            create_new: false, // Reuse existing project if available
            use_multi_agent: false, // Can be enabled later if needed
          }),
        });

        if (!createProjectResponse.ok) {
          const errorText = await createProjectResponse.text();
          throw new Error(`Failed to create V0 project: ${createProjectResponse.status} - ${errorText}`);
        }

        const projectResult = await createProjectResponse.json();
        const projectIdValue = projectResult.projectId || projectResult.v0_project_id;
        
        if (!projectIdValue) {
          throw new Error('Failed to get projectId from create-project response');
        }
        
        // Step 2: Submit chat to project (doesn't wait for response)
        const submitChatResponse = await fetch(`${API_URL}/api/design/submit-chat`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_id: productId,
            phase_submission_id: selectedSubmissionId,
            provider: 'v0',
            prompt: prompt,
            projectId: projectIdValue, // Use projectId (camelCase) to match V0 API format
          }),
        });

        if (!submitChatResponse.ok) {
          const errorText = await submitChatResponse.text();
          throw new Error(`Failed to submit chat: ${submitChatResponse.status} - ${errorText}`);
        }

        const chatResult = await submitChatResponse.json();
        
        // Update status - chat is submitted, status is in_progress
        setV0PrototypeStatus({
          status: 'in_progress',
          project_url: projectResult.project_url,
          project_id: projectIdValue,
          last_prompt: prompt, // Store last submitted prompt
          message: `V0 chat submitted! Project ID: ${projectIdValue}. Use "Check Status" to see when prototype is ready.`
        });
        
        // Show success message
        const v0Message = `V0 prototype request submitted!\n\n**Project ID:** ${projectIdValue}\n**Prompt Used:**\n${prompt}\n\nUse "Check Status" to see when your prototype is ready.`;
        
        window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
          detail: {
            message: v0Message,
            productId,
          }
        }));
      } else {
        // For Lovable, use generate-mockup endpoint
        const response = await fetch(`${API_URL}/api/design/generate-mockup`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
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
        // For Lovable, show the generated code and prompt
        if (result.code) {
          const lovableMessage = `Lovable prototype generated!\n\n**Prompt Used:**\n${prompt}\n\n**Generated Code:**\n\`\`\`\n${result.code.substring(0, 1000)}${result.code.length > 1000 ? '...' : ''}\n\`\`\`\n\nTo deploy: Create a new Lovable project and paste the generated code.`;
          
          window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
            detail: {
              message: lovableMessage,
              productId,
            }
          }));
        }
        
        // Open project URL if available
        if (result.project_url) {
          const url = result.project_url;
          if (url && url.startsWith('http')) {
            const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
            if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
              // Popup blocked, show alert with link
              alert(`Lovable mockup generated successfully!\n\nPopup blocked. Please click this link to open the prototype:\n${url}`);
            } else {
              alert(`Lovable mockup generated successfully! Opening project in new tab...`);
            }
          } else {
            alert(`Lovable mockup generated successfully! Invalid URL: ${url}`);
          }
        } else {
          alert(`Lovable mockup generated successfully!`);
        }
      }
      
      // Trigger refresh of mockup gallery
      setMockupRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error(`Error generating ${provider} mockup:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (errorMessage.includes('API key is not configured')) {
        if (provider === 'v0') {
          alert('V0 API key is not configured. Please configure it in Settings.');
        } else {
          // Lovable doesn't require API key - it uses link generator
          // This should not be reached, but if it is, just continue
        }
      } else {
        alert(`Failed to generate ${provider} mockup: ${errorMessage}`);
      }
    } finally {
      setIsGeneratingMockup({ ...isGeneratingMockup, [provider]: false });
    }
  };

  const handleCheckV0Status = async () => {
    if (!productId) {
      alert('Product ID is required');
      return;
    }

    setIsCheckingStatus({ ...isCheckingStatus, v0: true });

    try {
      // Build URL with optional projectId query parameter if available
      // V0 API doesn't know about product_id, so we pass projectId directly if we have it
      let checkStatusUrl = `${API_URL}/api/design/check-status/${productId}`;
      if (v0PrototypeStatus?.project_id) {
        checkStatusUrl += `?projectId=${encodeURIComponent(v0PrototypeStatus.project_id)}`;
      }
      
      // Use new check-status endpoint
      const response = await fetch(checkStatusUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // No project found - reset to not_submitted
          setV0PrototypeStatus({
            status: 'not_submitted',
            project_url: undefined,
            message: 'No V0 project found. Please generate a new prototype.'
          });
          setIsCheckingStatus({ ...isCheckingStatus, v0: false });
          return;
        }
        const errorText = await response.text();
        throw new Error(`Failed to check V0 status: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      
      // Map backend statuses to frontend statuses
      const projectStatus = result.project_status || 'unknown';
      let frontendStatus: 'not_submitted' | 'submitted' | 'in_progress' | 'completed';
      
      if (projectStatus === 'completed' || result.is_complete) {
        frontendStatus = 'completed';
      } else if (projectStatus === 'in_progress' || projectStatus === 'pending') {
        frontendStatus = 'in_progress';
      } else {
        frontendStatus = 'in_progress'; // Default to in_progress
      }
      
      // Use projectId (camelCase) from API response, fallback to project_id
      const projectIdValue = result.projectId || result.project_id;
      
      setV0PrototypeStatus({
        status: frontendStatus,
        project_url: result.project_url || result.demo_url || result.web_url,
        project_id: projectIdValue, // Store projectId from status check
        message: result.is_complete 
          ? 'Prototype is ready! Click the button above to open it.'
          : `Status: ${projectStatus}. Prototype is still being generated.`
      });

      // If completed, show success message
      if (result.is_complete && result.project_url) {
        const url = result.project_url;
        const shouldOpen = confirm(`V0 prototype is ready!\n\nWould you like to open it now?`);
        if (shouldOpen && url && url.startsWith('http')) {
          const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
          if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
            alert(`Popup blocked. Please click this link to open the prototype:\n${url}`);
          }
        }
      } else if (projectStatus === 'in_progress' || projectStatus === 'pending' || projectStatus === 'unknown') {
        // Show message for in-progress prototypes
        const statusMessage = projectStatus === 'pending' 
          ? 'V0 prototype request is pending and will start generating soon.'
          : projectStatus === 'in_progress'
          ? 'V0 prototype is currently being generated. This may take 10+ minutes.'
          : 'V0 prototype status is being checked. Please wait a moment and try again.';
        alert(`${statusMessage}\n\nStatus: ${projectStatus}\n\nPlease check again in a few minutes.`);
      }

      // Trigger refresh of mockup gallery
      setMockupRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error('Error checking V0 status:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      alert(`Failed to check V0 status: ${errorMessage}`);
    } finally {
      setIsCheckingStatus({ ...isCheckingStatus, v0: false });
    }
  };

  if (!isOpen) return null;

  // Safety checks for array bounds
  if (!phase.required_fields || !Array.isArray(phase.required_fields) || phase.required_fields.length === 0) {
    console.error('Phase has no required_fields:', phase);
    return null;
  }
  
  if (!phase.template_prompts || !Array.isArray(phase.template_prompts) || phase.template_prompts.length === 0) {
    console.error('Phase has no template_prompts:', phase);
    return null;
  }
  
  // Ensure arrays have same length
  if (phase.required_fields.length !== phase.template_prompts.length) {
    console.warn('Phase required_fields and template_prompts have different lengths:', {
      required_fields: phase.required_fields.length,
      template_prompts: phase.template_prompts.length,
      phase: phase.phase_name
    });
  }
  
  // Clamp currentPromptIndex to valid range (safe to use in render)
  const maxIndex = Math.min(phase.required_fields.length, phase.template_prompts.length) - 1;
  const safeIndex = Math.max(0, Math.min(currentPromptIndex, maxIndex));

  const currentField = phase.required_fields[safeIndex];
  const currentPrompt = phase.template_prompts[safeIndex];
  
  // Calculate progress based on filled fields, not just current index
  // This ensures progress doesn't reset when reopening a completed phase
  const filledFieldsCount = phase.required_fields.filter((field) => {
    const value = formData[field];
    if (!value) return false;
    if (field === 'v0_lovable_prompts') {
      try {
        const parsed = JSON.parse(value);
        return (parsed.v0_prompt?.trim() || parsed.lovable_prompt?.trim()) ? true : false;
      } catch {
        return false;
      }
    }
    return value.trim().length > 0;
  }).length;
  
  const totalFields = phase.required_fields.length;
  const progress = totalFields > 0 ? (filledFieldsCount / totalFields) * 100 : 0;
  
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
                      <strong>Step 1 - Generate Prompts:</strong> Click "Help with AI" to generate prompts for V0 and/or Lovable based on all previous phases. You can refine prompts manually or use "Help with AI" again to improve them.
                      <br /><br />
                      <strong>Step 2 - Generate Prototypes:</strong> Once you're satisfied with your prompts, click "Generate V0 Prototype" or "Generate Lovable Prototype" to create your design mockups. Prototypes are generated separately, so you can refine prompts before proceeding.
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Tab Navigation */}
                  <div className="flex gap-2 border-b border-gray-200">
                    <button
                      type="button"
                      onClick={() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : { v0_prompt: '', lovable_prompt: '' };
                        setFormData({
                          ...formData,
                          v0_lovable_prompts: JSON.stringify({ ...promptsObj, activeTab: 'v0' })
                        });
                      }}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                        (() => {
                          const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                          return promptsObj.activeTab !== 'lovable';
                        })()
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      V0 (Vercel) Prompt
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : { v0_prompt: '', lovable_prompt: '' };
                        setFormData({
                          ...formData,
                          v0_lovable_prompts: JSON.stringify({ ...promptsObj, activeTab: 'lovable' })
                        });
                      }}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition ${
                        (() => {
                          const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                          return promptsObj.activeTab === 'lovable';
                        })()
                          ? 'border-purple-500 text-purple-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      Lovable Prompt
                    </button>
                  </div>

                  {/* Stacked Content - Show active tab */}
                  {(() => {
                    const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                    const activeTab = promptsObj.activeTab || 'v0';
                    
                    return activeTab === 'v0' ? (
                      /* V0 Prompt */
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
                    {/* Prompt Quality Score */}
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600">Quality Score:</span>
                      {[1, 2, 3, 4, 5].map((score) => (
                        <button
                          key={score}
                          type="button"
                          onClick={() => setPromptScores({...promptScores, v0: score})}
                          className={`w-6 h-6 rounded-full border-2 transition ${
                            promptScores.v0 === score
                              ? 'bg-blue-600 border-blue-600 text-white'
                              : 'bg-white border-gray-300 text-gray-400 hover:border-blue-400'
                          }`}
                          disabled={isSubmitting}
                        >
                          {score}
                        </button>
                      ))}
                      {promptScores.v0 !== null && (
                        <span className="text-blue-600 font-medium">{promptScores.v0}/5</span>
                      )}
                    </div>
                           <button
                             type="button"
                             onClick={() => {
                               const status = v0PrototypeStatus?.status || 'not_submitted';
                               const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                               const currentPrompt = promptsObj['v0_prompt'] || '';
                               
                               // Check if prompt has changed from last submission
                               const promptChanged = v0PrototypeStatus?.last_prompt && v0PrototypeStatus.last_prompt !== currentPrompt;
                               
                               if (status === 'not_submitted' || promptChanged) {
                                 // Generate new prototype or submit new prompt to existing project
                                 handleGenerateMockup('v0');
                               } else if (status === 'in_progress') {
                                 // Check status
                                 handleCheckV0Status();
                               } else if (status === 'completed' && v0PrototypeStatus?.project_url) {
                                 // Open prototype URL in new window/tab
                                 const url = v0PrototypeStatus.project_url;
                                 if (url && url.startsWith('http')) {
                                   const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
                                   if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                                     // Popup blocked, show alert with link
                                     alert(`Popup blocked. Please click this link to open the prototype:\n${url}`);
                                   }
                                 } else {
                                   alert(`Invalid prototype URL: ${url}`);
                                 }
                               }
                             }}
                             disabled={(isGeneratingMockup.v0 || isCheckingStatus.v0 || isSubmitting || !productId || !sessionId) && (() => {
                               const status = v0PrototypeStatus?.status || 'not_submitted';
                               const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                               const currentPrompt = promptsObj['v0_prompt'] || '';
                               const promptChanged = v0PrototypeStatus?.last_prompt && v0PrototypeStatus.last_prompt !== currentPrompt;
                               
                               // Disable if no prompt and not submitting to existing project
                               if ((status === 'not_submitted' || promptChanged) && !currentPrompt.trim()) {
                                 return true;
                               }
                               return false;
                             })()}
                             className="w-full px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                           >
                             {(() => {
                               const status = v0PrototypeStatus?.status || 'not_submitted';
                               const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                               const currentPrompt = promptsObj['v0_prompt'] || '';
                               const promptChanged = v0PrototypeStatus?.last_prompt !== currentPrompt;
                               
                               if (isGeneratingMockup.v0) {
                                 return (
                                   <>
                                     <Loader2 className="w-4 h-4 animate-spin" />
                                     Submitting...
                                   </>
                                 );
                               } else if (isCheckingStatus.v0) {
                                 return (
                                   <>
                                     <Loader2 className="w-4 h-4 animate-spin" />
                                     Checking Status...
                                   </>
                                 );
                               } else if (status === 'completed' && !promptChanged) {
                                 return (
                                   <>
                                     <Play className="w-4 h-4" />
                                     Open Prototype
                                   </>
                                 );
                               } else if (status === 'in_progress' && !promptChanged) {
                                 return (
                                   <>
                                     <RefreshCw className="w-4 h-4" />
                                     Check Status
                                   </>
                                 );
                               } else {
                                 // Show "Generate V0 Prototype" if not submitted, or if prompt changed
                                 return (
                                   <>
                                     <Play className="w-4 h-4" />
                                     {promptChanged ? 'Submit New Prompt' : 'Generate V0 Prototype'}
                                   </>
                                 );
                               }
                             })()}
                           </button>
                           {v0PrototypeStatus && v0PrototypeStatus.status === 'in_progress' && (
                             <div className="text-xs text-blue-600 mt-2 flex items-center gap-2">
                               <Loader2 className="w-3 h-3 animate-spin" />
                               <span>{v0PrototypeStatus.message || 'Prototype is being generated. Click "Check Status" to see when it\'s ready.'}</span>
                             </div>
                           )}
                           {v0PrototypeStatus && v0PrototypeStatus.status === 'completed' && v0PrototypeStatus.project_url && (
                             <div className="text-xs text-green-600 mt-2 flex items-center gap-2">
                               <CheckCircle2 className="w-3 h-3" />
                               <span>Prototype is ready! Click the button above to open it.</span>
                             </div>
                           )}
                      </div>
                    ) : (
                      /* Lovable Prompt */
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
                    {/* Prompt Quality Score */}
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-600">Quality Score:</span>
                      {[1, 2, 3, 4, 5].map((score) => (
                        <button
                          key={score}
                          type="button"
                          onClick={() => setPromptScores({...promptScores, lovable: score})}
                          className={`w-6 h-6 rounded-full border-2 transition ${
                            promptScores.lovable === score
                              ? 'bg-purple-600 border-purple-600 text-white'
                              : 'bg-white border-gray-300 text-gray-400 hover:border-purple-400'
                          }`}
                          disabled={isSubmitting}
                        >
                          {score}
                        </button>
                      ))}
                      {promptScores.lovable !== null && (
                        <span className="text-purple-600 font-medium">{promptScores.lovable}/5</span>
                      )}
                    </div>
                           {/* Lovable Prototype button removed - users will copy prompt and paste manually in lovable.dev */}
                      </div>
                    );
                  })()}
                </div>
              </div>
            ) : isDesignMockupsSection ? (
              /* Special handling for Design phase - Design Mockups Section */
              <div className="space-y-6">
                {/* Prompts Section - Allow generating/regenerating prompts */}
                <div className="space-y-4">
                  <div className="flex items-start gap-3 p-4 bg-purple-50 border-l-4 border-purple-500 rounded-r-lg">
                    <Sparkles className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <div className="font-semibold text-purple-900 mb-1">
                        Generate V0 and Lovable Prompts
                      </div>
                      <div className="text-xs text-purple-700">
                        Generate or regenerate contextualized prompts for V0 and Lovable. These prompts will be used to create prototypes.
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* V0 Prompt */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-gray-700">V0 (Vercel) Prompt</label>
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
                              Generate
                            </>
                          )}
                        </button>
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
                        rows={8}
                        placeholder="V0 prompt will be generated here... Click 'Generate' to create based on all previous phases"
                        disabled={isSubmitting || isGeneratingPrompt.v0}
                      />
                    </div>

                    {/* Lovable Prompt */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm font-medium text-gray-700">Lovable Prompt</label>
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
                              Generate
                            </>
                          )}
                        </button>
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
                        rows={8}
                        placeholder="Lovable prompt will be generated here... Click 'Generate' to create based on all previous phases"
                        disabled={isSubmitting || isGeneratingPrompt.lovable}
                      />
                    </div>
                  </div>
                </div>

                {/* Mockups Section */}
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
                    {/* Response Length Radio Buttons */}
                    <div className="flex items-center gap-2 px-2 py-1 bg-gray-50 rounded-lg border border-gray-200">
                      <label className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                        <input
                          type="radio"
                          name="responseLength"
                          value="short"
                          checked={responseLength === 'short'}
                          onChange={(e) => setResponseLength(e.target.value as 'short' | 'verbose')}
                          disabled={isGeneratingAIHelp || isSubmitting}
                          className="w-3 h-3 text-purple-600 focus:ring-purple-500"
                        />
                        <span>Short</span>
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer">
                        <input
                          type="radio"
                          name="responseLength"
                          value="verbose"
                          checked={responseLength === 'verbose'}
                          onChange={(e) => setResponseLength(e.target.value as 'short' | 'verbose')}
                          disabled={isGeneratingAIHelp || isSubmitting}
                          className="w-3 h-3 text-purple-600 focus:ring-purple-500"
                        />
                        <span>Verbose</span>
                      </label>
                    </div>
                    <button
                      type="button"
                      onClick={handleAIHelp}
                      disabled={isGeneratingAIHelp || isSubmitting || !productId || !sessionId}
                      className="px-3 py-1.5 text-xs font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-sm flex items-center gap-1.5"
                      title="Get AI-generated content based on previous responses, all form data, conversation context, and RAG knowledge base"
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
                  value={isStreamingAIHelp && streamingContent ? streamingContent : (formData[currentField] || '')}
                  onChange={(e) => {
                    const value = e.target.value;
                    setFormData((prev) => ({ ...prev, [currentField]: value }));
                    if (isStreamingAIHelp) {
                      setStreamingContent(''); // Clear streaming content when user types
                    }
                  }}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  rows={8}
                  placeholder="Enter your detailed response here... or click 'Help with AI' to get AI-generated content based on your previous responses, conversation history, and all phase data"
                  disabled={isSubmitting || isGeneratingAIHelp}
                />
                <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
                  <span>{formData[currentField]?.length || 0} characters</span>
                  {(isGeneratingAIHelp || isStreamingAIHelp) && (
                    <span className="text-purple-600 flex items-center gap-1">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      {isStreamingAIHelp ? 'AI is streaming contextualized content...' : 'AI is generating contextualized content...'}
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

            {(() => {
              const maxIndex = Math.min(
                (phase.required_fields?.length || 0) - 1,
                (phase.template_prompts?.length || 0) - 1
              );
              const isLastQuestion = currentPromptIndex >= maxIndex;
              
              // For Design phase, show "Save to Chatbot" on question 2 (v0_lovable_prompts)
              const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
              const isV0LovableQuestion = isDesignPhase && currentField === 'v0_lovable_prompts';
              const isDesignMockupsQuestion = isDesignPhase && currentField === 'design_mockups';
              const shouldShowSaveButton = isDesignPhase && isV0LovableQuestion;
              const shouldShowGenerateButton = !isDesignPhase && (isLastQuestion || isDesignMockupsQuestion);
              
              // For Design phase, show "Save to Chatbot" button
              if (shouldShowSaveButton) {
                const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts'] || '{}') : {};
                const hasPrompts = promptsObj['v0_prompt']?.trim() || promptsObj['lovable_prompt']?.trim();
                const isButtonDisabled = !hasPrompts || isSubmitting;
                
                return (
                  <button
                    type="button"
                    onClick={handleSaveToChatbot}
                    disabled={isButtonDisabled}
                    className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg flex items-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving to Chat...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Save to Chat
                      </>
                    )}
                  </button>
                );
              }
              
              if (shouldShowGenerateButton) {
                // For design_mockups, check if prompts are filled; for other fields, check current field
                const isButtonDisabled = isDesignMockupsQuestion 
                  ? (() => {
                      const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts'] || '{}') : {};
                      return !promptsObj['v0_prompt']?.trim() || !promptsObj['lovable_prompt']?.trim();
                    })()
                  : !isCurrentFieldFilled();
                
                // "Save To Chat" button - saves form content to chat WITHOUT triggering multi-agent processing
                return (
                  <button
                    type="button"
                    onClick={async () => {
                      // First save the form data
                      try {
                        await handleSubmit(new Event('submit') as any);
                        // Then save to chat
                        await handleSaveToChatbot();
                      } catch (error) {
                        console.error('Error saving form and chat:', error);
                        alert(`Failed to save: ${error instanceof Error ? error.message : 'Unknown error'}`);
                      }
                    }}
                    disabled={isButtonDisabled || isSubmitting}
                    className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg hover:from-green-700 hover:to-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg flex items-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Saving to Chat...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Save To Chat
                      </>
                    )}
                  </button>
                );
              }
              
              return (
                <button
                  type="button"
                  onClick={handleNext}
                  disabled={!isCurrentFieldFilled() || isSubmitting}
                  className="px-6 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg"
                >
                  Next
                </button>
              );
            })()}
        </div>
      </form>

      {/* Recommendations Section - Only show if phase has been completed at least once */}
      {phaseRecommendations.length > 0 && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-5 h-5 text-yellow-600" />
            <h3 className="font-semibold text-yellow-900">Recommendations for Improvement</h3>
          </div>
          <div className="space-y-3">
            {phaseRecommendations.map((rec, idx) => (
              <div key={idx} className="bg-white rounded-lg p-3 border border-yellow-100">
                <h4 className="font-medium text-gray-900 mb-1 text-sm">{rec.section}</h4>
                <p className="text-xs text-gray-700 mb-2">{rec.importance}</p>
                <p className="text-sm font-medium text-yellow-800">💡 {rec.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Thumbnail Selector Modal for Lovable */}
      {showThumbnailSelector && lovableThumbnails.length > 0 && (
        <ThumbnailSelector
          previews={lovableThumbnails}
          isOpen={showThumbnailSelector}
          onClose={() => {
            setShowThumbnailSelector(false);
            setLovableThumbnails([]);
            setIsGeneratingMockup({ ...isGeneratingMockup, lovable: false });
          }}
          onSelect={async (selectedIndex: number) => {
            try {
              const selectedPreview = lovableThumbnails[selectedIndex];
              
              // Get prompt from formData or selectedPreview
              const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
              const prompt = selectedPreview.prompt || promptsObj['lovable_prompt'] || '';
              
              if (!prompt.trim()) {
                alert('Prompt is required to generate mockup');
                return;
              }
              
              // Generate full mockup with selected preview
              const response = await fetch(`${API_URL}/api/design/generate-mockup`, {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  product_id: productId,
                  phase_submission_id: selectedSubmissionId,
                  provider: 'lovable',
                  prompt: prompt,
                }),
              });

              if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to generate mockup: ${response.status} - ${errorText}`);
              }

              const result = await response.json();
              
              // Open Lovable project in browser if URL is available
              if (result.project_url) {
                const url = result.project_url;
                if (url && url.startsWith('http')) {
                  const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
                  if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                    // Popup blocked, show alert with link
                    alert(`Popup blocked. Please click this link to open the prototype:\n${url}`);
                  }
                } else {
                  alert(`Invalid prototype URL: ${url}`);
                }
              }
              
              // Send to chatbot
              window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
                detail: {
                  message: `Lovable AI prototype generated!\n\n**Selected Design Option ${selectedIndex + 1}**\n\nPrompt Used:\n${prompt}\n\nProject URL: ${result.project_url || 'N/A'}\n\nThumbnail: ${selectedPreview.thumbnail_url || 'N/A'}`,
                  productId,
                }
              }));
              
              alert(`Lovable mockup generated successfully! ${result.project_url ? 'Opening project in new tab...' : ''}`);
              
              // Close selector and refresh gallery
              setShowThumbnailSelector(false);
              setLovableThumbnails([]);
              setMockupRefreshTrigger(prev => prev + 1);
            } catch (error) {
              console.error('Error generating selected Lovable mockup:', error);
              alert(`Failed to generate mockup: ${error instanceof Error ? error.message : 'Unknown error'}`);
            } finally {
              setIsGeneratingMockup({ ...isGeneratingMockup, lovable: false });
            }
          }}
          provider="lovable"
        />
      )}
      
      {/* Error Modal */}
      <ErrorModal
        isOpen={errorModal.isOpen}
        onClose={() => setErrorModal({ isOpen: false, error: { title: '', message: '' } })}
        error={errorModal.error}
      />
    </div>
  </div>
);
}

