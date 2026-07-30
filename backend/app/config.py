import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_SECRET_KEY = "your-secret-key-change-me-in-production"
DEFAULT_POSTGRES_PASSWORD = "secretpassword"

class Settings:
    # LLM
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "gpt-4o-mini") #gpt-3.5-turbo-0125
    LLM_MODEL_SMART = os.getenv("LLM_MODEL_SMART", "gpt-4o-mini")#gpt-4-turbo-preview

    # Qdrant
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "advanced_rag_v1")

    # Postgres
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)
    POSTGRES_DB = os.getenv("POSTGRES_DB", "rag_metadata")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    # Auth
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # CORS - comma-separated list of allowed origins
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

settings = Settings()

if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
    print("WARNING: SECRET_KEY is using its default placeholder value. Set SECRET_KEY in .env before deploying anywhere but local dev.")
if settings.POSTGRES_PASSWORD == DEFAULT_POSTGRES_PASSWORD:
    print("WARNING: POSTGRES_PASSWORD is using its default placeholder value. Set POSTGRES_PASSWORD in .env before deploying anywhere but local dev.")
