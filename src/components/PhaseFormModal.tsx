import { useState, useEffect } from 'react';
import { X, Send, Loader2, Sparkles, Wand2, Trash2, Play } from 'lucide-react';
import type { LifecyclePhase } from '../lib/product-lifecycle-service';
import { lifecycleService } from '../lib/product-lifecycle-service';
import { DesignMockupGallery } from './DesignMockupGallery';
import { ThumbnailSelector } from './ThumbnailSelector';
import { useAuth } from '../contexts/AuthContext';
import { getValidatedApiUrl } from '../lib/runtime-config';

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
  const [responseLength, setResponseLength] = useState<'short' | 'verbose'>('verbose');
  const [isGeneratingPrompt, setIsGeneratingPrompt] = useState<{v0: boolean, lovable: boolean}>({v0: false, lovable: false});
  const [isGeneratingMockup, setIsGeneratingMockup] = useState<{v0: boolean, lovable: boolean}>({v0: false, lovable: false});
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<string | undefined>();
  const [mockupRefreshTrigger, setMockupRefreshTrigger] = useState(0);
  const [lovableThumbnails, setLovableThumbnails] = useState<any[]>([]);
  const [showThumbnailSelector, setShowThumbnailSelector] = useState(false);
  const [promptScores, setPromptScores] = useState<{v0: number | null, lovable: number | null}>({v0: null, lovable: null});
  const [showSaveToChatbot, setShowSaveToChatbot] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Load existing submission data if available
      const loadExistingData = async () => {
        if (productId && phase.id && token) {
          try {
            const { lifecycleService } = await import('../lib/product-lifecycle-service');
            lifecycleService.setToken(token);
            const submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
            
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
              console.log('Form initialized with existing submission data:', {
                phaseName: phase.phase_name,
                totalFields: phase.required_fields.length,
                fields: phase.required_fields,
                initialData,
                submissionId: submission.id,
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
        }
      };
      
      loadExistingData();
      setCurrentPromptIndex(0);
    }
  }, [isOpen, phase, existingData, productId, token]);

  // Fix index bounds - must be in useEffect to avoid hooks order issues
  useEffect(() => {
    if (isOpen && phase.required_fields && phase.template_prompts) {
      const maxIndex = Math.min(phase.required_fields.length, phase.template_prompts.length) - 1;
      if (currentPromptIndex > maxIndex) {
        console.warn('currentPromptIndex was out of bounds, correcting:', {
          old: currentPromptIndex,
          new: maxIndex,
          max: maxIndex
        });
        setCurrentPromptIndex(Math.max(0, maxIndex));
      }
    }
  }, [isOpen, phase.required_fields, phase.template_prompts, currentPromptIndex]);

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

    const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
    const v0Prompt = promptsObj['v0_prompt'] || '';
    const lovablePrompt = promptsObj['lovable_prompt'] || '';

      if (!v0Prompt.trim() && !lovablePrompt.trim()) {
      alert('Please generate at least one prompt (V0 or Lovable) before saving to chat');
      return;
    }

    // Get the highest score (or prompt user to score if not scored)
    const maxScore = Math.max(
      promptScores.v0 || 0,
      promptScores.lovable || 0
    );

    if (maxScore === 0 && !promptScores.v0 && !promptScores.lovable) {
      const shouldScore = confirm('You haven\'t scored the prompts yet. Would you like to score them now? (Click Cancel to save without scoring)');
      if (shouldScore) {
        // Show scoring UI - we'll add this
        return;
      }
    }

    setIsSubmitting(true);

    try {
      // Build the message to save to chatbot
      let chatbotMessage = `## Design Phase Prompts\n\n`;
      
      if (v0Prompt.trim()) {
        chatbotMessage += `### V0 Vercel Prompt\n${v0Prompt}\n\n`;
        if (promptScores.v0 !== null) {
          chatbotMessage += `**Score: ${promptScores.v0}/5**\n\n`;
        }
      }
      
      if (lovablePrompt.trim()) {
        chatbotMessage += `### Lovable.dev Prompt\n${lovablePrompt}\n\n`;
        if (promptScores.lovable !== null) {
          chatbotMessage += `**Score: ${promptScores.lovable}/5**\n\n`;
        }
      }

      if (maxScore > 0) {
        chatbotMessage += `**Design Phase Score: ${maxScore}/5**\n`;
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
          agent_name: 'Design Phase',
          agent_role: 'design',
          content: chatbotMessage,
          formatted_content: chatbotMessage,
          interaction_metadata: {
            phase_name: phase.phase_name,
            v0_prompt: v0Prompt,
            lovable_prompt: lovablePrompt,
            v0_score: promptScores.v0,
            lovable_score: promptScores.lovable,
            design_phase_score: maxScore,
          },
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to save to chatbot: ${response.status} - ${errorText}`);
      }

      // Dispatch event to update chatbot UI
      window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
        detail: {
          message: chatbotMessage,
          productId,
        }
      }));

      // Update phase submission with score
      if (maxScore > 0 && productId) {
        try {
          const submission = await lifecycleService.getPhaseSubmission(productId, phase.id);
          if (submission) {
            const metadata = {
              ...(submission.metadata || {}),
              design_phase_score: maxScore,
              v0_score: promptScores.v0,
              lovable_score: promptScores.lovable,
              prompts_saved_to_chatbot: true,
              saved_at: new Date().toISOString(),
            };
            await lifecycleService.updatePhaseContent(
              submission.id,
              submission.generated_content || '',
              submission.status || 'completed',
              metadata
            );
          }
        } catch (error) {
          console.error('Error updating phase submission with score:', error);
          // Don't fail the whole operation if this fails
        }
      }

      // Close modal first to prevent UI distortion
      onClose();
      setShowSaveToChatbot(false);
      
      // Show success message after a brief delay to ensure modal is closed
      setTimeout(() => {
        alert('Prompts saved to chat successfully!');
      }, 100);
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
    
    // Compute design phase section flags here
    const isDesignPhase = phase.phase_name.toLowerCase() === 'design';
    const isV0LovablePromptsSection = isDesignPhase && currentField === 'v0_lovable_prompts';
    const isDesignMockupsSection = isDesignPhase && currentField === 'design_mockups';

    setIsGeneratingAIHelp(true);

    try {
      if (!user || !user.id) {
        throw new Error('User not authenticated. Please log in to use AI help.');
      }

      
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

      // Build industry standards context
      const industryStandardsContext = [
        '## Industry Standards & Best Practices',
        '',
        'Please ensure the response follows industry standards from:',
        '- BCS (British Computer Society) Product Management Framework',
        '- ICAgile (International Consortium for Agile) Product Ownership',
        '- AIPMM (Association of International Product Marketing and Management)',
        '- Pragmatic Institute Product Management Framework',
        '- McKinsey CodeBeyond standards',
        '',
        'The response should be:',
        '- Professional and industry-standard compliant',
        '- Well-structured and comprehensive',
        '- Actionable and measurable',
        '- Aligned with best practices',
        '',
        '---',
        '',
      ].join('\n');

      // Build response length instruction
      const lengthInstruction = responseLength === 'short' 
        ? 'Please provide a concise, focused response (2-3 paragraphs maximum). Be direct and to the point while maintaining quality and relevance.'
        : 'Please provide a comprehensive, detailed response with full context, examples, and thorough explanations. Include all relevant details and industry best practices.';

      // Build the main prompt with all form data context
      const allFormDataContext = Object.entries(formData)
        .filter(([key, value]) => key !== currentField && value?.trim())
        .map(([key, value]) => {
          const fieldName = key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
          return `- **${fieldName}**: ${value.substring(0, 500)}${value.length > 500 ? '...' : ''}`;
        });

      const formDataSection = allFormDataContext.length > 0
        ? [
            '## Current Form Data (All Fields)',
            '',
            'The following information has already been provided in this form:',
            '',
            ...allFormDataContext,
            '',
            'Use this information to ensure consistency and build upon what has already been provided.',
            '',
            '---',
            '',
          ].join('\n')
        : '';

      const mainPrompt = [
        `I'm working on the "${phase.phase_name}" phase of my product lifecycle.`,
        '',
        'Based on all the context provided above (previous conversations, previous phases, all form data, and knowledge base),',
        `please help me generate a ${responseLength === 'short' ? 'concise' : 'comprehensive and detailed'} response for the following question:`,
        '',
        `**Question**: ${currentPrompt}`,
        '',
        `**Field**: ${currentField.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}`,
        '',
        lengthInstruction,
        '',
        'Please generate a well-structured response that:',
        '- Takes into account ALL previous information, conversations, and form data',
        '- Leverages knowledge from the RAG knowledge base',
        '- Is specific and relevant to the product being developed',
        '- Provides actionable and comprehensive information',
        '- Maintains consistency with previously provided information',
        '- Follows industry standards and best practices',
        '- Is professional and well-formatted',
        '',
        'Generate only the content for this specific field, without repeating the question or adding extra formatting.',
      ].join('\n');

      const fullPrompt = [
        ...contextParts,
        formDataSection,
        industryStandardsContext,
        mainPrompt,
      ].join('\n');

      // Call multi-agent API (API_URL already defined above)
      
      // Determine which agents to use based on phase and field
      // ALWAYS include RAG agent for knowledge base context
      let primaryAgent = 'ideation';
      let supportingAgents: string[] = ['rag']; // RAG is always first
      
      // Special handling for Design phase - V0/Lovable prompts
      if (isV0LovablePromptsSection) {
        primaryAgent = 'strategy';
        supportingAgents = ['rag', 'analysis', 'ideation'];
      } else if (phase.phase_name.toLowerCase().includes('research')) {
        primaryAgent = 'research';
        supportingAgents = ['rag', 'analysis', 'strategy'];
      } else if (phase.phase_name.toLowerCase().includes('requirement')) {
        primaryAgent = 'analysis';
        supportingAgents = ['rag', 'research'];
      } else if (phase.phase_name.toLowerCase().includes('design')) {
        primaryAgent = 'strategy';
        supportingAgents = ['rag', 'analysis', 'ideation'];
      } else if (phase.phase_name.toLowerCase().includes('development')) {
        primaryAgent = 'prd_authoring';
        supportingAgents = ['rag', 'analysis'];
      } else if (phase.phase_name.toLowerCase().includes('market')) {
        primaryAgent = 'research';
        supportingAgents = ['rag', 'analysis'];
      } else {
        // Default: always include RAG
        supportingAgents = ['rag', 'research', 'analysis'];
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
          coordination_mode: 'enhanced_collaborative', // Always use enhanced collaborative for heavy contextualization
          primary_agent: primaryAgent,
          supporting_agents: supportingAgents, // RAG is always included
          context: {
            product_id: productId,
            phase_id: phase.id,
            phase_name: phase.phase_name,
            current_field: currentField,
            current_prompt: currentPrompt,
            form_data: formData, // Include all form data
            all_form_fields: phase.required_fields,
            response_length: responseLength,
            industry_standards: true,
          },
        }),
      });

      if (!response.ok) {
        let errorMessage = `Failed to generate AI help: ${response.status}`;
        let errorDetails: any = null;
        
        try {
          const errorText = await response.text();
          try {
            errorDetails = JSON.parse(errorText);
            if (errorDetails.detail) {
              // Handle Pydantic validation errors
              if (typeof errorDetails.detail === 'object' && Array.isArray(errorDetails.detail)) {
                const validationErrors = errorDetails.detail.map((err: any) => {
                  const field = err.loc ? err.loc.join('.') : 'unknown';
                  const msg = err.msg || 'validation error';
                  return `${field}: ${msg}`;
                }).join(', ');
                errorMessage = `Validation error: ${validationErrors}`;
              } else if (typeof errorDetails.detail === 'string') {
                errorMessage = errorDetails.detail;
              } else {
                errorMessage = JSON.stringify(errorDetails.detail);
              }
            } else if (errorDetails.message) {
              errorMessage = errorDetails.message;
            }
          } catch {
            // If errorText is not JSON, use it as is
            if (errorText.includes('No AI provider configured')) {
              errorMessage = 'No AI provider is configured on the backend. Please go to Settings and configure at least one AI provider (OpenAI, Anthropic, or Google Gemini) before using "Help with AI".';
            } else {
              errorMessage = `${errorMessage} - ${errorText}`;
            }
          }
        } catch (e) {
          console.error('Error parsing error response:', e);
        }
        
        console.error('AI Help API error:', {
          status: response.status,
          statusText: response.statusText,
          error: errorMessage,
          details: errorDetails
        });
        
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
          context: {
            phase_name: phase.phase_name,
            form_data: formData,
            all_form_fields: phase.required_fields,
          },
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
        window.open(result.project_url, '_blank');
      }

      alert(`${provider === 'v0' ? 'V0' : 'Lovable'} project created successfully! ${result.project_url ? 'Opening project in new tab...' : ''}`);

      // Trigger refresh of mockup gallery
      setMockupRefreshTrigger(prev => prev + 1);
    } catch (error) {
      console.error(`Error creating ${provider} project:`, error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (errorMessage.includes('API key is not configured')) {
        alert(`${provider === 'v0' ? 'V0' : 'Lovable'} API key is not configured. Please configure it in Settings.`);
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
      
      // For Lovable, generate 3 thumbnail previews first
      if (provider === 'lovable') {
        const thumbnailsResponse = await fetch(`${API_URL}/api/design/generate-thumbnails`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            product_id: productId,
            phase_submission_id: selectedSubmissionId,
            lovable_prompt: prompt,
            num_previews: 3,
          }),
        });

        if (thumbnailsResponse.ok) {
          const thumbnailsData = await thumbnailsResponse.json();
          const previews = thumbnailsData.previews || [];
          
          if (previews.length > 0) {
            // Show thumbnail selector
            setLovableThumbnails(previews);
            setShowThumbnailSelector(true);
            // Don't set loading to false here - let the ThumbnailSelector's onSelect handle it
            // The ThumbnailSelector will handle the rest when user confirms selection
            return; // The ThumbnailSelector will handle the rest
          }
        }
      }
      
      // For V0 or if Lovable thumbnails failed, generate directly
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
      
      // For V0, show the generated code and prompt
      if (provider === 'v0' && result.code) {
        const v0Message = `V0 (Vercel) prototype generated!\n\n**Prompt Used:**\n${prompt}\n\n**Generated Code:**\n\`\`\`\n${result.code.substring(0, 1000)}${result.code.length > 1000 ? '...' : ''}\n\`\`\`\n\nTo deploy: Create a new Vercel project and paste the generated code.`;
        
        window.dispatchEvent(new CustomEvent('phaseFormGenerated', {
          detail: {
            message: v0Message,
            productId,
          }
        }));
      }
      
      // For Lovable, open project URL if available
      if (provider === 'lovable' && result.project_url) {
        window.open(result.project_url, '_blank');
      }
      
      alert(`${provider === 'v0' ? 'V0' : 'Lovable'} mockup generated successfully! ${provider === 'lovable' && result.project_url ? 'Opening project in new tab...' : ''}`);
      
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
  const progress = ((safeIndex + 1) / Math.max(phase.required_fields.length, phase.template_prompts.length)) * 100;
  
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
                             onClick={() => handleGenerateMockup('v0')}
                             disabled={isGeneratingMockup.v0 || isSubmitting || !productId || !sessionId || (() => {
                               const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                               return !promptsObj['v0_prompt']?.trim();
                             })()}
                             className="w-full px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                           >
                             {isGeneratingMockup.v0 ? (
                               <>
                                 <Loader2 className="w-4 h-4 animate-spin" />
                                 Generating V0 Prototype...
                               </>
                             ) : (
                               <>
                                 <Play className="w-4 h-4" />
                                 Generate V0 Prototype
                               </>
                             )}
                           </button>
                           {isGeneratingMockup.v0 && (
                             <div className="text-xs text-blue-600 mt-2 flex items-center gap-2">
                               <Loader2 className="w-3 h-3 animate-spin" />
                               <span>Please wait while V0 generates your prototype. The prompt used will be shown in the chatbot.</span>
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
                           <button
                             type="button"
                             onClick={() => handleGenerateMockup('lovable')}
                             disabled={isGeneratingMockup.lovable || isSubmitting || !productId || !sessionId || (() => {
                               const promptsObj = formData['v0_lovable_prompts'] ? JSON.parse(formData['v0_lovable_prompts']) : {};
                               return !promptsObj['lovable_prompt']?.trim();
                             })()}
                             className="w-full px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-purple-600 to-pink-600 rounded-lg hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
                           >
                             {isGeneratingMockup.lovable ? (
                               <>
                                 <Loader2 className="w-4 h-4 animate-spin" />
                                 Generating Prototypes...
                               </>
                             ) : (
                               <>
                                 <Play className="w-4 h-4" />
                                 Generate Lovable Prototype (3 Options)
                               </>
                             )}
                           </button>
                           {isGeneratingMockup.lovable && (
                             <div className="text-xs text-purple-600 mt-2 flex items-center gap-2">
                               <Loader2 className="w-3 h-3 animate-spin" />
                               <span>Generating 3 design variations. Please wait and select your preferred option when ready. The selected prototype will open in your browser.</span>
                             </div>
                           )}
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
                
                return (
                  <button
                    type="submit"
                    disabled={isButtonDisabled || isSubmitting}
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
                window.open(result.project_url, '_blank');
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
    </div>
  </div>
);
}
