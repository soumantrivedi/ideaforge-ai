import { useState, useEffect, useRef } from 'react';
import { Search, Command, X, ArrowRight, Zap } from 'lucide-react';
import { useCommandPalette, CommandPaletteItem } from '../lib/keyboard-shortcuts';
import { motion, AnimatePresence } from 'framer-motion';

interface CommandPaletteProps {
  onCommandSelect?: (item: CommandPaletteItem) => void;
}

export function CommandPalette({ onCommandSelect }: CommandPaletteProps) {
  const { isOpen, toggle, search, getByCategory } = useCommandPalette();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  const commands = query ? search(query) : getByCategory();
  const flatCommands = Array.isArray(commands) ? commands : Object.values(commands).flat();
  const groupedCommands = Array.isArray(commands) ? {} : commands;

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          toggle();
        } else if (e.key === 'ArrowDown') {
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, flatCommands.length - 1));
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
        } else if (e.key === 'Enter' && flatCommands[selectedIndex]) {
          e.preventDefault();
          handleSelect(flatCommands[selectedIndex]);
        }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, flatCommands, selectedIndex, toggle]);

  useEffect(() => {
    if (resultsRef.current && selectedIndex >= 0) {
      const selectedElement = resultsRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [selectedIndex]);

  const handleSelect = (item: CommandPaletteItem) => {
    item.action();
    onCommandSelect?.(item);
    toggle();
    setQuery('');
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black bg-opacity-50"
        onClick={toggle}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: -20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -20 }}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200">
            <Search className="w-5 h-5 text-gray-400" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              placeholder="Type a command or search..."
              className="flex-1 outline-none text-gray-900 placeholder-gray-400"
            />
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <kbd className="px-2 py-1 bg-gray-100 rounded">Esc</kbd>
              <span>to close</span>
            </div>
            <button
              onClick={toggle}
              className="p-1 hover:bg-gray-100 rounded transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-96 overflow-y-auto" ref={resultsRef}>
            {flatCommands.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <p>No commands found</p>
                <p className="text-sm mt-2">Try a different search term</p>
              </div>
            ) : (
              <div className="py-2">
                {Object.keys(groupedCommands).length > 0 ? (
                  // Grouped view
                  Object.entries(groupedCommands).map(([category, items]) => (
                    <div key={category} className="mb-4">
                      <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                        {category}
                      </div>
                      {items.map((item, index) => {
                        const globalIndex = flatCommands.findIndex(cmd => cmd.id === item.id);
                        return (
                          <button
                            key={item.id}
                            onClick={() => handleSelect(item)}
                            className={`w-full text-left px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors ${
                              globalIndex === selectedIndex ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                            }`}
                          >
                            {item.icon && <span className="text-lg">{item.icon}</span>}
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-gray-900">{item.label}</div>
                              {item.description && (
                                <div className="text-sm text-gray-500 truncate">{item.description}</div>
                              )}
                            </div>
                            <ArrowRight className="w-4 h-4 text-gray-400" />
                          </button>
                        );
                      })}
                    </div>
                  ))
                ) : (
                  // Flat list
                  flatCommands.map((item, index) => (
                    <button
                      key={item.id}
                      onClick={() => handleSelect(item)}
                      className={`w-full text-left px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors ${
                        index === selectedIndex ? 'bg-blue-50 border-l-4 border-blue-500' : ''
                      }`}
                    >
                      {item.icon && <span className="text-lg">{item.icon}</span>}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900">{item.label}</div>
                        {item.description && (
                          <div className="text-sm text-gray-500 truncate">{item.description}</div>
                        )}
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-400" />
                    </button>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">↑</kbd>
                <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">↓</kbd>
                <span>Navigate</span>
              </div>
              <div className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">Enter</kbd>
                <span>Select</span>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Command className="w-3 h-3" />
              <kbd className="px-1.5 py-0.5 bg-gray-100 rounded">K</kbd>
              <span>to open</span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

