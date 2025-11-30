/**
 * Keyboard shortcuts and command palette functionality
 */
import { useState, useEffect, useCallback } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;
  action: () => void;
}

export interface CommandPaletteItem {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  category: string;
  action: () => void;
  keywords?: string[];
}

class KeyboardShortcutManager {
  private shortcuts: Map<string, KeyboardShortcut> = new Map();
  private commandPaletteItems: CommandPaletteItem[] = [];
  private isCommandPaletteOpen = false;
  private listeners: Set<(isOpen: boolean) => void> = new Set();

  /**
   * Register a keyboard shortcut
   */
  register(shortcut: KeyboardShortcut): () => void {
    const key = this.getShortcutKey(shortcut);
    this.shortcuts.set(key, shortcut);
    
    // Return unregister function
    return () => {
      this.shortcuts.delete(key);
    };
  }

  /**
   * Register command palette items
   */
  registerCommands(items: CommandPaletteItem[]): void {
    this.commandPaletteItems = [...this.commandPaletteItems, ...items];
  }

  /**
   * Get shortcut key string
   */
  private getShortcutKey(shortcut: KeyboardShortcut): string {
    const parts: string[] = [];
    if (shortcut.ctrl || shortcut.meta) parts.push('mod');
    if (shortcut.shift) parts.push('shift');
    if (shortcut.alt) parts.push('alt');
    parts.push(shortcut.key.toLowerCase());
    return parts.join('+');
  }

  /**
   * Handle keyboard event
   */
  handleKeyDown(event: KeyboardEvent): boolean {
    // Command palette: Cmd+K or Ctrl+K
    if ((event.metaKey || event.ctrlKey) && event.key === 'k' && !event.shiftKey && !event.altKey) {
      event.preventDefault();
      this.toggleCommandPalette();
      return true;
    }

    // Check registered shortcuts
    const key = this.getShortcutKeyFromEvent(event);
    const shortcut = this.shortcuts.get(key);
    
    if (shortcut) {
      event.preventDefault();
      shortcut.action();
      return true;
    }

    return false;
  }

  /**
   * Get shortcut key from keyboard event
   */
  private getShortcutKeyFromEvent(event: KeyboardEvent): string {
    const parts: string[] = [];
    if (event.ctrlKey || event.metaKey) parts.push('mod');
    if (event.shiftKey) parts.push('shift');
    if (event.altKey) parts.push('alt');
    // Handle cases where event.key might be undefined (e.g., special keys)
    if (event.key) {
      parts.push(event.key.toLowerCase());
    } else if (event.code) {
      // Fallback to event.code if event.key is undefined
      parts.push(event.code.toLowerCase());
    } else {
      // If both are undefined, return empty string to avoid errors
      return '';
    }
    return parts.join('+');
  }

  /**
   * Toggle command palette
   */
  toggleCommandPalette(): void {
    this.isCommandPaletteOpen = !this.isCommandPaletteOpen;
    this.listeners.forEach(listener => listener(this.isCommandPaletteOpen));
  }

  /**
   * Subscribe to command palette state changes
   */
  subscribe(listener: (isOpen: boolean) => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Get command palette state
   */
  getCommandPaletteState(): boolean {
    return this.isCommandPaletteOpen;
  }

  /**
   * Search command palette items
   */
  searchCommands(query: string): CommandPaletteItem[] {
    if (!query.trim()) {
      return this.commandPaletteItems;
    }

    const lowerQuery = query.toLowerCase();
    return this.commandPaletteItems.filter(item => {
      const searchText = `${item.label} ${item.description || ''} ${item.keywords?.join(' ') || ''}`.toLowerCase();
      return searchText.includes(lowerQuery);
    });
  }

  /**
   * Get commands by category
   */
  getCommandsByCategory(): Record<string, CommandPaletteItem[]> {
    const grouped: Record<string, CommandPaletteItem[]> = {};
    this.commandPaletteItems.forEach(item => {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    });
    return grouped;
  }
}

// Global instance
export const keyboardShortcutManager = new KeyboardShortcutManager();

/**
 * React hook for keyboard shortcuts
 */
export function useKeyboardShortcut(
  key: string,
  action: () => void,
  options?: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean }
): void {
  useEffect(() => {
    const shortcut: KeyboardShortcut = {
      key,
      ...options,
      description: '',
      action,
    };
    
    const unregister = keyboardShortcutManager.register(shortcut);
    return unregister;
  }, [key, action, options?.ctrl, options?.shift, options?.alt, options?.meta]);
}

/**
 * React hook for command palette
 */
export function useCommandPalette(): {
  isOpen: boolean;
  toggle: () => void;
  search: (query: string) => CommandPaletteItem[];
  getByCategory: () => Record<string, CommandPaletteItem[]>;
} {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const unsubscribe = keyboardShortcutManager.subscribe(setIsOpen);
    return unsubscribe;
  }, []);

  return {
    isOpen,
    toggle: () => keyboardShortcutManager.toggleCommandPalette(),
    search: (query: string) => keyboardShortcutManager.searchCommands(query),
    getByCategory: () => keyboardShortcutManager.getCommandsByCategory(),
  };
}

/**
 * Initialize global keyboard shortcuts
 */
export function initKeyboardShortcuts(): () => void {
  const handleKeyDown = (event: KeyboardEvent) => {
    keyboardShortcutManager.handleKeyDown(event);
  };

  window.addEventListener('keydown', handleKeyDown);
  
  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}

