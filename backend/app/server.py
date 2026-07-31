from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pathlib
from typing import List, Dict, Any

from app.auth import router as auth_router, jwt, models
from app.config import settings
from app.graph.graph import app as graph_app
from app.services.ingestion import ingest_text, ingest_file
import json
import shutil
import tempfile
import os

app = FastAPI(title="Advanced RAG API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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

STEP_LABELS = {
    "retrieve": "Retrieving documents...",
    "grade_documents": "Grading relevance...",
    "generate": "Generating answer...",
    "rewrite_query": "Rewriting query, retrying...",
    "hallucination_check": "Checking answer...",
    "handle_retrieval_error": "Document store unavailable...",
}

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def _stream_chat(question: str, thread_id: str):
    """
    Streams step-progress events as the graph executes, then a final `done`
    event with the same {answer, steps} payload the old single-shot /chat
    response used to return. The verification pipeline (hallucination_check,
    retry loop) is unchanged - this only reports progress through it, it
    doesn't stream the answer text itself, since that can't be shown before
    it's verified anyway.

    Any exception here happens after SSE headers are already committed (200
    OK), so it can't become an HTTPException - it's reported as an `error`
    event instead.
    """
    inputs = {"question": question, "retry_count": 0}
    config = {"configurable": {"thread_id": thread_id}}

    final_answer = None
    final_steps = []
    try:
        for update in graph_app.stream(inputs, config=config, stream_mode="updates"):
            for node_name, node_output in update.items():
                final_steps = node_output.get("steps", final_steps)
                if node_output.get("generation") is not None:
                    final_answer = node_output["generation"]
                label = STEP_LABELS.get(node_name, node_name)
                yield _sse("step", {"node": node_name, "label": label})
        yield _sse("done", {"answer": final_answer, "steps": final_steps})
    except Exception as e:
        import traceback
        traceback_str = "".join(traceback.format_tb(e.__traceback__))
        print(f"Error in chat stream: {e}")
        print(traceback_str)
        yield _sse("error", {"detail": str(e)})

@app.get("/")
def read_root():
    return {"message": "Advanced RAG API is running"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, current_user: models.User = Depends(jwt.get_current_user)):
    """
    Protected Chat Endpoint. Only authenticated users can access.
    Streams step-progress via Server-Sent Events, ending with a `done` event
    carrying {answer, steps} - see _stream_chat for the event contract.
    """
    return StreamingResponse(
        _stream_chat(request.question, request.thread_id),
        media_type="text/event-stream",
    )

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
