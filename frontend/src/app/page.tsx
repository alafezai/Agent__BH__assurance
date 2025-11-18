"use client";  
import { useState } from "react";  
import { useRouter } from "next/navigation";  
import { Eye, EyeOff, Mail, Lock, ArrowRight, Shield } from "lucide-react";  
  
// Client API intégré directement dans le composant  
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";  
  
interface LoginResponse {  
  access_token: string;  
  refresh_token: string;  
  user_id: string;  
  token_type: string;  
}  
  
const authApi = {  
  async login(credentials: { email: string; password: string }): Promise<LoginResponse> {  
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {  
      method: "POST",  
      headers: {  
        "Content-Type": "application/json",  
        "Accept": "application/json",  
      },  
      body: JSON.stringify(credentials),  
    });  
  
    if (!response.ok) {  
      const error = await response.json().catch(() => ({ detail: "Erreur de connexion" }));  
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);  
    }  
  
    return response.json();  
  }  
};  
  
export default function Login() {  
  const router = useRouter();  
  const [email, setEmail] = useState("");  
  const [password, setPassword] = useState("");  
  const [showPassword, setShowPassword] = useState(false);  
  const [isLoading, setIsLoading] = useState(false);  
  const [error, setError] = useState("");  
  
  const handleSubmit = async (e: React.FormEvent) => {  
    e.preventDefault();  
    setIsLoading(true);  
    setError("");  
  
    try {  
      const data = await authApi.login({ email, password });  
        
      // Stocker les tokens  
      localStorage.setItem("access_token", data.access_token);  
      localStorage.setItem("refresh_token", data.refresh_token);  
      localStorage.setItem("user_id", data.user_id);  
      localStorage.setItem("token_type", data.token_type);  
  
      router.push("/chat");  
    } catch (err: any) {  
      setError(err.message);  
    } finally {  
      setIsLoading(false);  
    }  
  };  
  
  return (  
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">  
      <div className="w-full max-w-sm mx-auto bg-white p-6 rounded-lg shadow">  
        <div className="text-center mb-6">  
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-900 rounded-lg mb-3">  
            <Shield className="w-6 h-6 text-white" />  
          </div>  
          <h1 className="text-xl font-semibold text-gray-900">BH Assurance</h1>  
          <p className="text-sm text-gray-600">Assistant Conseil IA</p>  
        </div>  
  
        <form className="space-y-4" onSubmit={handleSubmit}>  
          {error && (  
            <div className="p-3 rounded-md bg-red-50 border border-red-200">  
              <p className="text-red-600 text-sm font-medium">{error}</p>  
            </div>  
          )}  
  
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
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors focus:outline-none focus:text-gray-600"  
                disabled={isLoading}  
              >  
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}  
              </button>  
            </div>  
          </div>  
  
          <button  
            type="submit"  
            disabled={isLoading || !email || !password}  
            className="w-full bg-blue-900 hover:bg-blue-800 text-white py-2.5 px-4 rounded-lg flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"  
          >  
            {isLoading ? (  
              <>  
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>  
                <span>Connexion...</span>  
              </>  
            ) : (  
              <>  
                <ArrowRight className="w-4 h-4" />  
                <span>Se connecter</span>  
              </>  
            )}  
          </button>  
        </form>  
  
        <p className="text-center text-gray-600 mt-4 text-xs">  
          Première visite ?{" "}  
          <a href="/signup" className="text-blue-600 font-medium hover:text-blue-700 transition-colors">  
            Créer un compte  
          </a>  
        </p>  
      </div>  
    </div>  
  );  
}