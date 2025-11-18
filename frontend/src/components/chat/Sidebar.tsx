"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  Plus, 
  MessageSquare, 
  LogOut, 
  Settings, 
  User,
  ChevronLeft,
  ChevronRight
} from "lucide-react";

interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  metadata: any;
}

interface SidebarProps {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  conversations: Conversation[];
  currentConversation: Conversation | null;
  error: string | null;
  onCreateNewConversation: () => void;
  onLogout: () => void;
}

export default function Sidebar({
  sidebarOpen,
  setSidebarOpen,
  conversations,
  currentConversation,
  error,
  onCreateNewConversation,
  onLogout
}: SidebarProps) {
  const router = useRouter();

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return "Aujourd'hui";
    if (diffDays === 2) return "Hier";
    if (diffDays <= 7) return `Il y a ${diffDays - 1} jours`;
    return date.toLocaleDateString("fr-FR", { 
      day: "numeric", 
      month: "short" 
    });
  };

  const truncateTitle = (title: string, maxLength: number = 25) => {
    return title.length > maxLength ? title.substring(0, maxLength) + "..." : title;
  };

  return (
    <div 
      className={`
        ${sidebarOpen ? 'w-80' : 'w-16'} 
        bg-white border-r border-gray-200 flex flex-col h-full
        sidebar-transition overflow-hidden
        ${sidebarOpen ? 'min-w-80' : 'min-w-16'}
      `}
    >
      {/* Header de la sidebar */}
      <div className="p-4 border-b border-gray-200 flex-shrink-0">
        <div className="flex items-center justify-between">
          {sidebarOpen ? (
            <>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-bh-accent rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-white" />
                </div>
                <div>
                  <span className="brand-text-bh">BH</span>
                  <span className="brand-text-assurance"> Assurance</span>
                  <span className="brand-text-ai"> AI</span>
                </div>
              </div>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                title="Réduire la sidebar"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </>
          ) : (
            <button
              onClick={() => setSidebarOpen(true)}
              className="w-full flex justify-center p-1 text-gray-400 hover:text-gray-600 transition-colors"
              title="Étendre la sidebar"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Bouton Nouvelle Conversation */}
      <div className="p-4 flex-shrink-0">
        <button
          onClick={onCreateNewConversation}
          className={`
            w-full flex items-center gap-3 p-3 bg-bh-primary text-white rounded-lg 
            hover:bg-bh-dark transition-all duration-200 font-medium
            ${!sidebarOpen ? 'justify-center' : 'justify-start'}
          `}
          title={sidebarOpen ? "Nouvelle conversation" : "Nouveau"}
        >
          <Plus className="w-5 h-5 flex-shrink-0" />
          {sidebarOpen && <span>Nouvelle conversation</span>}
        </button>
      </div>

      {/* Liste des conversations */}
      <div className="flex-1 overflow-y-auto px-4">
        {error && sidebarOpen && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-2">
          {conversations.map((conv) => (
            <button
              key={conv.conversation_id}
              onClick={() => router.push(`/chat/${conv.conversation_id}`)}
              className={`
                w-full p-3 rounded-lg text-left transition-all duration-200 group
                ${currentConversation?.conversation_id === conv.conversation_id
                  ? 'bg-bh-primary text-white shadow-sm'
                  : 'text-gray-700 hover:bg-gray-100'
                }
                ${!sidebarOpen ? 'flex justify-center' : ''}
              `}
              title={!sidebarOpen ? conv.title : undefined}
            >
              {sidebarOpen ? (
                <div className="flex flex-col gap-1">
                  <div className="font-medium text-sm leading-tight">
                    {truncateTitle(conv.title)}
                  </div>
                  <div className={`
                    text-xs opacity-75
                    ${currentConversation?.conversation_id === conv.conversation_id
                      ? 'text-blue-100'
                      : 'text-gray-500'
                    }
                  `}>
                    {formatDate(conv.updated_at)}
                  </div>
                </div>
              ) : (
                <MessageSquare className="w-5 h-5 flex-shrink-0" />
              )}
            </button>
          ))}

          {conversations.length === 0 && sidebarOpen && (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">Aucune conversation</p>
              <p className="text-xs mt-1">Créez votre première conversation</p>
            </div>
          )}
        </div>
      </div>

      {/* Footer avec user actions */}
      <div className="p-4 border-t border-gray-200 flex-shrink-0">
        <div className={`space-y-2 ${!sidebarOpen ? 'flex flex-col items-center' : ''}`}>
          {/* Bouton Paramètres */}
          <button
            className={`
              w-full flex items-center gap-3 p-2 text-gray-600 hover:bg-gray-100 
              rounded-lg transition-colors
              ${!sidebarOpen ? 'justify-center' : 'justify-start'}
            `}
            title={sidebarOpen ? "Paramètres" : "Paramètres"}
          >
            <Settings className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span className="text-sm">Paramètres</span>}
          </button>

          {/* Bouton Profil */}
          <button
            className={`
              w-full flex items-center gap-3 p-2 text-gray-600 hover:bg-gray-100 
              rounded-lg transition-colors
              ${!sidebarOpen ? 'justify-center' : 'justify-start'}
            `}
            title={sidebarOpen ? "Profil" : "Profil"}
          >
            <User className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span className="text-sm">Profil</span>}
          </button>

          {/* Bouton Déconnexion */}
          <button
            onClick={onLogout}
            className={`
              w-full flex items-center gap-3 p-2 text-red-600 hover:bg-red-50 
              rounded-lg transition-colors
              ${!sidebarOpen ? 'justify-center' : 'justify-start'}
            `}
            title={sidebarOpen ? "Déconnexion" : "Déconnexion"}
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {sidebarOpen && <span className="text-sm">Déconnexion</span>}
          </button>
        </div>
      </div>
    </div>
  );
}