"use client";  
import { useState } from "react";  
import { useRouter } from "next/navigation";  
import { Eye, EyeOff, Mail, Lock, UserPlus, Shield, Hash } from "lucide-react";  
  
// Client API intégré  
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";  
  
interface SignupResponse {  
  access_token?: string;  
  refresh_token?: string;  
  user_id: string;  
  token_type?: string;  
  message?: string;  
}  
  
const authApi = {  
  async signup(userData: {  
    email: string;  
    password: string;  
    full_name?: string;  
    bh_reference?: string;  
  }): Promise<SignupResponse> {  
    const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {  
      method: "POST",  
      headers: {  
        "Content-Type": "application/json",  
        "Accept": "application/json",  
      },  
      body: JSON.stringify(userData),  
    });  
  
    if (!response.ok) {  
      const error = await response.json().catch(() => ({ detail: "Erreur d'inscription" }));  
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);  
    }  
  
    return response.json();  
  }  
};  
  
export default function SignUp() {  
  const router = useRouter();  
  const [email, setEmail] = useState("");  
  const [password, setPassword] = useState("");  
  const [confirmPassword, setConfirmPassword] = useState("");  
  const [firstName, setFirstName] = useState("");  
  const [lastName, setLastName] = useState("");  
  const [bhReference, setBhReference] = useState("");  
  const [showPassword, setShowPassword] = useState(false);  
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);  
  const [acceptTerms, setAcceptTerms] = useState(false);  
  const [isLoading, setIsLoading] = useState(false);  
  const [error, setError] = useState("");  
  
  const handleSubmit = async (e: React.FormEvent) => {  
    e.preventDefault();  
    setIsLoading(true);  
    setError("");  
  
    // Validation côté client  
    if (password !== confirmPassword) {  
      setError("Les mots de passe ne correspondent pas");  
      setIsLoading(false);  
      return;  
    }  
  
    if (password.length < 6) {  
      setError("Le mot de passe doit contenir au moins 6 caractères");  
      setIsLoading(false);  
      return;  
    }  
  
    if (!acceptTerms) {  
      setError("Vous devez accepter les conditions d'utilisation");  
      setIsLoading(false);  
      return;  
    }  
  
    try {  
      const fullName = `${firstName.trim()} ${lastName.trim()}`.trim();  
        
      const data = await authApi.signup({  
        email,  
        password,  
        full_name: fullName || undefined,  
        bh_reference: bhReference.trim() || undefined  
      });  
  
      // Vérifier si l'inscription nécessite une confirmation d'email  
      if (data.message && data.message.includes("Check your email")) {  
        // Rediriger vers la page de confirmation avec l'email  
        router.push(`/confirm-email?email=${encodeURIComponent(email)}`);  
      } else if (data.access_token) {  
        // Connexion directe réussie  
        localStorage.setItem("access_token", data.access_token);  
        localStorage.setItem("refresh_token", data.refresh_token!);  
        localStorage.setItem("user_id", data.user_id);  
        localStorage.setItem("token_type", data.token_type!);  
        router.push("/chat");  
      } else {  
        // Cas par défaut - rediriger vers confirmation  
        router.push(`/confirm-email?email=${encodeURIComponent(email)}`);  
      }  
    } catch (err: any) {  
      setError(err.message);  
    } finally {  
      setIsLoading(false);  
    }  
  };  
  
  return (  
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">  
      <div className="w-full max-w-sm mx-auto">  
        {/* Header avec logo */}  
        <div className="text-center mb-6">  
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-900 rounded-lg mb-3">  
            <Shield className="w-6 h-6 text-white" />  
          </div>  
          <h1 className="text-xl font-semibold text-gray-900 mb-1">BH Assurance</h1>  
          <p className="text-sm text-gray-600">Créer votre compte</p>  
        </div>  
  
        {/* Formulaire */}  
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">  
          <form onSubmit={handleSubmit} className="space-y-4">  
            {/* Affichage des erreurs */}  
            {error && (  
              <div className="p-3 rounded-md bg-red-50 border border-red-200">  
                <p className="text-red-600 text-sm font-medium">{error}</p>  
              </div>  
            )}  
  
            {/* Prénom et Nom */}  
            <div className="grid grid-cols-2 gap-3">  
              <div>  
                <label htmlFor="firstName" className="block text-sm font-medium text-gray-700 mb-1">  
                  Prénom  
                </label>  
                <input  
                  id="firstName"  
                  type="text"  
                  placeholder="Jean"  
                  value={firstName}  
                  onChange={(e) => setFirstName(e.target.value)}  
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white"  
                  required  
                  disabled={isLoading}  
                />  
              </div>  
              <div>  
                <label htmlFor="lastName" className="block text-sm font-medium text-gray-700 mb-1">  
                  Nom  
                </label>  
                <input  
                  id="lastName"  
                  type="text"  
                  placeholder="Dupont"  
                  value={lastName}  
                  onChange={(e) => setLastName(e.target.value)}  
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white"  
                  required  
                  disabled={isLoading}  
                />  
              </div>  
            </div>  
  
            {/* Champ email */}  
            <div>  
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">  
                Email  
              </label>  
              <div className="relative">  
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />  
                <input  
                  id="email"  
                  type="email"  
                  placeholder="votre@email.com"  
                  value={email}  
                  onChange={(e) => setEmail(e.target.value)}  
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white"  
                  required  
                  disabled={isLoading}  
                />  
              </div>  
            </div>  
  
            {/* Champ Référence BH */}  
            <div>  
              <label htmlFor="bhReference" className="block text-sm font-medium text-gray-700 mb-1">  
                Votre Référence BH    
              </label>  
              <div className="relative">  
                <Hash className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />  
                <input  
                  id="bhReference"  
                  type="text"  
                  placeholder="123456"  
                  value={bhReference}  
                  onChange={(e) => setBhReference(e.target.value)}  
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white"  
                  disabled={isLoading}  
                />  
              </div>  
            </div>  
  
            {/* Champ mot de passe */}  
            <div>  
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">  
                Mot de passe  
              </label>  
              <div className="relative">  
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />  
                <input  
                  id="password"  
                  type={showPassword ? "text" : "password"}  
                  placeholder="••••••••"  
                  value={password}  
                  onChange={(e) => setPassword(e.target.value)}  
                  className="w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white"  
                  required  
                  disabled={isLoading}  
                />  
                <button  
                  type="button"  
                  onClick={() => setShowPassword(!showPassword)}  
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-200 focus:outline-none focus:text-gray-600"  
                  disabled={isLoading}  
                >  
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}  
                </button>  
              </div>  
            </div>  
  
            {/* Champ confirmation mot de passe */}  
            <div>  
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-1">  
                Confirmer le mot de passe  
              </label>  
              <div className="relative">  
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />  
                <input  
                  id="confirmPassword"  
                  type={showConfirmPassword ? "text" : "password"}  
                  placeholder="••••••••"  
                  value={confirmPassword}  
                  onChange={(e) => setConfirmPassword(e.target.value)}  
                  className={`w-full pl-10 pr-10 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all duration-200 text-gray-900 font-medium placeholder:text-gray-400 placeholder:font-normal bg-white ${  
                    confirmPassword && password !== confirmPassword   
                      ? 'border-red-300 bg-red-50'   
                      : 'border-gray-300'  
                  }`}  
                  required  
                  disabled={isLoading}  
                />  
                <button  
                  type="button"  
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}  
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-200 focus:outline-none focus:text-gray-600"  
                  disabled={isLoading}  
                >  
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}  
                </button>  
              </div>  
              {confirmPassword && password !== confirmPassword && (  
                <p className="text-red-500 text-xs mt-1 font-medium">Les mots de passe ne correspondent pas</p>  
              )}  
            </div>  
  
            {/* Conditions d'utilisation */}  
            <div className="flex items-start space-x-2">  
              <div className="flex items-center h-5">  
                <input  
                  id="acceptTerms"  
                  type="checkbox"  
                  checked={acceptTerms}  
                  onChange={(e) => setAcceptTerms(e.target.checked)}  
                  className="w-3 h-3 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"  
                  required  
                  disabled={isLoading}  
                />  
              </div>  
              <label htmlFor="acceptTerms" className="text-xs text-gray-700 leading-4">  
                J'accepte les{" "}  
                <a href="#" className="text-blue-600 hover:text-blue-700 underline font-medium">  
                  conditions d'utilisation  
                </a>{" "}  
                et la{" "}  
                <a href="#" className="text-blue-600 hover:text-blue-700 underline font-medium">  
                  politique de confidentialité  
                </a>  
              </label>  
            </div>  
  
            {/* Bouton d'inscription */}  
            <button  
              type="submit"  
              disabled={isLoading || !email || !password || !confirmPassword || !acceptTerms || password !== confirmPassword}  
              className="w-full bg-blue-900 hover:bg-blue-800 text-white py-2.5 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"  
            >  
              {isLoading ? (  
                <>  
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>  
                  <span>Création...</span>  
                </>  
              ) : (  
                <>  
                  <span>Créer mon compte</span>  
                  <UserPlus className="w-4 h-4" />  
                </>  
              )}  
            </button>  
          </form>  
  
          {/* Divider */}  
          <div className="relative my-4">  
            <div className="absolute inset-0 flex items-center">  
              <div className="w-full border-t border-gray-300"></div>  
            </div>  
            <div className="relative flex justify-center text-xs">  
              <span className="px-2 bg-white text-gray-500">ou</span>  
            </div>  
          </div>  
  
          {/* Connexion SSO */}  
          <div>  
            <button   
              type="button"  
              className="w-full border border-gray-300 hover:border-gray-400 bg-white text-gray-700 py-2.5 px-4 rounded-lg font-medium transition-all duration-200 flex items-center justify-center space-x-2"  
              disabled={isLoading}  
            >  
              <div className="w-4 h-4 bg-red-500 rounded"></div>  
              <span>S'inscrire avec Gmail</span>  
            </button>  
          </div>  
  
          {/* Lien connexion */}  
          <p className="text-center text-gray-600 mt-4 text-xs">  
            Déjà un compte ?{" "}  
            <a href="/" className="text-blue-600 hover:text-blue-700 transition-colors duration-200 font-medium">  
              Se connecter  
            </a>  
          </p>  
        </div>  
  
        {/* Footer */}  
        <div className="text-center mt-4 text-xs text-gray-500">  
          <p>© 2024 BH Assurance</p>  
          <div className="mt-1 space-x-3">  
          <a href="#" className="hover:text-gray-700 transition-colors duration-200">Support</a>  
            <a href="#" className="hover:text-gray-700 transition-colors duration-200">Confidentialité</a>  
          </div>  
        </div>  
      </div>  
    </div>  
  );  
}