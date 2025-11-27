/**
 * Session Storage Utility
 * 
 * Manages session-level caching for chat history, agent interactions, and app state.
 * Data persists across page refreshes but is cleared when the browser tab is closed or user logs out.
 */

const SESSION_KEYS = {
  CHAT_MESSAGES: (productId: string) => `chat_messages_${productId}`,
  AGENT_INTERACTIONS: (productId: string) => `agent_interactions_${productId}`,
  ACTIVE_AGENTS: (productId: string) => `active_agents_${productId}`,
  COORDINATION_MODE: (productId: string) => `coordination_mode_${productId}`,
  APP_STATE: 'app_state',
} as const;

export interface ChatSessionData {
  messages: any[];
  agentInteractions: any[];
  activeAgents: string[];
  coordinationMode?: string;
  lastUpdated: string;
}

export interface AppState {
  productId?: string;
  currentPhaseId?: string;
  view?: string;
  // Don't store phases/submissions in sessionStorage - they should be loaded fresh
  // phases?: any[];
  // submissions?: any[];
}

/**
 * Save chat messages for a product
 */
export function saveChatMessages(productId: string, messages: any[]): void {
  try {
    const data: ChatSessionData = {
      messages,
      agentInteractions: [],
      activeAgents: [],
      lastUpdated: new Date().toISOString(),
    };
    sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(data));
  } catch (error) {
    console.error('Error saving chat messages to sessionStorage:', error);
  }
}

/**
 * Load chat messages for a product
 */
export function loadChatMessages(productId: string): any[] | null {
  try {
    const stored = sessionStorage.getItem(SESSION_KEYS.CHAT_MESSAGES(productId));
    if (stored) {
      const data: ChatSessionData = JSON.parse(stored);
      return data.messages || null;
    }
  } catch (error) {
    console.error('Error loading chat messages from sessionStorage:', error);
  }
  return null;
}

/**
 * Save complete chat session data
 */
export function saveChatSession(productId: string, data: Partial<ChatSessionData>): void {
  try {
    const existing = loadChatSession(productId);
    const updated: ChatSessionData = {
      messages: data.messages ?? existing?.messages ?? [],
      agentInteractions: data.agentInteractions ?? existing?.agentInteractions ?? [],
      activeAgents: data.activeAgents ?? existing?.activeAgents ?? [],
      coordinationMode: data.coordinationMode ?? existing?.coordinationMode,
      lastUpdated: new Date().toISOString(),
    };
    sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(updated));
  } catch (error) {
    console.error('Error saving chat session to sessionStorage:', error);
  }
}

/**
 * Load complete chat session data
 */
export function loadChatSession(productId: string): ChatSessionData | null {
  try {
    const stored = sessionStorage.getItem(SESSION_KEYS.CHAT_MESSAGES(productId));
    if (stored) {
      return JSON.parse(stored) as ChatSessionData;
    }
  } catch (error) {
    console.error('Error loading chat session from sessionStorage:', error);
  }
  return null;
}

/**
 * Save app state (productId, currentPhase, view, etc.)
 */
export function saveAppState(state: AppState): void {
  try {
    sessionStorage.setItem(SESSION_KEYS.APP_STATE, JSON.stringify(state));
  } catch (error) {
    console.error('Error saving app state to sessionStorage:', error);
  }
}

/**
 * Load app state
 */
export function loadAppState(): AppState | null {
  try {
    const stored = sessionStorage.getItem(SESSION_KEYS.APP_STATE);
    if (stored) {
      return JSON.parse(stored) as AppState;
    }
  } catch (error) {
    console.error('Error loading app state from sessionStorage:', error);
  }
  return null;
}

/**
 * Clear all session data for a specific product
 */
export function clearProductSession(productId: string): void {
  try {
    sessionStorage.removeItem(SESSION_KEYS.CHAT_MESSAGES(productId));
    sessionStorage.removeItem(SESSION_KEYS.AGENT_INTERACTIONS(productId));
    sessionStorage.removeItem(SESSION_KEYS.ACTIVE_AGENTS(productId));
    sessionStorage.removeItem(SESSION_KEYS.COORDINATION_MODE(productId));
  } catch (error) {
    console.error('Error clearing product session:', error);
  }
}

/**
 * Clear all session storage (called on logout)
 */
export function clearAllSessionStorage(): void {
  try {
    // Clear all session storage items
    const keys = Object.keys(sessionStorage);
    keys.forEach(key => {
      // Only clear our app's session data, not other apps
      if (
        key.startsWith('chat_messages_') ||
        key.startsWith('agent_interactions_') ||
        key.startsWith('active_agents_') ||
        key.startsWith('coordination_mode_') ||
        key === 'app_state'
      ) {
        sessionStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.error('Error clearing session storage:', error);
  }
}

/**
 * Get all product IDs that have session data
 */
export function getProductsWithSessionData(): string[] {
  try {
    const productIds = new Set<string>();
    const keys = Object.keys(sessionStorage);
    keys.forEach(key => {
      if (key.startsWith('chat_messages_')) {
        const productId = key.replace('chat_messages_', '');
        productIds.add(productId);
      }
    });
    return Array.from(productIds);
  } catch (error) {
    console.error('Error getting products with session data:', error);
    return [];
  }
}

/**
 * Reset app state for a specific product (useful when UI gets corrupted)
 */
export function resetProductState(productId: string): void {
  try {
    console.log('Resetting product state for:', productId);
    // Clear all session data for this product
    clearProductSession(productId);
    
    // Clear app state if it references this product
    const appState = loadAppState();
    if (appState?.productId === productId) {
      saveAppState({
        view: appState.view || 'dashboard',
        // Clear productId and currentPhaseId to force fresh load
      });
    }
  } catch (error) {
    console.error('Error resetting product state:', error);
  }
}

/**
 * Clear app state completely (useful for fixing corrupted state)
 */
export function clearAppState(): void {
  try {
    sessionStorage.removeItem(SESSION_KEYS.APP_STATE);
    console.log('App state cleared');
  } catch (error) {
    console.error('Error clearing app state:', error);
  }
}

// Expose utility functions to window for debugging
if (typeof window !== 'undefined') {
  (window as any).ideaforgeDebug = {
    resetProductState,
    clearAppState,
    clearProductSession,
    clearAllSessionStorage,
    getProductsWithSessionData,
    loadAppState,
  };
  console.log('IdeaForge debug utilities available at window.ideaforgeDebug');
}

