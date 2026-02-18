import sys
import os

# Add parent dir to path so we can import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from app.auth.models import Base  # This imports the 'users' table definition

def init_db():
    print("Connecting to database and creating tables...")
    try:
        # This looks at all models that inherit from 'Base' and creates them
        Base.metadata.create_all(bind=engine)
        print("Success! Tables created in 'rag_metadata'.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_db()