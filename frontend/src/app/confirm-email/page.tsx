"use client";  
import { useState, useEffect, Suspense } from "react";  
import { useRouter, useSearchParams } from "next/navigation";  
import { MailCheck, ArrowLeft, Shield } from "lucide-react";  
import Link from "next/link";  
  
function ConfirmEmailContent() {  
  const router = useRouter();  
  const searchParams = useSearchParams();  
  const email = searchParams.get('email') || '';  
  
  return (  
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">  
      <div className="w-full max-w-md mx-auto">  
        <div className="text-center">  
          {/* Logo */}  
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-900 rounded-lg mb-6">  
            <Shield className="w-6 h-6 text-white" />  
          </div>  
  
          {/* Icône de confirmation */}  
          <div className="bg-green-50 rounded-full p-4 mb-6 inline-flex">  
            <MailCheck className="h-12 w-12 text-green-500" />  
          </div>  
  
          <h1 className="text-3xl font-semibold text-gray-900 mb-4">  
            Vérifiez votre email  
          </h1>  
  
          <p className="text-gray-600 mb-2">  
            Nous avons envoyé un lien de confirmation à :  
          </p>  
  
          <p className="text-lg font-medium mb-6 text-blue-900">  
            {email || 'votre adresse email'}  
          </p>  
  
          <div className="bg-green-50 border border-green-100 rounded-lg p-4 mb-8">  
            <p className="text-sm text-green-800">  
              Cliquez sur le lien dans l'email pour activer votre compte.   
              Si vous ne voyez pas l'email, vérifiez votre dossier spam.  
            </p>  
          </div>  
  
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">  
            <Link  
              href="/"  
              className="flex h-11 items-center justify-center px-6 text-center rounded-lg bg-blue-900 text-white hover:bg-blue-800 transition-colors"  
            >  
              Aller à la connexion  
            </Link>  
          </div>  
  
          {/* Instructions supplémentaires */}  
          <div className="mt-8 text-sm text-gray-500">  
            <p className="mb-2">Vous n'avez pas reçu l'email ?</p>  
            <button   
              onClick={() => {  
                // TODO: Implémenter la logique de renvoi d'email  
                alert("Fonctionnalité de renvoi à implémenter");  
              }}  
              className="text-blue-600 hover:text-blue-700 underline"  
            >  
              Renvoyer l'email de confirmation  
            </button>  
          </div>  
        </div>  
  
        {/* Footer */}  
        <div className="text-center mt-8 text-xs text-gray-500">  
          <p>© 2024 BH Assurance</p>  
          <div className="mt-1 space-x-3">  
            <a href="#" className="hover:text-gray-700 transition-colors">Support</a>  
            <a href="#" className="hover:text-gray-700 transition-colors">Confidentialité</a>  
          </div>  
        </div>  
      </div>  
    </div>  
  );  
}  
  
export default function ConfirmEmail() {  
  return (  
    <Suspense fallback={  
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">  
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-900"></div>  
      </div>  
    }>  
      <ConfirmEmailContent />  
    </Suspense>  
  );  
}