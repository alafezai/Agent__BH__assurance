"use client";

import { Bot } from "lucide-react";

interface EmptyStateProps {
  quickActions: string[];
  onActionClick: (action: string) => void;
}

export default function EmptyState({ quickActions, onActionClick }: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 bg-white">
      <div className="max-w-2xl w-full text-center">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl mx-auto mb-6 flex items-center justify-center">
          <Bot className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-semibold text-gray-900 mb-3">
          Comment puis-je vous aider ?
        </h2>
        <p className="text-gray-600 mb-8">
          Choisissez une suggestion ou posez votre propre question
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {quickActions.map((action, idx) => (
            <button
              key={idx}
              onClick={() => onActionClick(action)}
              className="p-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg transition-colors text-left"
            >
              <span className="text-gray-700 font-medium">{action}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}