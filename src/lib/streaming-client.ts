/**
 * Streaming client for real-time multi-agent responses.
 * Supports Server-Sent Events (SSE) and WebSocket connections.
 */

export interface StreamingEvent {
  type: 'agent_start' | 'agent_chunk' | 'agent_complete' | 'interaction' | 'error' | 'progress' | 'complete';
  agent?: string;
  chunk?: string;
  response?: string;
  error?: string;
  progress?: number;
  message?: string;
  from_agent?: string;
  to_agent?: string;
  query?: string;
  interactions?: any[];
  metadata?: any;
  timestamp?: string;
}

export interface StreamingOptions {
  onEvent?: (event: StreamingEvent) => void;
  onChunk?: (chunk: string, agent: string) => void;
  onAgentStart?: (agent: string) => void;
  onAgentComplete?: (agent: string, response: string, metadata?: any) => void;
  onInteraction?: (from_agent: string, to_agent: string, query: string, response: string, metadata?: any) => void;
  onProgress?: (progress: number, message: string) => void;
  onError?: (error: string) => void;
  onComplete?: (response: string, interactions: any[], metadata: any) => void;
}

/**
 * Stream multi-agent response using Server-Sent Events (SSE).
 * Uses fetch with ReadableStream for POST support (EventSource only supports GET).
 */
export async function streamMultiAgentSSE(
  request: any,
  token: string,
  apiUrl: string,
  options: StreamingOptions = {}
): Promise<{ response: string; interactions: any[]; metadata: any }> {
  return new Promise((resolve, reject) => {
    const controller = new AbortController();
    let accumulatedResponse = '';
    let interactions: any[] = [];
    let metadata: any = {};
    let currentEventType = '';

    fetch(`${apiUrl}/api/streaming/multi-agent/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        if (!reader) {
          throw new Error('Response body is not readable');
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEventType = line.substring(7).trim();
              continue;
            }
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                // Add event type from SSE format
                if (!data.type && currentEventType) {
                  data.type = currentEventType;
                }
                handleEvent(data, options, {
                  accumulatedResponse,
                  interactions,
                  metadata,
                  setAccumulated: (val: string) => { accumulatedResponse = val; },
                  setInteractions: (val: any[]) => { interactions = val; },
                  setMetadata: (val: any) => { metadata = val; },
                });
                
                // Reset event type after processing
                currentEventType = '';
              } catch (e) {
                console.error('Failed to parse SSE data:', e, 'Line:', line);
              }
            }
          }
        }

        resolve({
          response: accumulatedResponse,
          interactions,
          metadata,
        });
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          const errorMessage = error.message || error.toString() || 'Streaming connection failed. Please try again.';
          console.error('Streaming fetch error:', { error, message: errorMessage, name: error.name });
          
          // If we have partial response, resolve with it instead of rejecting
          if (accumulatedResponse && accumulatedResponse.length > 0) {
            console.warn('Streaming error but partial response available, returning partial result');
            resolve({
              response: accumulatedResponse,
              interactions,
              metadata: { error: errorMessage, partial: true },
            });
            return;
          }
          
          reject(error);
          options.onError?.(errorMessage);
        }
      });
  });
}

/**
 * Stream multi-agent response using WebSocket.
 */
export class WebSocketStreamingClient {
  private ws: WebSocket | null = null;
  private connectionId: string;
  private token: string;
  private apiUrl: string;
  private options: StreamingOptions;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(token: string, apiUrl: string, options: StreamingOptions = {}) {
    this.token = token;
    this.apiUrl = apiUrl;
    this.options = options;
    this.connectionId = `ws-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = this.apiUrl.replace(/^http/, 'ws');
      this.ws = new WebSocket(`${wsUrl}/api/streaming/ws/${this.connectionId}?token=${encodeURIComponent(this.token)}`);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        resolve();
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.options.onError?.('WebSocket connection error');
        reject(error);
      };

      this.ws.onclose = () => {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
        }
      };
    });
  }

  private handleMessage(data: any) {
    const event: StreamingEvent = data;
    
    // Filter out internal events - these are for supporting agents that shouldn't be shown to user
    if ((event as any).internal === true) {
      // Still track interactions for metadata, but don't show to user
      if (event.type === 'interaction' && event.from_agent && event.to_agent) {
        // Store interaction but don't call callbacks
      }
      return; // Don't process further - this is an internal event
    }
    
    switch (event.type) {
      case 'connected':
        break;
      case 'agent_start':
        // Only show agent_start for primary agent, not supporting agents
        this.options.onAgentStart?.(event.agent || '');
        break;
      case 'agent_chunk':
        // Only stream chunks from primary agent (supporting agents are internal)
        if (event.chunk && event.agent) {
          this.options.onChunk?.(event.chunk, event.agent);
        }
        break;
      case 'agent_complete':
        // Only show completion for primary agent (supporting agents are internal)
        if (event.agent && event.response) {
          this.options.onAgentComplete?.(event.agent, event.response, event.metadata);
        }
        break;
      case 'interaction':
        // Handle agent-to-agent interaction
        break;
      case 'progress':
        if (event.progress !== undefined && event.message) {
          this.options.onProgress?.(event.progress, event.message);
        }
        break;
      case 'error':
        const errorMessage = event.error || event.message || 'WebSocket streaming error occurred';
        console.error('WebSocket error event:', { type: event.type, error: errorMessage, event });
        this.options.onError?.(errorMessage);
        break;
      case 'complete':
        if (event.response) {
          this.options.onComplete?.(
            event.response,
            event.interactions || [],
            event.metadata || {}
          );
        }
        break;
    }

    this.options.onEvent?.(event);
  }

  sendRequest(request: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'multi_agent_request',
        request,
      }));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  ping() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }
}

function handleEvent(
  data: any,
  options: StreamingOptions,
  state: {
    accumulatedResponse: string;
    interactions: any[];
    metadata: any;
    setAccumulated: (val: string) => void;
    setInteractions: (val: any[]) => void;
    setMetadata: (val: any) => void;
  }
) {
  const event: StreamingEvent = data;
  
  // Filter out internal events - these are for supporting agents that shouldn't be shown to user
  if ((event as any).internal === true) {
    // Still track interactions for metadata, but don't show to user
    if (event.type === 'interaction' && event.from_agent && event.to_agent) {
      const interaction_data = {
        from_agent: event.from_agent,
        to_agent: event.to_agent,
        query: event.query,
        response: event.response,
        metadata: event.metadata || {},
        timestamp: event.timestamp || new Date().toISOString(),
      };
      state.interactions.push(interaction_data);
      state.setInteractions([...state.interactions]);
    }
    return; // Don't process further - this is an internal event
  }

  switch (event.type) {
    case 'agent_start':
      // Only show agent_start for primary agent, not supporting agents
      // Supporting agents will have internal flag set
      options.onAgentStart?.(event.agent || '');
      break;
    case 'agent_chunk':
      // Only stream chunks from primary agent (supporting agents are internal)
      if (event.chunk && event.agent) {
        state.setAccumulated(state.accumulatedResponse + event.chunk);
        options.onChunk?.(event.chunk, event.agent);
      }
      break;
    case 'agent_complete':
      // Only show completion for primary agent (supporting agents are internal)
      if (event.agent && event.response) {
        state.setAccumulated(state.accumulatedResponse + event.response);
        options.onAgentComplete?.(event.agent, event.response, event.metadata);
      }
      break;
    case 'interaction':
      if (event.from_agent && event.to_agent) {
        const interaction_data = {
          from_agent: event.from_agent,
          to_agent: event.to_agent,
          query: event.query,
          response: event.response,
          metadata: event.metadata || {},
          timestamp: event.timestamp || new Date().toISOString(),
        };
        state.interactions.push(interaction_data);
        state.setInteractions([...state.interactions]);
        // Call onInteraction callback if provided
        options.onInteraction?.(
          event.from_agent,
          event.to_agent,
          event.query || '',
          event.response || '',
          event.metadata
        );
      }
      break;
    case 'progress':
      if (event.progress !== undefined && event.message) {
        options.onProgress?.(event.progress, event.message);
      }
      break;
    case 'error':
      const errorMessage = event.error || event.message || 'Streaming connection error occurred';
      console.error('Streaming error event:', { type: event.type, error: errorMessage, event });
      options.onError?.(errorMessage);
      break;
    case 'complete':
      if (event.response) {
        state.setAccumulated(event.response);
        state.setInteractions(event.interactions || []);
        state.setMetadata(event.metadata || {});
        options.onComplete?.(
          event.response,
          event.interactions || [],
          event.metadata || {}
        );
      }
      break;
  }

  options.onEvent?.(event);
}

