"use client";

import { AlertTriangle } from "lucide-react";

interface DeleteModalProps {
  showDeleteModal: boolean;
  isDeleting: boolean;
  onClose: () => void;
  onConfirmDelete: () => void;
}

export default function DeleteModal({
  showDeleteModal,
  isDeleting,
  onClose,
  onConfirmDelete
}: DeleteModalProps) {
  if (!showDeleteModal) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-6 max-w-sm w-full mx-4 shadow-xl">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-red-600" />
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Supprimer cette conversation ?
          </h3>

          <p className="text-sm text-gray-600 mb-6">
            Cette action est irréversible. Tous les messages seront perdus.
          </p>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50 font-medium"
            >
              Annuler
            </button>
            <button
              onClick={onConfirmDelete}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center justify-center gap-2 font-medium"
            >
              {isDeleting ? (
                <>
                  <div className="w-4 h-4 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                  <span>Suppression...</span>
                </>
              ) : (
                "Supprimer"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}