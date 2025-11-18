"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Square, Volume2 } from "lucide-react";

interface VoiceRecorderProps {
  onTranscription: (text: string) => void;
  disabled?: boolean;
  conversationId: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function VoiceRecorder({ 
  onTranscription, 
  disabled = false, 
  conversationId 
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number | null>(null);

  // Nettoyage lors du démontage du composant
  useEffect(() => {
    return () => {
      stopRecording();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  // Analyser le niveau audio pour l'animation
  const analyzeAudio = () => {
    if (!analyserRef.current) return;

    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculer le niveau moyen
    const average = dataArray.reduce((a, b) => a + b) / bufferLength;
    setAudioLevel(average / 255);

    if (isRecording) {
      animationRef.current = requestAnimationFrame(analyzeAudio);
    }
  };

  const startRecording = async () => {
    try {
      setError(null);
      setRecordingTime(0);

      // Demander l'autorisation d'accès au microphone
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        } 
      });
      
      streamRef.current = stream;

      // Configurer l'analyseur audio pour l'animation
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      // Configurer MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        processAudio();
      };

      mediaRecorder.start(100); // Collecter des chunks toutes les 100ms
      setIsRecording(true);

      // Démarrer le timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      // Démarrer l'analyse audio
      analyzeAudio();

      // Arrêter automatiquement après 5 minutes
      setTimeout(() => {
        if (isRecording) {
          stopRecording();
        }
      }, 300000); // 5 minutes

    } catch (err: any) {
      console.error("Erreur microphone:", err);
      setError("Impossible d'accéder au microphone. Vérifiez les permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setAudioLevel(0);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const processAudio = async () => {
    if (audioChunksRef.current.length === 0) {
      setError("Aucun audio enregistré");
      return;
    }

    setIsProcessing(true);

    try {
      // Créer le blob audio
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      // Vérifier la taille du fichier (max 25MB)
      if (audioBlob.size > 25 * 1024 * 1024) {
        throw new Error("Enregistrement trop long. Maximum 5 minutes.");
      }

      // Préparer FormData pour l'envoi
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      formData.append('conversation_id', conversationId);

      // Envoyer au serveur pour transcription
      const token = localStorage?.getItem("access_token");
      if (!token) {
        throw new Error("Token d'authentification manquant");
      }

      const response = await fetch(`${API_BASE_URL}/api/speech/transcribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Erreur ${response.status}`);
      }

      const result = await response.json();
      
      if (result.transcription && result.transcription.trim()) {
        onTranscription(result.transcription.trim());
      } else {
        setError("Aucun texte détecté dans l'enregistrement");
      }

    } catch (err: any) {
      console.error("Erreur transcription:", err);
      setError(err.message || "Erreur lors de la transcription");
    } finally {
      setIsProcessing(false);
      setRecordingTime(0);
      audioChunksRef.current = [];
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Vérifier si le navigateur supporte l'enregistrement
  const isSupported = typeof navigator !== 'undefined' && 
                     navigator.mediaDevices && 
                     navigator.mediaDevices.getUserMedia;

  if (!isSupported) {
    return null; // Ne pas afficher le bouton si non supporté
  }

  return (
    <div className="relative">
      {/* Bouton principal */}
      <button
        onClick={isRecording ? stopRecording : startRecording}
        disabled={disabled || isProcessing}
        className={`p-2 rounded-lg transition-all duration-300 ${
          isRecording
            ? "bg-red-500 hover:bg-red-600 text-white animate-pulse"
            : isProcessing
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : "text-gray-400 hover:text-gray-600 hover:bg-gray-100"
        }`}
        title={
          isRecording 
            ? "Arrêter l'enregistrement" 
            : isProcessing 
            ? "Transcription en cours..." 
            : "Enregistrer un message vocal"
        }
      >
        {isProcessing ? (
          <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
        ) : isRecording ? (
          <Square className="w-5 h-5" />
        ) : (
          <Mic className="w-5 h-5" />
        )}
      </button>

      {/* Indicateur de niveau audio */}
      {isRecording && (
        <div className="absolute -top-2 -right-2">
          <div 
            className="w-3 h-3 bg-red-500 rounded-full animate-pulse"
            style={{
              transform: `scale(${1 + audioLevel * 0.5})`,
              opacity: 0.7 + audioLevel * 0.3
            }}
          />
        </div>
      )}

      {/* Timer d'enregistrement */}
      {isRecording && (
        <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-2 py-1 rounded text-xs font-mono whitespace-nowrap">
          {formatTime(recordingTime)}
        </div>
      )}

      {/* Indicateur de traitement */}
      {isProcessing && (
        <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-blue-500 text-white px-2 py-1 rounded text-xs whitespace-nowrap">
          Transcription...
        </div>
      )}

      {/* Message d'erreur */}
      {error && (
        <div className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 bg-red-100 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-xs max-w-xs text-center">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      )}

      {/* Instructions d'utilisation (tooltip) */}
      {!isRecording && !isProcessing && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-gray-800 text-white px-3 py-2 rounded-lg text-xs opacity-0 group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap pointer-events-none">
          Cliquez et maintenez pour enregistrer
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800" />
        </div>
      )}
    </div>
  );
}

// Hook personnalisé pour gérer les permissions du microphone
export function useMicrophonePermission() {
  const [permission, setPermission] = useState<'granted' | 'denied' | 'prompt' | 'unknown'>('unknown');

  useEffect(() => {
    if (typeof navigator !== 'undefined' && navigator.permissions) {
      navigator.permissions.query({ name: 'microphone' as PermissionName })
        .then(result => {
          setPermission(result.state as any);
          result.onchange = () => {
            setPermission(result.state as any);
          };
        })
        .catch(() => setPermission('unknown'));
    }
  }, []);

  const requestPermission = async () => {
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      setPermission('granted');
      return true;
    } catch {
      setPermission('denied');
      return false;
    }
  };

  return { permission, requestPermission };
}