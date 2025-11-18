import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.supabase import DBConnection
from services.redis import redis_service
from routers import auth, conversations, chat
from core.config import config

# Initialisation de la DB
db = DBConnection()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await db.initialize()
        await redis_service.initialize()
        # Initialiser tous les modules avec l'instance DB partagée
        conversations.initialize(db)
        chat.initialize(db)
        print("✅ Services initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    try:
        if redis_service.client:
            await redis_service.client.close()
        print("✅ Services cleaned up successfully")
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")


# Création de l'application FastAPI
app = FastAPI(
    title="Chatbot RAG API",
    description="API pour chatbot avec RAG basé sur l'architecture Suna",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers avec préfixes
app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


# Routes de test
@app.get("/")
async def root():
    return {"message": "Chatbot RAG API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chatbot-rag-api"}

@app.get("/api/health")
async def api_health_check():
    return {"status": "healthy", "api_version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
