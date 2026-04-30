"""
main.py
=======
FastAPI application.

Key invariants
--------------
* Every on-disk resource is scoped to (user_id, file_id) via storage_paths.
* file_id is a UUID generated once on upload and never reused.
* content_hash is used only for dedup (reuse embeddings); it is NOT a key.
* Sessions belong to a file; deleting a file cascades to its sessions + disk.
"""

import hashlib
import os

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth import create_access_token, decode_token, hash_password, verify_password
from db import (
    add_message,
    create_session,
    delete_session,
    delete_sessions_for_file,
    get_session,
    get_sessions,
    get_sessions_for_file,
    rename_session,
)
from db_files import (
    create_file,
    delete_file,
    find_duplicate,
    get_file,
    get_user_files,
)
from db_users import users
from pdf_utils import chunk_words, extract_pages_with_positions
from rag import answer_from_chunks, create_embeddings, load_embeddings, save_embeddings
from storage_paths import paths as file_paths

# ── startup ───────────────────────────────────────────────────────────────────

# Create top-level static dirs (subdirs are created per-file via makedirs())
os.makedirs("pdf_store",        exist_ok=True)
os.makedirs("embeddings_store", exist_ok=True)
os.makedirs("images",           exist_ok=True)

app = FastAPI()

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not origins:
    origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve per-file images at /images/<user_id>/<file_id>/page_N.png
app.mount("/images", StaticFiles(directory="images"), name="images")

oauth2_scheme = HTTPBearer()


# ── auth helpers ──────────────────────────────────────────────────────────────

def get_current_user(token=Depends(oauth2_scheme)) -> str:
    payload = decode_token(token.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["user_id"]


def content_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ── auth endpoints ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str


@app.post("/signup")
async def signup(req: SignupRequest):
    if await users.find_one({"email": req.email}):
        raise HTTPException(status_code=400, detail="User already exists")

    result = await users.insert_one({
        "email":    req.email,
        "password": hash_password(req.password),
    })
    token = create_access_token({"user_id": str(result.inserted_id)})
    return {"access_token": token, "token_type": "bearer"}


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
async def login(req: LoginRequest):
    user = await users.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": str(user["_id"])})
    return {"access_token": token, "token_type": "bearer"}


# ── file management ───────────────────────────────────────────────────────────

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """
    Upload a PDF and prepare embeddings.

    Flow
    ----
    1. Hash the bytes (SHA-256).
    2. If this user already has a file with the same hash, reuse its
       embeddings — but still create a fresh file record so the user
       can manage uploads independently.
    3. Save PDF to disk at the path owned by the new file_id.
    4. Generate (or copy) embeddings, then return file_id + session_id.
    """
    file_bytes   = await file.read()
    c_hash       = content_hash(file_bytes)

    # 1. Create file record (new UUID every upload)
    file_id = await create_file(
        user_id=user_id,
        file_name=file.filename,
        content_hash=c_hash,
    )

    p = file_paths(user_id, file_id)
    p.makedirs()

    # 2. Save PDF
    with open(p.pdf, "wb") as f:
        f.write(file_bytes)

    # 3. Create a default session for this file
    session_id = await create_session(user_id=user_id, file_id=file_id)

    # 4. Check if embeddings can be reused from a previous identical upload
    duplicate = await find_duplicate(user_id, c_hash)
    if duplicate and duplicate["file_id"] != file_id:
        cached = load_embeddings(user_id, duplicate["file_id"])
        if cached:
            # Copy embeddings under the new file_id so paths stay consistent
            save_embeddings(user_id, file_id, cached)
            return {
                "message":    "Loaded from cache (duplicate content)",
                "session_id": session_id,
                "file_id":    file_id,
                "chunks":     len(cached["embeddings"]),
            }

    # 5. Process fresh
    import io
    pages      = extract_pages_with_positions(io.BytesIO(file_bytes))
    chunks     = chunk_words(pages)
    embeddings = create_embeddings(chunks)

    save_embeddings(user_id, file_id, {"chunks": chunks, "embeddings": embeddings})

    return {
        "message":    "Processed and saved",
        "session_id": session_id,
        "file_id":    file_id,
        "chunks":     len(chunks),
    }


@app.get("/files")
async def list_files(user_id: str = Depends(get_current_user)):
    return await get_user_files(user_id)


@app.get("/files/{file_id}")
async def get_file_detail(file_id: str, user_id: str = Depends(get_current_user)):
    file = await get_file(file_id)
    if not file or file["user_id"] != user_id:
        raise HTTPException(status_code=404)
    return file


@app.delete("/files/{file_id}")
async def delete_file_endpoint(file_id: str, user_id: str = Depends(get_current_user)):
    """
    Delete a file and everything associated with it:
    DB record → sessions → PDF → embeddings → images.
    """
    file = await get_file(file_id)
    if not file:
        raise HTTPException(status_code=404)
    if file["user_id"] != user_id:
        raise HTTPException(status_code=403)

    # 1. DB
    await delete_file(file_id)
    await delete_sessions_for_file(file_id)

    # 2. Disk (single call removes all dirs for this file)
    file_paths(user_id, file_id).delete_all()

    return {"message": "File and all associated data deleted"}


# ── session management ────────────────────────────────────────────────────────

@app.post("/files/{file_id}/sessions")
async def create_session_endpoint(file_id: str, user_id: str = Depends(get_current_user)):
    """Start a new chat session on an existing file."""
    file = await get_file(file_id)
    if not file or file["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="File not found")

    data = load_embeddings(user_id, file_id)
    if not data:
        raise HTTPException(status_code=400, detail="Embeddings not ready for this file")

    session_id = await create_session(user_id=user_id, file_id=file_id)
    return {"session_id": session_id, "file_id": file_id}


@app.get("/files/{file_id}/sessions")
async def list_sessions_for_file(file_id: str, user_id: str = Depends(get_current_user)):
    file = await get_file(file_id)
    if not file or file["user_id"] != user_id:
        raise HTTPException(status_code=404)
    return await get_sessions_for_file(file_id)


@app.get("/sessions")
async def list_all_sessions(user_id: str = Depends(get_current_user)):
    return await get_sessions(user_id)


@app.get("/sessions/{session_id}")
async def fetch_session(session_id: str, user_id: str = Depends(get_current_user)):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404)
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403)
    session.pop("_id", None)
    return session


@app.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str, user_id: str = Depends(get_current_user)):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404)
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403)
    await delete_session(session_id)
    return {"message": "Session deleted"}


class RenameSessionRequest(BaseModel):
    title: str


@app.patch("/sessions/{session_id}")
async def rename_session_endpoint(
    session_id: str,
    req: RenameSessionRequest,
    user_id: str = Depends(get_current_user),
):
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404)
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403)
    await rename_session(session_id, req.title)
    return {"message": "Session renamed"}


# ── Q&A ───────────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    query: str


@app.post("/sessions/{session_id}/ask")
async def ask(
    session_id: str,
    req: QuestionRequest,
    user_id: str = Depends(get_current_user),
):
    # Validate session ownership
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized session access")

    file_id = session["file_id"]

    # Validate file ownership
    file = await get_file(file_id)
    if not file or file["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="File not found")

    # Load embeddings — always keyed by (user_id, file_id)
    data = load_embeddings(user_id, file_id)
    if not data:
        raise HTTPException(status_code=400, detail="Embeddings not found. Re-upload the PDF.")

    history = session.get("messages", [])

    answer, highlights, images = answer_from_chunks(
        query=req.query,
        chunk_embeddings=data["embeddings"],
        user_id=user_id,
        file_id=file_id,
        history=history[-6:],
    )

    await add_message(session_id, {"role": "user",      "content": req.query})
    await add_message(session_id, {"role": "assistant", "content": answer,
                                   "highlights": highlights, "images": images})

    return {
        "query":      req.query,
        "answer":     answer,
        "highlights": highlights,
        "images":     images,
        "session_id": session_id,
    }