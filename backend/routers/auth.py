from fastapi import APIRouter, HTTPException, Depends, Request  
from fastapi.security import HTTPBearer  
from pydantic import BaseModel  
from typing import Optional  
import jwt  
from jwt.exceptions import PyJWTError  
from services.supabase import DBConnection  
from core.config import config  
import structlog  
  
router = APIRouter(prefix="/auth", tags=["authentication"])  
security = HTTPBearer()  
  
# Configuration du logger  
logger = structlog.get_logger()  
  
class UserLogin(BaseModel):  
    email: str  
    password: str  
  
class UserCreate(BaseModel):  
    email: str  
    password: str  
    full_name: Optional[str] = None  
  
class LoginResponse(BaseModel):  
    access_token: str  
    token_type: str = "bearer"  
    user_id: str  
    refresh_token: str  
  
class UserResponse(BaseModel):  
    user_id: str  
    email: str  
    full_name: Optional[str] = None  
    created_at: str  
  
@router.post("/login", response_model=LoginResponse)  
async def login(credentials: UserLogin):  
    """Endpoint de connexion avec Supabase Auth"""  
    try:  
        # Initialiser la connexion Supabase  
        db = DBConnection()  
        await db.initialize()  
        client = await db.client  
          
        # Authentification avec Supabase Auth  
        auth_response = await client.auth.sign_in_with_password({  
            "email": credentials.email,  
            "password": credentials.password  
        })  
          
        if not auth_response.user:  
            raise HTTPException(  
                status_code=401,   
                detail="Invalid email or password"  
            )  
          
        user = auth_response.user  
        session = auth_response.session  
          
        logger.info(  
            "User logged in successfully",  
            user_id=user.id,  
            email=user.email  
        )  
          
        return LoginResponse(  
            access_token=session.access_token,  
            token_type="bearer",  
            user_id=user.id,  
            refresh_token=session.refresh_token  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Login error: {str(e)}")  
        raise HTTPException(  
            status_code=401,   
            detail="Authentication failed"  
        )  
  
@router.post("/signup", response_model=LoginResponse)  
async def signup(user_data: UserCreate):  
    """Endpoint d'inscription avec Supabase Auth"""  
    try:  
        # Initialiser la connexion Supabase  
        db = DBConnection()  
        await db.initialize()  
        client = await db.client  
          
        # Créer l'utilisateur avec Supabase Auth  
        auth_response = await client.auth.sign_up({  
            "email": user_data.email,  
            "password": user_data.password,  
            "options": {  
                "data": {  
                    "full_name": user_data.full_name  
                }  
            }  
        })  
          
        if not auth_response.user:  
            raise HTTPException(  
                status_code=400,  
                detail="Failed to create user account"  
            )  
          
        user = auth_response.user  
        session = auth_response.session  
          
        logger.info(  
            "User registered successfully",  
            user_id=user.id,  
            email=user.email  
        )  
          
        # Si pas de session (email confirmation requise)  
        if not session:  
            raise HTTPException(  
                status_code=201,  
                detail="User created. Please check your email for confirmation."  
            )  
          
        return LoginResponse(  
            access_token=session.access_token,  
            token_type="bearer",  
            user_id=user.id,  
            refresh_token=session.refresh_token  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Signup error: {str(e)}")  
        raise HTTPException(  
            status_code=400,   
            detail="Registration failed"  
        )  
  
async def get_current_user_id_from_jwt(request: Request) -> str:  
    """  
    Extraire et vérifier l'ID utilisateur depuis le JWT dans l'en-tête Authorization.  
    Basé sur le système d'authentification de Suna.  
    """  
    auth_header = request.headers.get('Authorization')  
      
    if not auth_header or not auth_header.startswith('Bearer '):  
        raise HTTPException(  
            status_code=401,  
            detail="No valid authentication credentials found",  
            headers={"WWW-Authenticate": "Bearer"}  
        )  
      
    token = auth_header.split(' ')[1]  
      
    try:  
        # Décoder le JWT sans vérification de signature (comme Suna)  
        payload = jwt.decode(token, options={"verify_signature": False})  
        user_id = payload.get('sub')  
          
        if not user_id:  
            raise HTTPException(  
                status_code=401,  
                detail="Invalid token payload",  
                headers={"WWW-Authenticate": "Bearer"}  
            )  
          
        return user_id  
          
    except PyJWTError:  
        raise HTTPException(  
            status_code=401,  
            detail="Invalid token",  
            headers={"WWW-Authenticate": "Bearer"}  
        )  
  
@router.get("/me", response_model=UserResponse)  
async def get_current_user(request: Request):  
    """Récupérer les informations de l'utilisateur connecté"""  
    try:  
        # Extraire l'ID utilisateur depuis le JWT  
        user_id = await get_current_user_id_from_jwt(request)  
          
        # Initialiser la connexion Supabase  
        db = DBConnection()  
        await db.initialize()  
        client = await db.client  
          
        # Récupérer les informations utilisateur depuis Supabase  
        user_response = await client.auth.admin.get_user_by_id(user_id)  
          
        if not user_response.user:  
            raise HTTPException(  
                status_code=404,  
                detail="User not found"  
            )  
          
        user = user_response.user  
        user_metadata = user.user_metadata or {}  
          
        return UserResponse(  
            user_id=user.id,  
            email=user.email,  
            full_name=user_metadata.get('full_name'),  
            created_at=user.created_at  
        )  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Get current user error: {str(e)}")  
        raise HTTPException(  
            status_code=500,  
            detail="Failed to retrieve user information"  
        )  
  
@router.post("/refresh")  
async def refresh_token(request: Request):  
    """Rafraîchir le token d'accès"""  
    try:  
        body = await request.json()  
        refresh_token = body.get('refresh_token')  
          
        if not refresh_token:  
            raise HTTPException(  
                status_code=400,  
                detail="Refresh token required"  
            )  
          
        # Initialiser la connexion Supabase  
        db = DBConnection()  
        await db.initialize()  
        client = await db.client  
          
        # Rafraîchir la session  
        auth_response = await client.auth.refresh_session(refresh_token)  
          
        if not auth_response.session:  
            raise HTTPException(  
                status_code=401,  
                detail="Invalid refresh token"  
            )  
          
        session = auth_response.session  
          
        return {  
            "access_token": session.access_token,  
            "token_type": "bearer",  
            "refresh_token": session.refresh_token  
        }  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Refresh token error: {str(e)}")  
        raise HTTPException(  
            status_code=401,  
            detail="Token refresh failed"  
        )  
  
@router.post("/logout")  
async def logout(request: Request):  
    """Déconnexion de l'utilisateur"""  
    try:  
        # Extraire l'ID utilisateur depuis le JWT  
        user_id = await get_current_user_id_from_jwt(request)  
          
        # Initialiser la connexion Supabase  
        db = DBConnection()  
        await db.initialize()  
        client = await db.client  
          
        # Déconnecter l'utilisateur  
        await client.auth.sign_out()  
          
        logger.info(  
            "User logged out successfully",  
            user_id=user_id  
        )  
          
        return {"message": "Logged out successfully"}  
          
    except HTTPException:  
        raise  
    except Exception as e:  
        logger.error(f"Logout error: {str(e)}")  
        raise HTTPException(  
            status_code=500,  
            detail="Logout failed"  
        )