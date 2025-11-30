/**
 * Syntax highlighting utility using Prism.js
 * Provides enhanced code formatting with syntax highlighting
 */
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css'; // Dark theme
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-bash';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-markdown';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-docker';
import 'prismjs/components/prism-jsx';
import 'prismjs/components/prism-tsx';
import 'prismjs/components/prism-css';
import 'prismjs/components/prism-html';

/**
 * Highlight code block with syntax highlighting
 */
export function highlightCode(code: string, language: string = 'text'): string {
  if (!code) return '';
  
  // Normalize language name
  const normalizedLang = language.toLowerCase().replace(/[^a-z0-9]/g, '');
  
  // Map common language aliases
  const langMap: Record<string, string> = {
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'sh': 'bash',
    'shell': 'bash',
    'yml': 'yaml',
    'md': 'markdown',
  };
  
  const prismLang = langMap[normalizedLang] || normalizedLang;
  
  try {
    // Check if language is supported
    if (Prism.languages[prismLang]) {
      return Prism.highlight(code, Prism.languages[prismLang], prismLang);
    } else {
      // Fallback to plain text
      return Prism.util.encode(code);
    }
  } catch (error) {
    console.warn('Syntax highlighting error:', error);
    return Prism.util.encode(code);
  }
}

/**
 * Detect language from code block or file extension
 */
export function detectLanguage(code: string, hint?: string): string {
  if (hint) {
    return hint.toLowerCase();
  }
  
  // Try to detect from code patterns
  if (code.includes('import ') || code.includes('export ') || code.includes('const ') || code.includes('function ')) {
    if (code.includes('interface ') || code.includes('type ') || code.includes(':')) {
      return 'typescript';
    }
    return 'javascript';
  }
  
  if (code.includes('def ') || code.includes('import ') || code.includes('class ')) {
    return 'python';
  }
  
  if (code.includes('SELECT ') || code.includes('FROM ') || code.includes('WHERE ')) {
    return 'sql';
  }
  
  if (code.includes('<!DOCTYPE') || code.includes('<html')) {
    return 'html';
  }
  
  if (code.includes('{') && code.includes('}') && code.includes(':')) {
    return 'json';
  }
  
  return 'text';
}

/**
 * Format code block with syntax highlighting and copy button
 */
export function formatCodeBlock(code: string, language: string = 'text'): string {
  const highlighted = highlightCode(code, language);
  const escapedCode = code.replace(/`/g, '\\`').replace(/\$/g, '\\$');
  
  return `
    <div class="code-block-wrapper relative group">
      <div class="flex items-center justify-between mb-2 px-1">
        <span class="text-xs font-mono text-gray-500 uppercase">${language}</span>
        <button 
          class="copy-code-btn opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded"
          onclick="navigator.clipboard.writeText(\`${escapedCode}\`); this.textContent='Copied!'; setTimeout(() => this.textContent='Copy', 2000);"
        >
          Copy
        </button>
      </div>
      <pre class="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto"><code class="language-${language}">${highlighted}</code></pre>
    </div>
  `;
}

