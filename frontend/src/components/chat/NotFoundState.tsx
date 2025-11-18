"use client";

import { Bot } from "lucide-react";

interface NotFoundStateProps {
  onBackToChat: () => void;
}

export default function NotFoundState({ onBackToChat }: NotFoundStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-white">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl mx-auto mb-6 flex items-center justify-center">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-3">
          Conversation introuvable
        </h2>
        <p className="text-gray-600 mb-6">
          Cette conversation n'existe pas ou a été supprimée.
        </p>
        <button
          onClick={onBackToChat}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Retour aux conversations
        </button>
      </div>
    </div>
  );
}