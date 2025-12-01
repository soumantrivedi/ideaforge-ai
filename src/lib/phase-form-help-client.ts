/**
 * Client for phase form help streaming API.
 * Provides smooth streaming of HTML-formatted responses for phase form questions.
 */
import { getValidatedApiUrl } from './runtime-config';

const API_URL = getValidatedApiUrl();

export interface PhaseFormHelpRequest {
  product_id: string;
  phase_id: string;
  phase_name: string;
  current_field: string;
  current_prompt: string;
  user_input?: string;
  response_length: 'short' | 'verbose';
  conversation_summary?: string;
}

export interface PhaseFormHelpCallbacks {
  onChunk?: (chunk: string, accumulated: string) => void;
  onComplete?: (htmlContent: string, wordCount: number, agent: string) => void;
  onError?: (error: string) => void;
}

/**
 * Stream phase form help response from the backend.
 */
export async function streamPhaseFormHelp(
  request: PhaseFormHelpRequest,
  token: string,
  callbacks: PhaseFormHelpCallbacks
): Promise<void> {
  const response = await fetch(`${API_URL}/api/phase-form-help/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorText = await response.text();
    callbacks.onError?.(`Failed to stream phase form help: ${response.status} - ${errorText}`);
    return;
  }

  if (!response.body) {
    callbacks.onError?.('Response body is null');
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let accumulatedHtml = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.type === 'chunk') {
              accumulatedHtml += data.content;
              callbacks.onChunk?.(data.content, accumulatedHtml);
            } else if (data.type === 'complete') {
              accumulatedHtml = data.content;
              callbacks.onComplete?.(data.content, data.word_count || 0, data.agent || 'unknown');
              return;
            } else if (data.type === 'error') {
              callbacks.onError?.(data.error || 'Unknown error occurred');
              return;
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, line);
            // If we can't parse the JSON, try to extract error message from the line
            if (line.includes('error') || line.includes('Error')) {
              const errorMatch = line.match(/error["\s:]+(.+?)(?:"|$)/i);
              if (errorMatch) {
                callbacks.onError?.(errorMatch[1] || 'Error parsing response data');
                return;
              }
            }
            // If it's a JSON parse error but we have the raw line, pass it through
            if (e instanceof SyntaxError && line) {
              callbacks.onError?.(`Error parsing response: ${line.slice(6)}`);
              return;
            }
          }
        }
      }
    }
  } catch (error) {
    callbacks.onError?.(error instanceof Error ? error.message : 'Unknown error occurred');
  } finally {
    reader.releaseLock();
  }
}

/**
 * Generate a conversation summary from conversation history.
 */
export function generateConversationSummary(conversationHistory: Array<{
  message_type: string;
  content: string;
  agent_name?: string;
}>): string {
  if (conversationHistory.length === 0) {
    return '';
  }

  // Take last 5 messages and create a summary
  const recentMessages = conversationHistory.slice(-5);
  const summaryParts: string[] = [];

  recentMessages.forEach((entry) => {
    if (entry.message_type === 'user' || entry.message_type === 'agent') {
      const role = entry.message_type === 'user' ? 'User' : (entry.agent_name || 'Agent');
      const content = entry.content.substring(0, 200);
      summaryParts.push(`${role}: ${content}${entry.content.length > 200 ? '...' : ''}`);
    }
  });

  return summaryParts.join('\n');
}

