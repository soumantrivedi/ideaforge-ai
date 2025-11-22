export interface FormattedSection {
  type: 'heading' | 'paragraph' | 'list' | 'code' | 'quote' | 'table';
  content: string | string[] | string[][];
  level?: number;
  language?: string;
}

export class ContentFormatter {
  /**
   * Convert markdown-style text to HTML
   */
  static markdownToHtml(markdown: string): string {
    let html = markdown;

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3 class="text-lg font-bold text-gray-900 mt-6 mb-3">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold text-gray-900 mt-8 mb-4">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-gray-900 mt-10 mb-5">$1</h1>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/g, '<em class="italic text-gray-800">$1</em>');

    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre class="bg-gray-900 text-gray-100 rounded-lg p-4 my-4 overflow-x-auto"><code class="text-sm font-mono">${this.escapeHtml(code.trim())}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-pink-600 px-2 py-1 rounded text-sm font-mono">$1</code>');

    // Unordered lists
    html = html.replace(/^\* (.*$)/gim, '<li class="ml-6 mb-2 list-disc">$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li class="ml-6 mb-2 list-disc">$1</li>');

    // Ordered lists
    html = html.replace(/^\d+\. (.*$)/gim, '<li class="ml-6 mb-2 list-decimal">$1</li>');

    // Wrap consecutive list items
    html = html.replace(/(<li class="ml-6 mb-2 list-disc">.*<\/li>\n?)+/g, (match) => {
      return `<ul class="my-4 space-y-1">${match}</ul>`;
    });
    html = html.replace(/(<li class="ml-6 mb-2 list-decimal">.*<\/li>\n?)+/g, (match) => {
      return `<ol class="my-4 space-y-1">${match}</ol>`;
    });

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">$1</a>');

    // Blockquotes
    html = html.replace(/^> (.*$)/gim, '<blockquote class="border-l-4 border-blue-500 pl-4 py-2 my-4 italic text-gray-700 bg-blue-50">$1</blockquote>');

    // Horizontal rules
    html = html.replace(/^---$/gim, '<hr class="my-8 border-t-2 border-gray-200" />');

    // Paragraphs (lines not already wrapped)
    const lines = html.split('\n');
    html = lines.map(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('<')) {
        return `<p class="mb-4 text-gray-800 leading-relaxed">${line}</p>`;
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
