'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  isStreaming?: boolean;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ 
  content, 
  isStreaming = false 
}) => {
  // Nettoyer le markdown pendant le streaming
  const cleanContent = (text: string) => {
    if (!isStreaming) return text;
    
    // Supprimer le markdown brut pendant le streaming
    return text
      .replace(/\*\*(.*?)\*\*/g, '$1') // **gras** → gras
      .replace(/\*(.*?)\*/g, '$1')     // *italique* → italique
      .replace(/### (.*?)(\n|$)/g, '$1\n') // ### titre → titre
      .replace(/## (.*?)(\n|$)/g, '$1\n')  // ## titre → titre
      .replace(/# (.*?)(\n|$)/g, '$1\n');   // # titre → titre
  };

  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {cleanContent(content)}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;