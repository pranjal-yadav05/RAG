from fastapi import FastAPI, UploadFile, File
from pdf_utils import extract_pages_with_positions, chunk_words
from pydantic import BaseModel
from openai import OpenAI
from rag import create_embeddings, save_embeddings, load_embeddings, answer_from_chunks
import hashlib
import os
from fastapi.staticfiles import StaticFiles



os.makedirs("pdf_store", exist_ok=True)
os.makedirs("images", exist_ok=True)

app = FastAPI()

chat_history = {}

app.mount("/images", StaticFiles(directory="images"), name="images")

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

    file_path = f"pdf_store/{file_hash}.pdf"
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    cached = load_embeddings(file_hash)
    if cached:
        return {
            "message": "Loaded from cache",
            "file_hash": file_hash,
            "chunks": len(cached["chunks"])
        }
    
    file.file.seek(0)

    pages = extract_pages_with_positions(file.file)
    chunks = chunk_words(pages)
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
    answer, highlights, images = answer_from_chunks(req.query, embeddings, req.file_hash, history=history)
    history.append({ "role": "assistant", "content": answer })

    recent_history = history[-5:]
    return {
        "query": req.query,
        "answer": answer,
        "highlights": highlights,
        "history": recent_history,
        "images": images
    }
