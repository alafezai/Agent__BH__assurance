"use client";

import { useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DevisDownloadButton from '@/components/DevisDownloadButton';
import {
  Bot,
  User,
  X,
  Copy,
  Volume2,
  MoreVertical,
  Check
} from "lucide-react";

interface Message {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata: any;
}

interface MessageListProps {
  messages: Message[];
  isTyping: boolean;
  isCancelling: boolean;
  onCancelStream: () => void;
}

// Fonction pour extraire l'ID du devis
const extractDevisId = (content: string): string | null => {
  console.log("🔍 Contenu analysé pour devis:", content);
  
  const patterns = [
    /\*\*ID Devis:\*\*\s*`([^`]+)`/i,
    /ID Devis:\s*`([^`]+)`/i,
    /\*\*ID Devis:\*\*\s*([\w-]+)/i,
    /ID Devis:\s*([\w-]+)/i,
    /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i
  ];

  for (let i = 0; i < patterns.length; i++) {
    const pattern = patterns[i];
    const match = content.match(pattern);
    if (match) {
      console.log(`✅ Devis ID trouvé avec pattern ${i + 1}:`, match[1]);
      return match[1];
    }
  }
  
  console.log("❌ Aucun devis ID trouvé");
  return null;
};

// Fonction de nettoyage pour messages FINAUX seulement
const cleanAssistantResponse = (content: string) => {
  if (!content || typeof content !== 'string') {
    return content;
  }

  return content
    .replace(/<function_calls>[\s\S]*?<\/function_calls>/gi, '')
    .replace(/<invoke[\s\S]*?<\/invoke>/gi, '')
    .replace(/\(Résultat du search_rag\)\s*/gi, '')
    .replace(/[ \t]{3,}/g, '  ') // Réduire seulement les espaces multiples excessifs
    .replace(/\n\s*\n\s*\n/g, '\n\n') // Max 2 sauts de ligne consécutifs
    .trim();
};

// Fonction de nettoyage MINIMAL pour le streaming
const cleanStreamingContent = (content: string) => {
  if (!content || typeof content !== 'string') {
    return content;
  }

  // Supprimer SEULEMENT les balises XML, préserver TOUS les espaces
  return content
    .replace(/<function_calls>[\s\S]*?<\/function_calls>/gi, '')
    .replace(/<invoke[\s\S]*?<\/invoke>/gi, '')
    .replace(/\(Résultat du search_rag\)\s*/gi, '');
};

// Styles Markdown
const markdownStyles = `
.prose {
  max-width: none;
  line-height: 1.6;
}

.prose h1, .prose h2, .prose h3 {
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
  color: #1f2937;
}

.prose h2 {
  font-size: 1.25em;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 0.3em;
  margin-top: 2em;
}

.prose h3 {
  font-size: 1.1em;
  color: #374151;
}

.prose p {
  margin-bottom: 1em;
}

.prose ul, .prose ol {
  margin-bottom: 1em;
  padding-left: 1.5em;
}

.prose li {
  margin-bottom: 0.5em;
}

.prose strong {
  font-weight: 600;
  color: #111827;
}

.prose code {
  background-color: #f3f4f6;
  padding: 0.2em 0.4em;
  border-radius: 0.25em;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 0.9em;
}

.prose pre {
  background-color: #1f2937;
  color: #f9fafb;
  padding: 1em;
  border-radius: 0.5em;
  overflow-x: auto;
  margin-bottom: 1.5em;
}

.prose table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.5em;
}

.prose th, .prose td {
  padding: 0.5em;
  border: 1px solid #e5e7eb;
  text-align: left;
}

.prose th {
  background-color: #f9fafb;
  font-weight: 600;
}

.prose a {
  color: #2563eb;
  text-decoration: underline;
}

/* Styles pour le contenu en streaming */
.streaming-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
  font-size: 0.875rem;
}
`;

// Composant Enhanced Markdown
const EnhancedMarkdown = ({ content }: { content: string }) => {
  return (
    <>
      <style>{markdownStyles}</style>
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h2: ({ node, ...props }) => (
              <h2 
                {...props} 
                className="flex items-center gap-2 text-gray-900 border-b border-gray-200 pb-2 mb-4 mt-6"
              />
            ),
            h3: ({ node, ...props }) => (
              <h3 {...props} className="text-gray-800 mt-4 mb-2" />
            ),
            ul: ({ node, ...props }) => (
              <ul {...props} className="list-disc list-inside space-y-1" />
            ),
            ol: ({ node, ...props }) => (
              <ol {...props} className="list-decimal list-inside space-y-1" />
            ),
            li: ({ node, ...props }) => (
              <li {...props} className="pl-2" />
            ),
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto">
                <table {...props} className="min-w-full" />
              </div>
            ),
            code: ({ node, inline, ...props }: any) =>
              inline ? (
                <code {...props} className="bg-gray-100 px-1 py-0.5 rounded text-sm" />
              ) : (
                <pre className="bg-gray-900 text-white p-4 rounded-lg overflow-x-auto">
                  <code {...props} className="text-sm" />
                </pre>
              ),
            blockquote: ({ node, ...props }) => (
              <blockquote
                {...props}
                className="border-l-4 border-blue-200 bg-blue-50 px-4 py-2 italic text-gray-700"
              />
            )
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </>
  );
};

export default function MessageList({ 
  messages, 
  isTyping, 
  isCancelling, 
  onCancelStream 
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedMessage, setCopiedMessage] = useState<string | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const copyMessage = (content: string, messageId: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(content);
      setCopiedMessage(messageId);
      setTimeout(() => setCopiedMessage(null), 2000);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 bg-white h-full">
      <div className="max-w-4xl mx-auto space-y-6 pb-4">
        {messages.map((msg) => {
          const devisId = extractDevisId(msg.content);
          // Détecter si le message est en cours de streaming
          const isStreaming = msg.message_id.startsWith('temp-');
          
          return (
            <div
              key={msg.message_id}
              className={`flex items-start gap-4 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              {/* Avatar */}
              <div className="flex-shrink-0">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    msg.role === "user"
                      ? "bg-blue-600"
                      : "bg-gray-100 border border-gray-200"
                  }`}
                >
                  {msg.role === "user" ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <Bot className="w-4 h-4 text-gray-600" />
                  )}
                </div>
              </div>

              {/* Message Content */}
              <div className={`flex-1 max-w-[80%] ${msg.role === "user" ? "text-right" : ""}`}>
                <div className={`flex items-center gap-2 mb-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <span className="text-sm font-medium text-gray-600">
                    {msg.role === "user" ? "Vous" : "Assistant"}
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(msg.timestamp).toLocaleTimeString("fr-FR", { 
                      hour: "2-digit", 
                      minute: "2-digit" 
                    })}
                  </span>
                </div>

                <div className={`relative group ${msg.role === "user" ? "ml-auto" : ""}`}>
                  <div
                    className={`px-4 py-3 rounded-2xl ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white rounded-br-md"
                        : "bg-gray-50 text-gray-900 border border-gray-200 rounded-bl-md"
                    }`}
                  >
                    {/* CORRECTION PRINCIPALE: Traitement différent selon le type de message */}
                    {msg.role === "user" ? (
                      // Messages utilisateur - simple texte avec espaces préservés
                      <div className="streaming-content">
                        {msg.content}
                      </div>
                    ) : isStreaming ? (
                      // Messages assistant en streaming - préserver TOUS les espaces
                      <div className="streaming-content">
                        {cleanStreamingContent(msg.content)}
                      </div>
                    ) : (
                      // Messages assistant finaux - utiliser Markdown
                      <div className="prose prose-sm max-w-none">
                        <EnhancedMarkdown content={cleanAssistantResponse(msg.content)} />
                      </div>
                    )}
                  </div>

                  {/* Bouton de téléchargement du devis */}
                  {devisId && msg.role === "assistant" && (
                    <DevisDownloadButton devisId={devisId} />
                  )}

                  {/* Actions du message - seulement pour les messages finaux */}
                  {msg.role === "assistant" && !isStreaming && (
                    <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => copyMessage(msg.content, msg.message_id)}
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Copier"
                      >
                        {copiedMessage === msg.message_id ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Lire"
                      >
                        <Volume2 className="w-4 h-4" />
                      </button>
                      <button
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Plus"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Indicateur de frappe */}
        {isTyping && (
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 rounded-full bg-gray-100 border border-gray-200 flex items-center justify-center">
                <Bot className="w-4 h-4 text-gray-600" />
              </div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-gray-600">Assistant</span>
                <span className="text-xs text-gray-400">écrit...</span>
              </div>
              <div className="bg-gray-50 border border-gray-200 px-4 py-3 rounded-2xl rounded-bl-md max-w-fit flex items-center gap-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
                {isTyping && (
                  <button
                    onClick={onCancelStream}
                    disabled={isCancelling}
                    className="px-3 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded-md text-xs transition-colors border border-red-200 font-medium"
                  >
                    {isCancelling ? 'Annulation...' : 'Arrêter'}
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
      
      {/* Styles inclus dans le composant */}
      <style jsx>{`
        .streaming-content {
          white-space: pre-wrap;
          word-wrap: break-word;
          line-height: 1.6;
          font-size: 0.875rem;
        }
        
        ${markdownStyles}
      `}</style>
    </div>
  );
}