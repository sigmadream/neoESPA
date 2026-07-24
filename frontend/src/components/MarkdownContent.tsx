'use client';

import ReactMarkdown from 'react-markdown';

type MarkdownContentProps = {
  content: string;
  className?: string;
};

export default function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  return (
    <div className={`prose dark:prose-invert max-w-none text-slate-700 dark:text-slate-300 leading-relaxed ${className}`}>
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
