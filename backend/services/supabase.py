from typing import Optional  
from supabase import create_async_client, AsyncClient  
from core.config import config  
import threading  
  
class DBConnection:  
    """Thread-safe singleton database connection manager using Supabase."""  
      
    _instance: Optional['DBConnection'] = None  
    _lock = threading.Lock()  
  
    def __new__(cls):  
        if cls._instance is None:  
            with cls._lock:  
                if cls._instance is None:  
                    cls._instance = super().__new__(cls)  
                    cls._instance._initialized = False  
                    cls._instance._client = None  
        return cls._instance  
  
    async def initialize(self):  
        """Initialize the database connection."""  
        if self._initialized:  
            return  
                  
        try:  
            supabase_url = config.SUPABASE_URL  
            supabase_key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY  
              
            if not supabase_url or not supabase_key:  
                raise RuntimeError("SUPABASE_URL and key must be set.")  
  
            self._client = await create_async_client(supabase_url, supabase_key)  
            self._initialized = True  
              
        except Exception as e:  
            raise RuntimeError(f"Failed to initialize database: {str(e)}")  
  
    @property  
    async def client(self) -> AsyncClient:  
        """Get the Supabase client instance."""  
        if not self._initialized:  
            await self.initialize()  
        return self._client