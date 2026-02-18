from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Synchronous engine for Auth (Simpler for now, can migrate to async if needed)
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL.replace("+asyncpg", "") # quick fix for sync sqlalchemy

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
