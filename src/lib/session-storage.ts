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
 * Handles QuotaExceededError by truncating old messages
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
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      // Quota exceeded - try to save with truncated messages
      console.warn('SessionStorage quota exceeded, truncating old messages');
      try {
        // Keep only the most recent 50 messages
        const truncatedMessages = messages.slice(-50);
        const data: ChatSessionData = {
          messages: truncatedMessages,
          agentInteractions: [],
          activeAgents: [],
          lastUpdated: new Date().toISOString(),
        };
        sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(data));
        console.log(`Saved truncated chat messages (${truncatedMessages.length} messages)`);
      } catch (truncateError) {
        // If still failing, try even more aggressive truncation
        console.warn('Still exceeding quota, trying more aggressive truncation');
        try {
          // Keep only last 20 messages and truncate content
          const truncatedMessages = messages.slice(-20).map((msg: any) => ({
            ...msg,
            content: typeof msg.content === 'string' && msg.content.length > 500 
              ? msg.content.substring(0, 500) + '... [truncated]' 
              : msg.content
          }));
          const data: ChatSessionData = {
            messages: truncatedMessages,
            agentInteractions: [],
            activeAgents: [],
            lastUpdated: new Date().toISOString(),
          };
          sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(data));
          console.log(`Saved heavily truncated chat messages (${truncatedMessages.length} messages)`);
        } catch (finalError) {
          // Last resort: clear old session data and try again
          console.warn('Clearing old session data to free space');
          try {
            clearProductSession(productId);
            // Wait a bit for storage to clear
            setTimeout(() => {
              // Try one more time with minimal data
              const minimalData: ChatSessionData = {
                messages: messages.slice(-10),
                agentInteractions: [],
                activeAgents: [],
                lastUpdated: new Date().toISOString(),
              };
              try {
                sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(minimalData));
                console.log('✅ Successfully saved minimal data after clearing');
              } catch (e) {
                console.error('❌ Still unable to save after clearing. Storage may be full. Please clear manually.');
                console.log('💡 Run in console: window.ideaforgeDebug.clearAllStorage()');
              }
            }, 100);
          } catch (clearError) {
            console.error('❌ Unable to clear storage. Please clear manually:', clearError);
            console.log('💡 Run in console: window.ideaforgeDebug.clearAllStorage()');
          }
        }
      }
    } else {
      console.error('Error saving chat messages to sessionStorage:', error);
    }
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
 * Handles QuotaExceededError by truncating old messages
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
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      // Quota exceeded - truncate messages and try again
      console.warn('SessionStorage quota exceeded in saveChatSession, truncating messages');
      try {
        const existing = loadChatSession(productId);
        // Limit messages to 50, agentInteractions to 20
        const truncatedMessages = (data.messages ?? existing?.messages ?? []).slice(-50);
        const truncatedInteractions = (data.agentInteractions ?? existing?.agentInteractions ?? []).slice(-20);
        const updated: ChatSessionData = {
          messages: truncatedMessages,
          agentInteractions: truncatedInteractions,
          activeAgents: data.activeAgents ?? existing?.activeAgents ?? [],
          coordinationMode: data.coordinationMode ?? existing?.coordinationMode,
          lastUpdated: new Date().toISOString(),
        };
        sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(updated));
        console.log(`Saved truncated chat session (${truncatedMessages.length} messages, ${truncatedInteractions.length} interactions)`);
      } catch (truncateError) {
        // If still failing, clear and save minimal data
        console.warn('Still exceeding quota, clearing and saving minimal data');
        clearProductSession(productId);
        const minimalData: ChatSessionData = {
          messages: (data.messages ?? []).slice(-10),
          agentInteractions: [],
          activeAgents: data.activeAgents ?? [],
          coordinationMode: data.coordinationMode,
          lastUpdated: new Date().toISOString(),
        };
          try {
            sessionStorage.setItem(SESSION_KEYS.CHAT_MESSAGES(productId), JSON.stringify(minimalData));
            console.log('✅ Successfully saved minimal data after clearing');
          } catch (e) {
            console.error('❌ Still unable to save after clearing. Storage may be full. Please clear manually.');
            console.log('💡 Run in console: window.ideaforgeDebug.clearAllStorage()');
          }
      }
    } else {
      console.error('Error saving chat session to sessionStorage:', error);
    }
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
        key === 'app_state' ||
        key.startsWith('product_info_')
      ) {
        sessionStorage.removeItem(key);
      }
    });
    console.log('Cleared all IdeaForge AI session storage');
  } catch (error) {
    console.error('Error clearing session storage:', error);
  }
}

/**
 * Get sessionStorage usage information
 * Returns estimated usage and percentage
 */
export function getSessionStorageInfo(): { used: number; quota: number; percentage: number; keys: string[] } {
  try {
    let used = 0;
    const keys: string[] = [];
    for (let key in sessionStorage) {
      if (sessionStorage.hasOwnProperty(key)) {
        const value = sessionStorage[key];
        used += (value ? value.length : 0) + key.length;
        keys.push(key);
      }
    }
    // Estimate quota (typically 5-10MB, but varies by browser)
    const quota = 5 * 1024 * 1024; // 5MB estimate
    const percentage = (used / quota) * 100;
    return { used, quota, percentage, keys };
  } catch (error) {
    console.error('Error getting sessionStorage info:', error);
    return { used: 0, quota: 0, percentage: 0, keys: [] };
  }
}

// Expose utility functions to window for debugging
if (typeof window !== 'undefined') {
  (window as any).ideaforgeDebug = {
    clearProductSession,
    clearAllSessionStorage,
    getSessionStorageInfo,
    clearStorageForProduct: (productId: string) => {
      clearProductSession(productId);
      console.log(`✅ Cleared storage for product: ${productId}`);
    },
    clearAllStorage: () => {
      clearAllSessionStorage();
      console.log('✅ Cleared all IdeaForge AI storage');
    },
    showStorageInfo: () => {
      const info = getSessionStorageInfo();
      console.log('📊 SessionStorage Info:', {
        used: `${(info.used / 1024).toFixed(2)} KB`,
        quota: `${(info.quota / 1024 / 1024).toFixed(2)} MB`,
        percentage: `${info.percentage.toFixed(2)}%`,
        keys: info.keys.filter(k => k.startsWith('chat_messages_') || k.startsWith('product_info_'))
      });
      return info;
    }
  };
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

