import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

from app.services.ingestion import ingest_file

def test_ingest():
    # Create a dummy file
    filename = "test_ingest.txt"
    with open(filename, "w", encoding='utf-8') as f:
        f.write("This is a test document for ingestion.")
        
    try:
        count = ingest_file(filename)
        print(f"Successfully ingested {count} chunks.")
    except Exception as e:
        print(f"Error ingest_file: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_ingest()
