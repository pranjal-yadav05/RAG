from fastapi import FastAPI, UploadFile, File
from pdf_utils import extract_text_from_pdf, chunk_text
from pydantic import BaseModel
from openai import OpenAI
from rag import create_embeddings, save_embeddings, load_embeddings, answer_from_chunks
import hashlib

app = FastAPI()

chat_history = {}

class QuestionRequest(BaseModel):
    session_id: str
    file_hash: str
    query: str

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

@app.post("/upload-pdf")
def upload_pdf(file: UploadFile = File(...)):
    file_bytes = file.file.read()

    file_hash = get_file_hash(file_bytes)

    cached = load_embeddings(file_hash)
    if cached:
        return {
            "message": "Loaded from cache",
            "file_hash": file_hash,
            "chunks": len(cached["chunks"])
        }
    
    file.file.seek(0)

    text = extract_text_from_pdf(file.file)
    chunks = chunk_text(text)
    embeddings = create_embeddings(chunks)

    save_embeddings(file_hash, {
        "chunks": chunks,
        "embeddings": embeddings
    })

    return {
        "message": "Processed and saved",
        "file_hash": file_hash,
        "chunks": len(chunks)
    }

@app.post("/ask")
def ask(req: QuestionRequest):
    data = load_embeddings(req.file_hash)
    if not data:
        return { "error": "PDF not found. Upload first." }
    
    chunks = data["chunks"]
    embeddings = data["embeddings"]

    if req.session_id not in chat_history:
        chat_history[req.session_id] = []

    history = chat_history[req.session_id]
    history.append({ "role": "user", "content": req.query })

    # Answer with RAG
    answer = answer_from_chunks(req.query, embeddings)
    history.append({ "role": "assistant", "content": answer })

    recent_history = history[-5:]
    return {
        "query": req.query,
        "history": recent_history
    }




