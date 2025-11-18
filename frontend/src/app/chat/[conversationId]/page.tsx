"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";

// Import des composants
import Sidebar from '@/components/chat/Sidebar';
import ChatHeader from '@/components/chat/ChatHeader';
import MessageList from '@/components/chat/MessageList';
import ChatInput from '@/components/chat/ChatInput';
import DeleteModal from '@/components/chat/DeleteModal';
import EmptyState from '@/components/chat/EmptyState';
import LoadingState from '@/components/chat/LoadingState';
import NotFoundState from '@/components/chat/NotFoundState';

// Types
interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  metadata: any;
}

interface Message {
  message_id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  metadata: any;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ConversationPage() {
  const router = useRouter();
  const params = useParams();
  const conversationId = params?.conversationId as string;

  // States
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  // Changement: true = étendue, false = réduite
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const loadedMessagesRef = useRef(false);
  const loadedConversationsRef = useRef(false);

  // Quick actions pour l'état vide
  const quickActions = [
    "",
  ];

  // Effects
  useEffect(() => {
    const token = localStorage?.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }
  
    if (!loadedConversationsRef.current) {
      loadConversations();
      loadedConversationsRef.current = true;
    }
  }, [router]);
  
  useEffect(() => {
    if (conversationId && !loadedMessagesRef.current) {
      loadCurrentConversation();
      loadMessages();
      loadedMessagesRef.current = true;
    }
  
    return () => {
      loadedMessagesRef.current = false;
    };
  }, [conversationId]);

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // API Functions (identiques à votre code existant)
  const loadConversations = async () => {
    try {
      const token = localStorage?.getItem("access_token");
      if (!token) return;
      
      const response = await fetch(`${API_BASE_URL}/api/conversations/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) throw new Error("Échec du chargement des conversations");
      const convs = await response.json();
      setConversations(convs);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const loadCurrentConversation = async () => {
    if (!conversationId) return;
    
    try {
      const token = localStorage?.getItem("access_token");
      if (!token) return;
      
      const response = await fetch(
        `${API_BASE_URL}/api/conversations/${conversationId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) throw new Error("Conversation introuvable");
      const conv = await response.json();
      setCurrentConversation(conv);
    } catch (err: any) {
      setError(err.message);
      setCurrentConversation(null);
    }
  };

  const removeDuplicateMessages = (messages: Message[]): Message[] => {
    const seen = new Map();
    const filtered: Message[] = [];
    
    for (const msg of messages) {
      const contentKey = msg.content.length > 50 
        ? msg.content.substring(0, 25) + msg.content.substring(msg.content.length - 25)
        : msg.content;
      
      const key = `${msg.role}-${msg.timestamp}-${contentKey}`;
      
      if (!msg.message_id.startsWith('temp-') && !seen.has(key)) {
        seen.set(key, true);
        filtered.push(msg);
      } else if (msg.message_id.startsWith('temp-')) {
        filtered.push(msg);
      }
    }
    
    return filtered;
  };
  
  const loadMessages = async () => {
    if (!conversationId) return;
    
    try {
      setIsLoading(true);
      const token = localStorage?.getItem("access_token");
      if (!token) return;
      
      const response = await fetch(
        `${API_BASE_URL}/api/chat/conversations/${conversationId}/messages`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) throw new Error("Échec du chargement des messages");
      const msgs = await response.json();
      
      const cleanedMessages = removeDuplicateMessages(msgs)
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
        .map(msg => ({
          ...msg,
          content: msg.role === "assistant" ? cleanAssistantResponse(msg.content) : msg.content
        }));
      
      setMessages(cleanedMessages);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const cleanAssistantResponse = (content: string) => {
    if (!content || typeof content !== 'string') {
      return content;
    }
  
    let cleaned = content
      // Supprimer les balises XML mais préserver les espaces
      .replace(/<function_calls>[\s\S]*?<\/function_calls>/gi, '')
      .replace(/<invoke[\s\S]*?<\/invoke>/gi, '')
      .replace(/\(Résultat du search_rag\)\s*/gi, '');
  
    // Nettoyer les espaces multiples mais préserver la structure
    cleaned = cleaned
      .replace(/\n\s*\n\s*\n/g, '\n\n') // Max 2 sauts de ligne consécutifs
      .replace(/[ \t]{3,}/g, '  ')        // Max 2 espaces consécutifs
      .trim();
  
    return cleaned;
  };

  const messageDisplayCSS = `
  .message-content {
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.5;
  }
  
  .message-content p {
    margin-bottom: 0.5rem;
  }
  
  .message-content:last-child {
    margin-bottom: 0;
  }
`;

  const cancelStream = () => {
    if (abortControllerRef.current) {
      setIsCancelling(true);
      abortControllerRef.current.abort();
      setIsTyping(false);
    }
  };

  const streamLLMResponse = async (userMessage: string) => {
    const tempAssistantId = `temp-assistant-${Date.now()}`;
    let fullResponse = "";
    
    abortControllerRef.current = new AbortController();
    setIsCancelling(false);
  
    setMessages(prev => [...prev, {
      message_id: tempAssistantId,
      conversation_id: conversationId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      metadata: {}
    }]);
  
    try {
      const token = localStorage?.getItem("access_token");
      if (!token) return;
      
      const response = await fetch(
        `${API_BASE_URL}/api/chat/conversations/${conversationId}/stream`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json; charset=utf-8", // Encodage explicite
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            message: userMessage,
            stream: true
          }),
          signal: abortControllerRef.current.signal
        }
      );
  
      if (!response.ok) throw new Error("Erreur de requête");
      if (!response.body) throw new Error("Pas de corps de réponse");
  
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8"); // Décodage UTF-8 explicite
      let buffer = "";
  
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
  
        // Décodage avec preservation des caractères UTF-8
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || "";
  
        for (const line of lines) {
          if (line.startsWith('data: ') && line.trim() !== 'data: [DONE]') {
            try {
              const dataString = line.substring(6).trim();
              if (!dataString) continue;
              
              const data = JSON.parse(dataString);
              
              if (data.content) {
                // CORRECTION PRINCIPALE: Gestion correcte de l'accumulation
                if (data.action === 'create') {
                  // Nouveau message - remplacer complètement
                  fullResponse = data.content;
                } else if (data.action === 'append') {
                  // Ajouter le nouveau contenu à la fin
                  fullResponse += data.content;
                } else if (typeof data.content === 'string') {
                  // Fallback: traiter comme contenu complet si pas d'action
                  if (data.content.length > fullResponse.length) {
                    fullResponse = data.content;
                  } else {
                    // Éviter la duplication - seulement ajouter le nouveau contenu
                    const newContent = data.content;
                    if (!fullResponse.includes(newContent)) {
                      fullResponse += newContent;
                    }
                  }
                }
                
                // Mettre à jour l'affichage avec le contenu accumulé
                setMessages(prev =>
                  prev.map(msg =>
                    msg.message_id === tempAssistantId
                      ? { ...msg, content: fullResponse }
                      : msg
                  )
                );
              }
              
              // Gérer la completion
              if (data.action === 'complete') {
                break;
              }
              
            } catch (parseError) {
              console.error("Erreur parsing SSE:", parseError, "Line:", line);
              continue;
            }
          }
        }
      }
  
      // Nettoyage final du contenu
      const finalContent = cleanAssistantResponse(fullResponse);
      const finalMessageId = `assistant-${Date.now()}`;
      
      setMessages(prev => 
        prev.map(msg => 
          msg.message_id === tempAssistantId 
            ? { 
                ...msg, 
                message_id: finalMessageId,
                content: finalContent
              }
            : msg
        )
      );
  
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        console.log("Stream annulé par l'utilisateur");
      } else {
        console.error("Erreur streaming:", err);
        throw err;
      }
      setMessages(prev => prev.filter(msg => msg.message_id !== tempAssistantId));
    } finally {
      abortControllerRef.current = null;
      setIsCancelling(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isTyping || !currentConversation) return;

    const userMessage = input;
    const userMessageId = `user-${Date.now()}`;

    setMessages(prev => [...prev, {
      message_id: userMessageId,
      conversation_id: conversationId,
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString(),
      metadata: {}
    }]);

    setInput("");
    setIsTyping(true);
    setError("");

    try {
      await streamLLMResponse(userMessage);
    } catch (err: any) {
      console.error("Error:", err);
      setError(err.message);
      setMessages(prev => prev.filter(msg => msg.message_id !== userMessageId));
    } finally {
      setIsTyping(false);
    }
  };

  const createNewConversation = async () => {
    try {
      setError("");
      const token = localStorage?.getItem("access_token");
      if (!token) return;
      
      const response = await fetch(`${API_BASE_URL}/api/conversations/`, {
        method: "POST",
        headers: {  
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: `Conversation ${conversations.length + 1}`,
          metadata: {},
        }),
      });

      if (!response.ok) throw new Error("Échec de création");
      const newConv = await response.json();
      router.push(`/chat/${newConv.conversation_id}`);
    } catch (err: any) {
      setError("Impossible de créer une nouvelle conversation");
    }
  };

  const deleteConversation = async () => {  
    if (!conversationId) return;  

    try {  
      setIsDeleting(true);  
      setError(null);  

      const token = localStorage?.getItem("access_token");  
      if (!token) {  
        throw new Error("Utilisateur non authentifié.");  
      }  

      const response = await fetch(  
        `${API_BASE_URL}/api/conversations/${conversationId}`,  
        {  
          method: "DELETE",  
          headers: {  
            Authorization: `Bearer ${token}`,  
            "Content-Type": "application/json",  
          },  
        }  
      );  

      if (!response.ok) {  
        const errorText = await response.text();  
        let errorMessage = "Échec de la suppression";  

        try {  
          const errorData = JSON.parse(errorText);  
          errorMessage = errorData.detail || errorMessage;  
        } catch {  
          errorMessage = errorText || errorMessage;  
        }  

        throw new Error(errorMessage);  
      }  

      setShowDeleteModal(false);  
      router.push("/chat");  

    } catch (err: any) {  
      console.error("Delete conversation error:", err);  
      setError(err.message || "Erreur inconnue");  

    } finally {  
      setIsDeleting(false);  
    }  
  };  

  const handleLogout = async () => {
    try {
      const token = localStorage?.getItem("access_token");
      if (token) {
        await fetch(`${API_BASE_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
      }
    } catch (error) {
      console.error("Erreur logout:", error);
    } finally {
      localStorage?.clear();
      router.push("/");
    }
  };

  const handleQuickAction = (action: string) => {
    setInput(action);
    setTimeout(() => sendMessage(), 100);
  };

  // Loading state
  if (isLoading && !currentConversation) {
    return <LoadingState />;
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar - toujours présente mais avec largeur variable */}
      <Sidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        conversations={conversations}
        currentConversation={currentConversation}
        error={error}
        onCreateNewConversation={createNewConversation}
        onLogout={handleLogout}
      />

      {/* Main Content - Largeur s'adapte selon l'état de la sidebar */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {currentConversation ? (
          <>
            {/* Chat Header avec nouveau branding */}
            <div className="bg-white border-b border-gray-200 px-6 py-4">
              <div className="items-left justify-between">
                <div className="items-center gap-4">
                  {/* Logo/Icon de l'assistant */}
                  {/* Branding texte */}
                </div>

                <ChatHeader
                  currentConversation={currentConversation}
                  sidebarOpen={sidebarOpen}
                  setSidebarOpen={setSidebarOpen}
                  messagesCount={messages.length}
                  onDeleteClick={() => setShowDeleteModal(true)}
                />
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {messages.length === 0 ? (
                <EmptyState 
                  quickActions={quickActions}
                  onActionClick={handleQuickAction}
                />
              ) : (
                <div className="flex-1 overflow-hidden">
                  <MessageList
                    messages={messages}
                    isTyping={isTyping}
                    isCancelling={isCancelling}
                    onCancelStream={cancelStream}
                  />
                </div>
              )}

              {/* Input Area - Fixed at bottom */}
              <div className="flex-shrink-0">
                <ChatInput
                  input={input}
                  setInput={setInput}
                  isTyping={isTyping}
                  isCancelling={isCancelling}
                  conversationId={conversationId}
                  onSendMessage={sendMessage}
                  onCancelStream={cancelStream}
                />
              </div>
            </div>
          </>
        ) : (
          <NotFoundState onBackToChat={() => router.push("/chat")} />
        )}
      </div>

      {/* Delete Modal */}
      <DeleteModal
        showDeleteModal={showDeleteModal}
        isDeleting={isDeleting}
        onClose={() => setShowDeleteModal(false)}
        onConfirmDelete={deleteConversation}
      />

      {/* Custom Styles avec nouvelles couleurs et animations de transition */}
      <style jsx global>{`
        /* Assurer que le body et html prennent toute la hauteur */
        html, body {
          height: 100%;
          margin: 0;
          padding: 0;
          overflow: hidden;
        }

        /* Transitions fluides pour la sidebar */
        .sidebar-transition {
          transition: width 0.3s ease-in-out, min-width 0.3s ease-in-out;
        }

        /* Couleur principale BH */
        .bg-bh-primary {
          background-color: #154c79 !important;
        }
        
        .text-bh-primary {
          color: #154c79 !important;
        }
        
        .border-bh-primary {
          border-color: #154c79 !important;
        }

        /* Couleur accent rouge */
        .bg-bh-accent {
          background-color: #f03028 !important;
        }
        
        .text-bh-accent {
          color: #f03028 !important;
        }

        /* Couleur sombre */
        .bg-bh-dark {
          background-color: #072641 !important;
        }
        
        .text-bh-dark {
          color: #072641 !important;
        }

        /* Remplacer les couleurs bleues par les couleurs BH */
        .bg-blue-600, .bg-blue-700, .bg-blue-800 {
          background-color: #154c79 !important;
        }
        
        .hover\\:bg-blue-700:hover {
          background-color: #072641 !important;
        }
        
        .text-blue-600 {
          color: #154c79 !important;
        }
        
        .border-blue-200 {
          border-color: #154c79 !important;
        }
        
        .ring-blue-100 {
          ring-color: rgba(21, 76, 121, 0.1) !important;
        }

        /* Messages utilisateur avec couleur BH */
        .bg-blue-600.text-white {
          background: linear-gradient(135deg, #154c79 0%, #072641 100%) !important;
        }

        /* Scrollbar personnalisé avec couleurs BH */
        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: #154c79;
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: #072641;
        }

        /* Animation pour les messages */
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .animate-fade-in {
          animation: fadeInUp 0.3s ease-out;
        }

        /* Responsive textarea */
        textarea {
          field-sizing: content;
        }

        /* Focus states avec couleurs BH */
        .focus-within\\:ring-2:focus-within {
          ring-width: 2px;
          ring-color: rgba(21, 76, 121, 0.2) !important;
        }

        /* Hover effects pour les messages */
        .group:hover .group-hover\\:opacity-100 {
          opacity: 1;
        }

        /* Animation de typing plus fluide */
        .animate-bounce {
          animation: bounce 1.2s infinite;
        }

        @keyframes bounce {
          0%, 60%, 100% {
            transform: translateY(0);
          }
          30% {
            transform: translateY(-4px);
          }
        }

        /* Mobile optimizations */
        @media (max-width: 640px) {
          .prose {
            font-size: 14px;
          }
          
          .max-w-\\[80\\%\\] {
            max-width: 90%;
          }
        }

        /* Loading state pour le bouton avec couleur BH */
        .animate-spin {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        /* Boutons avec gradient BH */
        .btn-bh-gradient {
          background: linear-gradient(135deg, #154c79 0%, #072641 100%);
          transition: all 0.3s ease;
        }
        
        .btn-bh-gradient:hover {
          background: linear-gradient(135deg, #072641 0%, #154c79 100%);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(21, 76, 121, 0.3);
        }

        /* Status indicator pulse */
        .animate-pulse {
          animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: .5;
          }
        }

        /* Smooth transitions partout */
        * {
          transition-property: color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter;
          transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
          transition-duration: 150ms;
        }

        /* Éviter les espaces supplémentaires */
        .chat-container {
          height: 100vh;
          overflow: hidden;
        }

        .chat-content {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        /* Fix pour l'input qui colle au bas */
        .chat-input-container {
          position: sticky;
          bottom: 0;
          background: white;
          border-top: 1px solid #e5e7eb;
          z-index: 10;
        }

        /* Assistant avatar avec couleur rouge */
        .assistant-avatar {
          background-color: #f03028 !important;
        }

        /* Branding dans le header */
        .brand-text-bh {
          color: #f03028;
          font-weight: 700;
        }
        
        .brand-text-assurance {
          color: #072641;
          font-weight: 700;
        }
        
        .brand-text-ai {
          color: #000000;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}