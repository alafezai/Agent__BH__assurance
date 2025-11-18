"use client";
import { Bot, Menu, Trash2, X } from "lucide-react";

interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  metadata: any;
}

interface ChatHeaderProps {
  currentConversation: Conversation | null;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  messagesCount: number;
  onDeleteClick: () => void;
}

export default function ChatHeader({
  currentConversation,
  sidebarOpen,
  setSidebarOpen,
  messagesCount,
  onDeleteClick
}: ChatHeaderProps) {
  return (
    <>
      {/* Mobile Header - Toujours visible sur mobile */}
      <div className="lg:hidden bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between flex-shrink-0">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <span className="font-medium text-gray-900">BH Agent</span>
        </div>
        <div className="w-9"></div>
      </div>

      {/* Desktop Chat Header - Visible seulement si conversation existe */}
      {currentConversation && (
        <div className="hidden lg:flex bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0 items-center justify-between">
          {/* Bouton menu pour réduire/étendre la sidebar */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title={sidebarOpen ? "Réduire la sidebar" : "Étendre la sidebar"}
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>

          {/* Titre + nombre de messages centrés */}
          <div className="flex flex-col items-center text-center">
            <div className="flex items-center gap-3">
              {/* Icône Bot */}
              <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              {/* Titre et messages */}
              <div>
                <h1 className="text-xl font-semibold text-gray-900">
                  {currentConversation.title}
                </h1>
                <p className="text-sm text-gray-500">
                  {messagesCount > 0 ? `${messagesCount} messages` : "Prêt à discuter"}
                </p>
              </div>
            </div>
          </div>

          {/* Bouton Supprimer à droite */}
          <button
            onClick={onDeleteClick}
            className="flex items-center gap-2 px-3 py-2 text-red-600 hover:bg-red-50 border border-red-200 rounded-lg transition-colors text-sm font-medium"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Supprimer</span>
          </button>
        </div>
      )}
    </>
  );
}