import { useState, useRef } from 'react';  
import { Mic, Square } from 'lucide-react';  
  
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
interface VoiceRecorderProps {  
  onTranscription: (text: string) => void;  
  disabled?: boolean;  
  conversationId: string;
}  
  
export const VoiceRecorder = ({ onTranscription, disabled, conversationId }: VoiceRecorderProps) => {  
  const [isRecording, setIsRecording] = useState(false);  
  const [isProcessing, setIsProcessing] = useState(false);  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);  
  const chunksRef = useRef<Blob[]>([]);  
  
  const startRecording = async () => {  
    try {  
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });  
      const mediaRecorder = new MediaRecorder(stream);  
      mediaRecorderRef.current = mediaRecorder;  
      chunksRef.current = [];  
  
      mediaRecorder.ondataavailable = (event) => {  
        if (event.data.size > 0) {  
          chunksRef.current.push(event.data);  
        }  
      };  
  
      mediaRecorder.onstop = async () => {  
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });  
        await sendAudioToBackend(audioBlob);  
        stream.getTracks().forEach(track => track.stop());  
      };  
  
      mediaRecorder.start();  
      setIsRecording(true);  
    } catch (error) {  
      console.error('Error starting recording:', error);  
    }  
  };  
  
  const stopRecording = () => {  
    if (mediaRecorderRef.current && isRecording) {  
      mediaRecorderRef.current.stop();  
      setIsRecording(false);  
      setIsProcessing(true);  
    }  
  };  
  
  const sendAudioToBackend = async (audioBlob: Blob) => {  
    try {  
      const reader = new FileReader();  
      reader.onloadend = async () => {  
        const base64Audio = (reader.result as string).split(',')[1];  
          
        const token = localStorage.getItem("access_token");  
        const response = await fetch(`${API_BASE_URL}/api/chat/conversations/${conversationId}/voice-message`, {  
          method: 'POST',  
          headers: {  
            'Authorization': `Bearer ${token}`,  
            'Content-Type': 'application/json',  
          },  
          body: JSON.stringify({  
            audio_data: base64Audio,  
            audio_format: 'webm',  
            metadata: { source: 'voice' }  
          })  
        });  
  
        if (response.ok) {  
          const result = await response.json();  
          onTranscription(result.content || '');  
        }  
      };  
      reader.readAsDataURL(audioBlob);  
    } catch (error) {  
      console.error('Error sending audio:', error);  
    } finally {  
      setIsProcessing(false);  
    }  
  };   
  
  return (  
    <button  
      onClick={isRecording ? stopRecording : startRecording}  
      disabled={disabled || isProcessing}  
      className={`p-2 rounded-lg transition-colors ${  
        isRecording   
          ? 'text-red-500 bg-red-50 animate-pulse'   
          : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'  
      }`}  
      title={isRecording ? "Arrêter l'enregistrement" : "Enregistrement vocal"}  
    >  
      {isProcessing ? (  
        <div className="w-5 h-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />  
      ) : isRecording ? (  
        <Square className="w-5 h-5" />  
      ) : (  
        <Mic className="w-5 h-5" />  
      )}  
    </button>  
  );  
};
