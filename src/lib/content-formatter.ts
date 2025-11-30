export interface FormattedSection {
  type: 'heading' | 'paragraph' | 'list' | 'code' | 'quote' | 'table';
  content: string | string[] | string[][];
  level?: number;
  language?: string;
}

export class ContentFormatter {
  /**
   * Detect if content is a V0 or Lovable prompt
   */
  static isV0OrLovablePrompt(content: string): boolean {
    const lowerContent = content.toLowerCase();
    // Check for V0 indicators
    const v0Indicators = [
      'v0 vercel prompt',
      'v0 prompt',
      'v0-ready',
      'react + next.js + tailwind',
      'shadcn/ui',
      'v0-1.5-md',
    ];
    // Check for Lovable indicators
    const lovableIndicators = [
      'lovable.dev prompt',
      'lovable prompt',
      'lovable ai',
    ];
    
    const hasV0 = v0Indicators.some(indicator => lowerContent.includes(indicator));
    const hasLovable = lovableIndicators.some(indicator => lowerContent.includes(indicator));
    
    // Also check if content looks like a code prompt (contains React/Next.js patterns)
    const looksLikeCodePrompt = (
      lowerContent.includes('react') && 
      (lowerContent.includes('next.js') || lowerContent.includes('tailwind')) &&
      lowerContent.length > 200 // Prompts are usually longer
    );
    
    return hasV0 || hasLovable || looksLikeCodePrompt;
  }

  /**
   * Convert markdown-style text to HTML
   */
  static markdownToHtml(markdown: string): string {
    // Check if this is a V0 or Lovable prompt - if so, format as code
    if (this.isV0OrLovablePrompt(markdown)) {
      return `<pre class="bg-gray-900 text-gray-100 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-sm font-mono whitespace-pre-wrap">${this.escapeHtml(markdown.trim())}</code></pre>`;
    }
    
    let html = markdown;

    // Headers - Professional styling similar to ChatGPT/Claude
    html = html.replace(/^### (.*$)/gim, '<h3 class="text-xl font-semibold text-gray-900 mt-8 mb-4 leading-tight">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="text-2xl font-semibold text-gray-900 mt-10 mb-5 leading-tight">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="text-3xl font-semibold text-gray-900 mt-12 mb-6 leading-tight">$1</h1>');

    // Bold - More prominent
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em class="italic text-gray-700">$1</em>');

    // Code blocks with syntax highlighting
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
      const language = lang || 'text';
      // Import syntax highlighter dynamically
      try {
        const { highlightCode, detectLanguage } = require('./syntax-highlighter');
        const detectedLang = detectLanguage(code.trim(), language);
        const highlighted = highlightCode(code.trim(), detectedLang);
        return `<div class="code-block-wrapper relative group my-4">
          <div class="flex items-center justify-between mb-2 px-1">
            <span class="text-xs font-mono text-gray-500 uppercase">${detectedLang}</span>
            <button 
              class="copy-code-btn opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded"
              onclick="navigator.clipboard.writeText(\`${code.trim().replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`); this.textContent='Copied!'; setTimeout(() => this.textContent='Copy', 2000);"
            >
              Copy
            </button>
          </div>
          <pre class="bg-gray-900 text-gray-100 rounded-lg p-5 my-6 overflow-x-auto shadow-lg"><code class="language-${detectedLang} text-sm font-mono leading-relaxed">${highlighted}</code></pre>
        </div>`;
      } catch (e) {
        // Fallback to basic formatting
        return `<pre class="bg-gray-900 text-gray-100 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-sm font-mono">${this.escapeHtml(code.trim())}</code></pre>`;
      }
    });

    // Inline code - Better styling
    html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-pink-600 px-2 py-0.5 rounded text-sm font-mono">$1</code>');

    // Unordered lists - Better spacing and styling
    html = html.replace(/^\* (.*$)/gim, '<li class="ml-6 mb-3 list-disc text-gray-800 leading-[1.75]">$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li class="ml-6 mb-3 list-disc text-gray-800 leading-[1.75]">$1</li>');

    // Ordered lists
    html = html.replace(/^\d+\. (.*$)/gim, '<li class="ml-6 mb-3 list-decimal text-gray-800 leading-[1.75]">$1</li>');

    // Wrap consecutive list items - Better spacing
    html = html.replace(/(<li class="ml-6 mb-3 list-disc.*?<\/li>\n?)+/g, (match) => {
      return `<ul class="my-6 space-y-2 pl-2">${match}</ul>`;
    });
    html = html.replace(/(<li class="ml-6 mb-3 list-decimal.*?<\/li>\n?)+/g, (match) => {
      return `<ol class="my-6 space-y-2 pl-2">${match}</ol>`;
    });

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">$1</a>');

    // Blockquotes - More prominent styling
    html = html.replace(/^> (.*$)/gim, '<blockquote class="border-l-4 border-blue-500 pl-5 py-3 my-6 italic text-gray-700 bg-blue-50 rounded-r-lg">$1</blockquote>');

    // Horizontal rules
    html = html.replace(/^---$/gim, '<hr class="my-8 border-t-2 border-gray-200" />');

    // Paragraphs (lines not already wrapped) - Better spacing and typography
    const lines = html.split('\n');
    html = lines.map(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('<')) {
        return `<p class="mb-5 text-gray-800 leading-[1.75] text-base">${line}</p>`;
      }
      return line;
    }).join('\n');

    return html;
  }

  /**
   * Parse and structure content
   */
  static parseContent(content: string): FormattedSection[] {
    const sections: FormattedSection[] = [];
    const lines = content.split('\n');
    let currentList: string[] = [];
    let currentListType: 'ul' | 'ol' | null = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      if (!line) {
        if (currentList.length > 0) {
          sections.push({
            type: 'list',
            content: currentList,
          });
          currentList = [];
          currentListType = null;
        }
        continue;
      }

      // Headers
      if (line.startsWith('###')) {
        sections.push({ type: 'heading', content: line.substring(3).trim(), level: 3 });
      } else if (line.startsWith('##')) {
        sections.push({ type: 'heading', content: line.substring(2).trim(), level: 2 });
      } else if (line.startsWith('#')) {
        sections.push({ type: 'heading', content: line.substring(1).trim(), level: 1 });
      }
      // Lists
      else if (line.match(/^[\*\-] /)) {
        if (currentListType !== 'ul' && currentList.length > 0) {
          sections.push({ type: 'list', content: currentList });
          currentList = [];
        }
        currentListType = 'ul';
        currentList.push(line.substring(2));
      } else if (line.match(/^\d+\. /)) {
        if (currentListType !== 'ol' && currentList.length > 0) {
          sections.push({ type: 'list', content: currentList });
          currentList = [];
        }
        currentListType = 'ol';
        currentList.push(line.replace(/^\d+\. /, ''));
      }
      // Code blocks
      else if (line.startsWith('```')) {
        const language = line.substring(3);
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        sections.push({
          type: 'code',
          content: codeLines.join('\n'),
          language: language || 'text',
        });
      }
      // Blockquote
      else if (line.startsWith('>')) {
        sections.push({ type: 'quote', content: line.substring(1).trim() });
      }
      // Paragraph
      else {
        if (currentList.length > 0) {
          sections.push({ type: 'list', content: currentList });
          currentList = [];
          currentListType = null;
        }
        sections.push({ type: 'paragraph', content: line });
      }
    }

    if (currentList.length > 0) {
      sections.push({ type: 'list', content: currentList });
    }

    return sections;
  }

  /**
   * Convert to PDF-ready HTML
   */
  static toPdfHtml(content: string, title?: string): string {
    const html = this.markdownToHtml(content);

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title || 'Document'}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      line-height: 1.6;
      color: #1f2937;
      max-width: 800px;
      margin: 0 auto;
      padding: 40px 20px;
      background: white;
    }

    h1, h2, h3, h4, h5, h6 {
      font-weight: 700;
      margin-top: 2em;
      margin-bottom: 0.75em;
      color: #111827;
    }

    h1 { font-size: 2em; border-bottom: 3px solid #3b82f6; padding-bottom: 0.3em; }
    h2 { font-size: 1.5em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; }
    h3 { font-size: 1.25em; }

    p {
      margin-bottom: 1em;
      text-align: justify;
    }

    ul, ol {
      margin: 1em 0 1em 2em;
    }

    li {
      margin-bottom: 0.5em;
    }

    code {
      background: #f3f4f6;
      padding: 0.2em 0.4em;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      font-size: 0.9em;
      color: #db2777;
    }

    pre {
      background: #1f2937;
      color: #f9fafb;
      padding: 1em;
      border-radius: 8px;
      overflow-x: auto;
      margin: 1.5em 0;
    }

    pre code {
      background: none;
      color: inherit;
      padding: 0;
    }

    blockquote {
      border-left: 4px solid #3b82f6;
      padding-left: 1em;
      margin: 1.5em 0;
      font-style: italic;
      background: #eff6ff;
      padding: 1em;
      border-radius: 4px;
    }

    hr {
      border: none;
      border-top: 2px solid #e5e7eb;
      margin: 2em 0;
    }

    a {
      color: #2563eb;
      text-decoration: underline;
    }

    strong {
      font-weight: 600;
      color: #111827;
    }

    em {
      font-style: italic;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.5em 0;
    }

    th, td {
      border: 1px solid #e5e7eb;
      padding: 0.75em;
      text-align: left;
    }

    th {
      background: #f9fafb;
      font-weight: 600;
    }

    @media print {
      body {
        max-width: 100%;
        padding: 20px;
      }

      h1, h2, h3 {
        page-break-after: avoid;
      }

      pre, blockquote {
        page-break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  ${title ? `<h1>${this.escapeHtml(title)}</h1>` : ''}
  ${html}
  <hr>
  <p style="text-align: center; color: #6b7280; font-size: 0.875em; margin-top: 3em;">
    Generated by IdeaForge AI • ${new Date().toLocaleDateString()}
  </p>
</body>
</html>
    `.trim();
  }

  /**
   * Escape HTML special characters
   */
  static escapeHtml(text: string): string {
    const map: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
  }

  /**
   * Strip all markdown and HTML tags from content, returning plain text
   */
  static stripMarkdownAndHtml(content: string): string {
    let text = content;
    
    // Remove HTML tags
    text = text.replace(/<[^>]*>/g, '');
    
    // Remove markdown headers
    text = text.replace(/^#{1,6}\s+/gm, '');
    
    // Remove markdown bold/italic
    text = text.replace(/\*\*(.*?)\*\*/g, '$1');
    text = text.replace(/\*(.*?)\*/g, '$1');
    text = text.replace(/_(.*?)_/g, '$1');
    
    // Remove markdown code blocks
    text = text.replace(/```[\s\S]*?```/g, '');
    text = text.replace(/`([^`]+)`/g, '$1');
    
    // Remove markdown links (keep text)
    text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    
    // Remove markdown images
    text = text.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');
    
    // Remove markdown blockquotes
    text = text.replace(/^>\s+/gm, '');
    
    // Remove markdown horizontal rules
    text = text.replace(/^[-*_]{3,}$/gm, '');
    
    // Remove markdown list markers
    text = text.replace(/^[\*\-\+]\s+/gm, '');
    text = text.replace(/^\d+\.\s+/gm, '');
    
    // Clean up extra whitespace
    text = text.replace(/\n{3,}/g, '\n\n');
    text = text.trim();
    
    return text;
  }

  /**
   * Generate a summary from content
   */
  static generateSummary(content: string, maxLength: number = 200): string {
    // Remove markdown formatting
    let text = content.replace(/[#*`>\[\]]/g, '');
    text = text.replace(/\n+/g, ' ').trim();

    if (text.length <= maxLength) {
      return text;
    }

    return text.substring(0, maxLength) + '...';
  }

  /**
   * Extract key points from content
   */
  static extractKeyPoints(content: string): string[] {
    const points: string[] = [];
    const lines = content.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.match(/^[\*\-] /) || trimmed.match(/^\d+\. /)) {
        const point = trimmed.replace(/^[\*\-] /, '').replace(/^\d+\. /, '');
        if (point.length > 10) {
          points.push(point);
        }
      }
    }

    return points;
  }
}
