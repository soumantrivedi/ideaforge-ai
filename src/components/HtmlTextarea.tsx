import { useEffect, useRef, useState } from 'react';
import { ContentFormatter } from '../lib/content-formatter';

interface HtmlTextareaProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  disabled?: boolean;
  className?: string;
  onStreamingUpdate?: (chunk: string) => void;
  isStreaming?: boolean;
}

/**
 * A textarea component that can display HTML-formatted content
 * while allowing editing. Shows HTML rendering when content is formatted,
 * but allows plain text editing.
 */
export function HtmlTextarea({
  id,
  value,
  onChange,
  placeholder = '',
  rows = 8,
  disabled = false,
  className = '',
  onStreamingUpdate,
  isStreaming = false,
}: HtmlTextareaProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [displayValue, setDisplayValue] = useState(value);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const previewRef = useRef<HTMLDivElement>(null);
  const isHtmlContent = useRef(false);

  // Check if content contains HTML or markdown formatting
  useEffect(() => {
    if (!value) {
      setDisplayValue('');
      if (previewRef.current) {
        previewRef.current.innerHTML = '';
      }
      return;
    }
    
    // Check for markdown patterns (multiline)
    const hasMarkdown = /#{1,6}\s|\*\*.*\*\*|\* .*|\- .*|\d+\. .*|```[\s\S]*```|`[^`]+`/m.test(value);
    const hasHtml = /<[a-z][\s\S]*>/i.test(value);
    isHtmlContent.current = hasMarkdown || hasHtml;
    
    if (isHtmlContent.current && !isEditing && !isStreaming) {
      // Render as HTML
      const html = ContentFormatter.markdownToHtml(value);
      if (previewRef.current) {
        previewRef.current.innerHTML = html || value;
      }
    } else {
      // Show plain text
      setDisplayValue(value);
    }
  }, [value, isEditing, isStreaming]);

  // Handle streaming updates
  useEffect(() => {
    if (isStreaming) {
      // During streaming, show plain text in textarea
      setIsEditing(true);
      setDisplayValue(value);
    } else if (!isStreaming && value) {
      // After streaming completes, check if we should render as HTML
      const hasMarkdown = /#{1,6}\s|\*\*.*\*\*|\* .*|\- .*|\d+\. .*|```[\s\S]*```|`[^`]+`/m.test(value);
      const hasHtml = /<[a-z][\s\S]*>/i.test(value);
      if (hasMarkdown || hasHtml) {
        setIsEditing(false);
      }
    }
  }, [isStreaming, value]);

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    setDisplayValue(newValue);
    onChange(newValue);
  };

  const handlePreviewClick = () => {
    setIsEditing(true);
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 0);
  };

  const handleBlur = () => {
    // Check if content should be rendered as HTML (multiline check)
    const hasMarkdown = /#{1,6}\s|\*\*.*\*\*|\* .*|\- .*|\d+\. .*|```[\s\S]*```|`[^`]+`/m.test(displayValue);
    const hasHtml = /<[a-z][\s\S]*>/i.test(displayValue);
    
    if (hasMarkdown || hasHtml) {
      setIsEditing(false);
    }
  };

  // If content is HTML/markdown and not editing, show preview
  if (isHtmlContent.current && !isEditing && !isStreaming) {
    return (
      <div className="relative">
        <div
          ref={previewRef}
          onClick={handlePreviewClick}
          className={`${className} min-h-[${rows * 1.5}rem] px-4 py-3 border border-gray-300 rounded-xl cursor-text prose prose-sm max-w-none focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent`}
          style={{ minHeight: `${rows * 1.5}rem` }}
        >
          {!value && (
            <div className="text-gray-400 italic">{placeholder}</div>
          )}
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="absolute top-2 right-2 px-2 py-1 text-xs text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
          >
            Edit
          </button>
        )}
      </div>
    );
  }

  // Show textarea for editing
  return (
    <textarea
      ref={textareaRef}
      id={id}
      value={displayValue}
      onChange={handleTextareaChange}
      onBlur={handleBlur}
      placeholder={placeholder}
      rows={rows}
      disabled={disabled}
      className={className}
    />
  );
}

