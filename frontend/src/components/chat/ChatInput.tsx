"use client";

import { useRef, useCallback, useEffect } from "react";
import { Paperclip, Send, X } from "lucide-react";
import { VoiceRecorder } from "./voice-message";

interface ChatInputProps {
  input: string;
  setInput: (input: string) => void;
  isTyping: boolean;
  isCancelling: boolean;
  conversationId: string;
  onSendMessage: () => void;
  onCancelStream: () => void;
}

export default function ChatInput({
  input,
  setInput,
  isTyping,
  isCancelling,
  conversationId,
  onSendMessage,
  onCancelStream
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className="bg-white border-t border-gray-200 p-4 flex-shrink-0">
      <div className="max-w-4xl mx-auto">
        <div className="relative bg-gray-50 border border-gray-200 rounded-xl focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
          <div className="flex items-end gap-3 p-3">
            <button 
              className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="Joindre un fichier"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            
            <textarea
              ref={textareaRef}
              className="flex-1 bg-transparent border-none outline-none resize-none text-gray-900 placeholder-gray-500 text-sm leading-relaxed min-h-[24px] max-h-32 font-medium placeholder:font-normal"
              placeholder="Écrivez votre message... (Entrée pour envoyer, Shift+Entrée pour nouvelle ligne)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isTyping}
              rows={1}
            />
            
            <div className="flex items-center gap-2 flex-shrink-0">
                
              <button
                onClick={isTyping ? onCancelStream : onSendMessage}
                disabled={(!input.trim() && !isTyping) || isCancelling}
                className={`p-3 text-white rounded-lg transition-all duration-200 font-medium ${
                  isTyping 
                    ? "bg-red-500 hover:bg-red-600" 
                    : input.trim()
                      ? "bg-blue-600 hover:bg-blue-700"
                      : "bg-gray-300 cursor-not-allowed"
                }`}
                title={isTyping ? "Arrêter la génération" : "Envoyer le message"}
              >
                {isTyping ? (
                  isCancelling ? (
                    <div className="w-5 h-5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                  ) : (
                    <X className="w-5 h-5" />
                  )
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
          </div>
          
          {/* Input Footer */}
          <div className="flex items-center justify-between px-4 pb-3 text-xs text-gray-400">
            <span></span>
            <div className="flex items-center gap-2">
              <span>{input.length} caractères</span>
              {input.length > 0 && <span>• Entrée pour envoyer</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}