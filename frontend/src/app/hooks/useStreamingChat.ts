import { useState, useCallback, useRef } from 'react';  
  
interface StreamingChatHook {  
  sendMessage: (message: string) => Promise<void>;  
  isStreaming: boolean;  
  streamingContent: string;  
  error: string | null;  
}  
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
interface Message {  
    message_id: string;  
    conversation_id: string;  
    role: "user" | "assistant";  
    content: string;  
    timestamp: string;  
    metadata: any;  
  }  
export function useStreamingChat(  
  conversationId: string,  
  onMessageComplete: (message: Message) => void  
): StreamingChatHook {  
  const [isStreaming, setIsStreaming] = useState(false);  
  const [streamingContent, setStreamingContent] = useState('');  
  const [error, setError] = useState<string | null>(null);  
    
  const abortControllerRef = useRef<AbortController | null>(null);  
  const streamingMessageIdRef = useRef<string | null>(null);  
  
  const sendMessage = useCallback(async (userMessage: string) => {  
    if (isStreaming || !userMessage.trim()) return;  
  
    // Annuler tout streaming précédent  
    if (abortControllerRef.current) {  
      abortControllerRef.current.abort();  
    }  
  
    const abortController = new AbortController();  
    abortControllerRef.current = abortController;  
  
    setIsStreaming(true);  
    setStreamingContent('');  
    setError(null);  
  
    try {  
      const token = localStorage.getItem("access_token");  
        
      // 1. Envoyer le message utilisateur  
      const messageResponse = await fetch(  
        `${API_BASE_URL}/api/chat/conversations/${conversationId}/messages`,  
        {  
          method: "POST",  
          headers: {  
            Authorization: `Bearer ${token}`,  
            "Content-Type": "application/json",  
          },  
          body: JSON.stringify({ content: userMessage, metadata: {} }),  
          signal: abortController.signal,  
        }  
      );  
  
      if (!messageResponse.ok) {  
        throw new Error("Échec de l'envoi du message");  
      }  
  
      const sentMessage = await messageResponse.json();  
      onMessageComplete(sentMessage);  
  
      // 2. Démarrer le streaming avec contrôle de terminaison  
      const streamResponse = await fetch(  
        `${API_BASE_URL}/api/chat/conversations/${conversationId}/stream`,  
        {  
          method: "POST",  
          headers: {  
            Authorization: `Bearer ${token}`,  
            "Content-Type": "application/json",  
          },  
          body: JSON.stringify({   
            message: userMessage,   
            stream: true,  
            single_response: true // Flag pour éviter les réponses multiples  
          }),  
          signal: abortController.signal,  
        }  
      );  
  
      if (!streamResponse.ok) {  
        throw new Error("Échec du streaming");  
      }  
  
      const reader = streamResponse.body?.getReader();  
      const decoder = new TextDecoder();  
      let assistantContent = '';  
      let isComplete = false;  
  
      if (reader) {  
        while (!isComplete && !abortController.signal.aborted) {  
          const { done, value } = await reader.read();  
            
          if (done) break;  
  
          const chunk = decoder.decode(value);  
          const lines = chunk.split('\n');  
  
          for (const line of lines) {  
            if (line.startsWith('data: ')) {  
              try {  
                const data = JSON.parse(line.slice(6));  
                  
                // Contrôle de terminaison basé sur Suna  
                if (data.type === 'completion' || data.done === true) {  
                  isComplete = true;  
                  break;  
                }  
                  
                if (data.content && !data.done) {  
                  assistantContent += data.content;  
                  setStreamingContent(assistantContent);  
                }  
              } catch (e) {  
                console.error('Erreur parsing SSE:', e);  
              }  
            }  
          }  
        }  
  
        // Finaliser le message assistant  
        if (assistantContent && !abortController.signal.aborted) {  
          const finalMessage: Message = {  
            message_id: `assistant-${Date.now()}`,  
            conversation_id: conversationId,  
            role: 'assistant',  
            content: assistantContent,  
            timestamp: new Date().toISOString(),  
            metadata: {},  
          };  
          onMessageComplete(finalMessage);  
        }  
      }  
  
    } catch (err: any) {  
      if (err.name !== 'AbortError') {  
        console.error('Erreur streaming:', err);  
        setError(err.message);  
      }  
    } finally {  
      setIsStreaming(false);  
      setStreamingContent('');  
      abortControllerRef.current = null;  
    }  
  }, [conversationId, isStreaming, onMessageComplete]);  
  
  return {  
    sendMessage,  
    isStreaming,  
    streamingContent,  
    error,  
  };  
}