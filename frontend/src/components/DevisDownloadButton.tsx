'use client';
import { useState, useEffect } from 'react';

interface DevisDownloadButtonProps {
  devisId: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DevisDownloadButton({ devisId }: DevisDownloadButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [debugInfo, setDebugInfo] = useState<string>('');

  const downloadDevis = async () => {
    try {
      setIsLoading(true);
      const url = `${API_BASE_URL}/api/chat/devis/${devisId}/pdf`;
      const response = await fetch(url);
  
      if (!response.ok) throw new Error('PDF non trouvé ou erreur serveur');
  
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `devis_${devisId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      setMessage('✅ PDF téléchargé avec succès');
    } catch (err) {
      console.error(err);
      setMessage('❌ Erreur téléchargement PDF');
    } finally {
      setIsLoading(false);
    }
  };

  const viewDevis = async () => {
    try {
      setIsLoading(true);
      const url = `${API_BASE_URL}/api/chat/devis/${devisId}/pdf`;
      const response = await fetch(url);
  
      if (!response.ok) throw new Error('PDF non trouvé ou erreur serveur');
  
      const blob = await response.blob();
      const pdfUrl = window.URL.createObjectURL(blob);
      
      // Créer le modal directement dans le DOM
      createPdfModal(pdfUrl, devisId);
      
     // setMessage('✅ PDF chargé pour visualisation');
    } catch (err) {
      console.error(err);
      setMessage('❌ Erreur chargement PDF');
    } finally {
      setIsLoading(false);
    }
  };

  const createPdfModal = (pdfUrl: string, devisId: string) => {
    // Créer l'overlay
    const overlay = document.createElement('div');
    overlay.id = 'pdf-modal-overlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.3);
      backdrop-filter: blur(4px);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    `;

    // Créer le modal
    const modal = document.createElement('div');
    modal.style.cssText = `
      background: white;
      border-radius: 12px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
      border: 2px solid #e5e7eb;
      width: 85%;
      max-width: 64rem;
      height: 75vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    `;

    // Header du modal
    const header = document.createElement('div');
    header.style.cssText = `
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-bottom: 1px solid #e5e7eb;
      background: white;
    `;

    const title = document.createElement('h3');
    title.textContent = `📄 Devis #${devisId}`;
    title.style.cssText = `
      font-size: 1.125rem;
      font-weight: 600;
      color: #1f2937;
      margin: 0;
    `;

    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = 'display: flex; gap: 0.5rem;';

    // Bouton télécharger
    const downloadBtn = document.createElement('button');
    downloadBtn.textContent = '📥 Télécharger';
    downloadBtn.style.cssText = `
      background: #2563eb;
      color: white;
      padding: 0.25rem 0.75rem;
      border-radius: 0.25rem;
      border: none;
      font-size: 0.875rem;
      cursor: pointer;
      transition: background-color 0.2s;
    `;
    downloadBtn.onmouseover = () => downloadBtn.style.background = '#1d4ed8';
    downloadBtn.onmouseout = () => downloadBtn.style.background = '#2563eb';
    downloadBtn.onclick = () => {
      const a = document.createElement('a');
      a.href = pdfUrl;
      a.download = `devis_${devisId}.pdf`;
      a.click();
    };

    // Bouton fermer
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '✕ Fermer';
    closeBtn.style.cssText = `
      background: #6b7280;
      color: white;
      padding: 0.25rem 0.75rem;
      border-radius: 0.25rem;
      border: none;
      font-size: 0.875rem;
      cursor: pointer;
      transition: background-color 0.2s;
    `;
    closeBtn.onmouseover = () => closeBtn.style.background = '#4b5563';
    closeBtn.onmouseout = () => closeBtn.style.background = '#6b7280';

    // Fonction de fermeture
    const closeModal = () => {
      document.body.removeChild(overlay);
      window.URL.revokeObjectURL(pdfUrl);
      // Restaurer le scroll du body
      document.body.style.overflow = '';
    };

    closeBtn.onclick = closeModal;

    // Contenu du PDF
    const content = document.createElement('div');
    content.style.cssText = `
      flex: 1;
      padding: 1rem;
      overflow: hidden;
    `;

    const iframe = document.createElement('iframe');
    iframe.src = pdfUrl;
    iframe.style.cssText = `
      width: 100%;
      height: 100%;
      border: 1px solid #d1d5db;
      border-radius: 0.5rem;
    `;
    iframe.title = `Devis ${devisId}`;

    // Assembler le modal
    buttonContainer.appendChild(downloadBtn);
    buttonContainer.appendChild(closeBtn);
    header.appendChild(title);
    header.appendChild(buttonContainer);
    content.appendChild(iframe);
    modal.appendChild(header);
    modal.appendChild(content);
    overlay.appendChild(modal);

    // Fermer en cliquant sur l'overlay
    overlay.onclick = (e) => {
      if (e.target === overlay) {
        closeModal();
      }
    };

    // Empêcher le scroll du body
    document.body.style.overflow = 'hidden';

    // Ajouter au DOM
    document.body.appendChild(overlay);

    // Focus sur le modal pour l'accessibilité
    modal.focus();
  };

  // Fonction pour tester si le devis existe
  const testDevisExists = async () => {
    try {
      setDebugInfo('🔍 Test de l\'endpoint PDF...');
      
      const response = await fetch(`${API_BASE_URL}/devis/${devisId}/pdf`, {
        method: 'HEAD',
        headers: {
          'Accept': 'application/pdf',
        }
      });
      
      if (response.ok) {
        setDebugInfo(`✅ Endpoint accessible (${response.status})`);
      } else {
        const error = await response.text();
        setDebugInfo(`❌ Endpoint non accessible (${response.status}): ${error}`);
      }
    } catch (error: any) {
      setDebugInfo(`❌ Erreur test: ${error.message}`);
    }
  };

  // Cleanup au démontage du composant
  useEffect(() => {
    return () => {
      const existingModal = document.getElementById('pdf-modal-overlay');
      if (existingModal) {
        document.body.removeChild(existingModal);
        document.body.style.overflow = '';
      }
    };
  }, []);

  return (
    <div className="my-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
      <div className="flex gap-2 mb-3">
        <button
          onClick={viewDevis}
          disabled={isLoading}
          className={`
            bg-gradient-to-r from-green-600 to-green-800
            text-white px-4 py-2 rounded-lg font-medium
            shadow-md hover:shadow-lg transform hover:-translate-y-0.5
            transition-all duration-200 disabled:opacity-50
            disabled:cursor-not-allowed text-sm
          `}
        >
          {isLoading ? '⏳ Chargement...' : '👁️ Voir Devis'}
        </button>
        
        <button
          onClick={downloadDevis}
          disabled={isLoading}
          className={`
            bg-gradient-to-r from-blue-600 to-blue-800
            text-white px-4 py-2 rounded-lg font-medium
            shadow-md hover:shadow-lg transform hover:-translate-y-0.5
            transition-all duration-200 disabled:opacity-50
            disabled:cursor-not-allowed text-sm
          `}
        >
          {isLoading ? '⏳ Téléchargement...' : '📥 Télécharger PDF'}
        </button>

      </div>
      
      {message && (
        <div className={`mb-2 p-2 rounded text-sm ${
          message.includes('✅') 
            ? 'bg-green-100 text-green-800 border border-green-200' 
            : 'bg-red-100 text-red-800 border border-red-200'
        }`}>
          {message}
        </div>
      )}

      {debugInfo && (
        <div className="bg-gray-100 p-2 rounded text-xs font-mono text-gray-700 whitespace-pre-wrap border">
          <strong>Debug Info:</strong><br />
          {debugInfo}
        </div>
      )}
      
      <p className="text-xs text-gray-500 mt-2">
        💡 ID Devis: <code className="bg-gray-200 px-1 rounded">{devisId}</code>
      </p>
    </div>
  );
}