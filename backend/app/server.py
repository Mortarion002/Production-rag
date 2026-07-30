from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pathlib
from typing import List, Dict, Any

from app.auth import router as auth_router, jwt, models
from app.graph.graph import app as graph_app
from app.services.ingestion import ingest_text, ingest_file
import shutil
import tempfile
import os

app = FastAPI(title="Advanced RAG API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)

class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default"

class IngestRequest(BaseModel):
    text: str
    filename: str

@app.get("/")
def read_root():
    return {"message": "Advanced RAG API is running"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: models.User = Depends(jwt.get_current_user)):
    """
    Protected Chat Endpoint. Only authenticated users can access.
    """
    inputs = {"question": request.question, "retry_count": 0}
    config = {"configurable": {"thread_id": request.thread_id}}

    # Synchronous invoke for now; streaming is tracked separately in PLAN.md.
    try:
        final_state = graph_app.invoke(inputs, config=config)
    except Exception as e:
        import traceback
        traceback_str = "".join(traceback.format_tb(e.__traceback__))
        print(f"Error in chat endpoint: {e}")
        print(traceback_str)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)} Traceback: {traceback_str}")

    return {
        "answer": final_state.get("generation"),
        "steps": final_state.get("steps", []),
    }

@app.post("/ingest")
async def ingest_endpoint(request: IngestRequest, current_admin: models.User = Depends(jwt.get_current_admin_user)):
    """
    Protected Ingestion Endpoint. Only ADMIN users can access.
    """
    try:
        count = ingest_text(request.text, metadata={"filename": request.filename})
        return {"message": f"Successfully ingested {count} chunks", "filename": request.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/file")
async def ingest_file_endpoint(file: UploadFile = File(...), current_admin: models.User = Depends(jwt.get_current_admin_user)):
    """
    Protected File Ingestion Endpoint. Only ADMIN users can access.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    try:
        # Create a temporary file to save the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=pathlib.Path(file.filename).suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
            
        try:
            # Ingest the file
            count = ingest_file(tmp_path, file.filename)
            return {"message": f"Successfully ingested {count} chunks", "filename": file.filename}
        finally:
            # Clean up the temporary file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
    except Exception as e:
        import traceback
        traceback_str = "".join(traceback.format_tb(e.__traceback__))
        print(f"Error processing file upload: {e}")
        print(traceback_str)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)} Traceback: {traceback_str}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
