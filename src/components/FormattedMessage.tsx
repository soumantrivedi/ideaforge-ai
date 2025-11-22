import { ContentFormatter } from '../lib/content-formatter';

interface FormattedMessageProps {
  content: string;
  className?: string;
}

export function FormattedMessage({ content, className = '' }: FormattedMessageProps) {
  const formattedHtml = ContentFormatter.markdownToHtml(content);

  return (
    <div
      className={`formatted-content prose prose-sm max-w-none ${className}`}
      dangerouslySetInnerHTML={{ __html: formattedHtml }}
    />
  );
}
