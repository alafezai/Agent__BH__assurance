"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Plus, Bot, User, MessageSquare } from "lucide-react";
import { LogOut } from "lucide-react";
interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  metadata: any;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatDashboard() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/api/conversations/`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
        
      if (!response.ok) throw new Error("Failed to fetch conversations");
        
      const convs = await response.json();
      setConversations(convs);
        
      if (convs.length > 0) {
        router.push(`/chat/${convs[0].conversation_id}`);
      } else {
        await createDefaultConversation();
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const createDefaultConversation = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/api/conversations/`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title: "Nouvelle conversation", metadata: {} }),
      });
        
      if (!response.ok) throw new Error("Failed to create conversation");
        
      const newConv = await response.json();
      router.push(`/chat/${newConv.conversation_id}`);
    } catch (err: any) {
      setError("Erreur lors de la création de la conversation par défaut");
    }
  };

  const handleLogout = async () => {  
    try {  
      // Appeler votre endpoint de logout backend  
      const token = localStorage.getItem("access_token");  
      await fetch(`${API_BASE_URL}/api/auth/logout`, {  
        method: "POST",  
        headers: {  
          "Authorization": `Bearer ${token}`,  
          "Content-Type": "application/json",  
        },  
      });  
        
      // Nettoyer le localStorage  
      localStorage.removeItem("access_token");  
      localStorage.removeItem("refresh_token");  
      localStorage.removeItem("user_id");  
      localStorage.removeItem("token_type");  
        
      // Rediriger vers la page de connexion  
      router.push("/");  
    } catch (error) {  
      console.error("Erreur lors de la déconnexion:", error);  
      // Même en cas d'erreur, nettoyer le localStorage et rediriger  
      localStorage.clear();  
      router.push("/");  
    }  
  };  

  const createNewConversation = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/api/conversations/`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          title: `Conversation ${conversations.length + 1}`, 
          metadata: {} 
        }),
      });
        
      if (!response.ok) throw new Error("Failed to create conversation");
        
      const newConv = await response.json();
      router.push(`/chat/${newConv.conversation_id}`);
    } catch (err: any) {
      setError("Erreur lors de la création de la conversation");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar avec votre design BH Agent */}
      <div className="w-80 bg-white border-r border-slate-200 flex flex-col shadow-sm">
        <div className="p-5 border-b border-slate-200 flex items-center gap-3 bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="w-9 h-9 bg-white rounded-lg flex items-center justify-center shadow-md">
            <Bot className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-white text-base">BH Agent</span>
            <span className="text-blue-100 text-xs">Assistant IA</span>
          </div>
        </div>

        <div className="p-4">
          <button 
            onClick={createNewConversation}
            className="w-full flex items-center gap-2 px-3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all duration-200 shadow-sm hover:shadow-md text-sm"
          >
            <Plus className="w-4 h-4" />
            <span className="font-medium">Nouvelle Conversation</span>
          </button>
        </div>

        <div className="flex-1 px-4 py-2 overflow-y-auto">
          <h3 className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wider">
            Mes Conversations
          </h3>
            
          {error && (
            <div className="text-red-500 text-sm mb-3 p-2 bg-red-50 rounded">{error}</div>
          )}
            
          <div className="space-y-1.5">
            {conversations.map((conv) => (
              <button
                key={conv.conversation_id}
                onClick={() => router.push(`/chat/${conv.conversation_id}`)}
                className="w-full text-left px-3 py-2.5 rounded-lg transition-all duration-200 text-sm group text-slate-700 hover:bg-slate-50 hover:border-l-3 hover:border-slate-300 border border-transparent"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <span className="truncate font-medium block">{conv.title}</span>
                    <span className="text-xs text-slate-400 block mt-1">
                      {new Date(conv.updated_at).toLocaleDateString('fr-FR')}
                    </span>
                    <span className="text-xs text-slate-300 font-mono block mt-1">
                      {conv.conversation_id.slice(0, 8)}...
                    </span>
                  </div>
                  <MessageSquare className="w-4 h-4 text-slate-400 flex-shrink-0 mt-1" />
                </div>
              </button>
            ))}
          </div>
        </div>

    
            

        <div className="p-4 border-t border-slate-200 bg-slate-50 flex flex-col gap-3">
  <div className="flex items-center gap-3">
    <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-blue-700 rounded-full flex items-center justify-center shadow-sm">
      <User className="w-4 h-4 text-white" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="font-semibold text-slate-900 text-sm">Ala FEZAI</p>
      <p className="text-xs text-slate-500">En ligne</p>
    </div>
    <div className="w-2 h-2 bg-green-400 rounded-full shadow-sm animate-pulse"></div>
  </div>

  {/* Bouton de déconnexion - version améliorée */}
  <button
    onClick={handleLogout}
    className="w-full flex items-center gap-2 px-3 py-2 bg-white text-slate-700 hover:bg-red-50 hover:text-red-600 rounded-lg transition-all duration-200 text-sm border border-slate-200 hover:border-red-200"
  >
    <LogOut className="w-4 h-4" />
    <span className="font-medium">Se déconnecter</span>
  </button>
</div>

      </div>

      {/* Contenu Principal */}
      <div className="flex-1 flex flex-col items-center justify-center bg-white">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl mx-auto mb-6 flex items-center justify-center shadow-md">
            <Bot className="w-8 h-8 text-white" />
          </div>
            
          <h2 className="text-2xl font-bold text-slate-800 mb-2">
            Sélectionnez une conversation
          </h2>
            
          <p className="text-slate-600 mb-6">
            Choisissez une conversation existante ou créez-en une nouvelle
          </p>

          {conversations.length > 0 && (
            <div className="bg-slate-50 rounded-lg p-4 text-sm text-slate-600">
              <p className="font-medium mb-2">Statistiques :</p>
              <p>{conversations.length} conversation{conversations.length > 1 ? 's' : ''} disponible{conversations.length > 1 ? 's' : ''}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}