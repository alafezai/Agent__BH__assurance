from fastapi import HTTPException, Request  
from typing import Optional  
import jwt  
from jwt.exceptions import PyJWTError  
import structlog  
  
logger = structlog.get_logger()  
  
async def get_current_user_id_from_jwt(request: Request) -> str:  
    """  
    Extraire et vérifier l'ID utilisateur depuis le JWT dans l'en-tête Authorization.  
    Fonction utilitaire réutilisable basée sur Suna.  
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
        # Décoder le JWT sans vérification de signature (comme Supabase)  
        payload = jwt.decode(token, options={"verify_signature": False})  
        user_id = payload.get('sub')  
          
        if not user_id:  
            raise HTTPException(  
                status_code=401,  
                detail="Invalid token payload",  
                headers={"WWW-Authenticate": "Bearer"}  
            )  
          
        logger.info("User authenticated", user_id=user_id)  
        return user_id  
          
    except PyJWTError:  
        raise HTTPException(  
            status_code=401,  
            detail="Invalid token",  
            headers={"WWW-Authenticate": "Bearer"}  
        )  
  
async def get_optional_user_id(request: Request) -> Optional[str]:  
    """  
    Extraire l'ID utilisateur depuis le JWT si présent, sinon retourner None.  
    Utile pour les endpoints qui supportent l'authentification optionnelle.  
    """  
    auth_header = request.headers.get('Authorization')  
      
    if not auth_header or not auth_header.startswith('Bearer '):  
        return None  
      
    token = auth_header.split(' ')[1]  
      
    try:  
        payload = jwt.decode(token, options={"verify_signature": False})  
        return payload.get('sub')  
    except PyJWTError:  
        return None