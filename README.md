# 📄 RAG PDF (Work in Progress)

This is a learning project where I’m building a **Retrieval-Augmented Generation (RAG) system from scratch**, step by step, instead of using high-level frameworks.

The goal is to understand what actually happens behind “chat with your PDF” systems—how documents are processed, embedded, retrieved, and used by LLMs.

Right now, the project has evolved from a simple Streamlit prototype into a **FastAPI-based backend system**, while the **frontend is still in progress and being actively explored**.

For now, the backend is fully usable as a standalone service, and there is also a separate Streamlit demo available for interactive experimentation.

---

## 🧠 What I’m Trying to Learn

* How embeddings represent meaning in text
* How chunking affects retrieval quality
* How similarity search actually works in practice
* How RAG pipelines are structured in real systems
* How backend architecture changes when moving from prototype → API design
* Where simple retrieval systems break and why

---

## 🧱 Current Architecture

The project is split into a **backend service + experimental frontend demo**:

```text
RAG_PDF/
│
├── backend/
│   ├── main.py              # FastAPI app (upload + ask endpoints)
│   ├── rag.py               # embeddings, retrieval, LLM logic
│   ├── pdf_utils.py         # PDF extraction + chunking
│
├── frontend/
│   └── streamlit_demo.py   # standalone Streamlit UI (NOT connected to backend)
│
├── embeddings_store/       # cached embeddings per PDF
├── .env
├── requirements.txt
```

---

## ⚙️ Current Features

### 📄 PDF Processing

* Upload a PDF via FastAPI (`/upload-pdf`)
* Extract text using `pdfplumber`
* Split into overlapping chunks

### 🧠 Embeddings & Storage

* Generate embeddings using OpenRouter (`text-embedding-3-small`)
* Cache embeddings locally using MD5 hash of the file
* Avoid recomputation on re-upload

### 🔍 Retrieval System

* Embed user query
* Compute cosine similarity with stored chunks
* Retrieve most relevant chunks

### 💬 Question Answering

* `/ask` endpoint accepts:

  * `session_id`
  * `file_hash`
  * `query`
* Uses retrieved context + LLM (`gpt-4o-mini`)
* Returns answer + chat history

### 🧾 Chat Memory

* Maintains in-memory session-based history
* Keeps last few messages for context
* Not persisted across restarts

---

## 🚀 Backend Service (Main System)

The **FastAPI backend is the primary system** in this project.

It is fully usable on its own:

### 📤 Upload PDF

```
POST /upload-pdf
```

Uploads a PDF, processes it, and stores embeddings.

### 💬 Ask Question

```
POST /ask
```

Request:

```json
{
  "session_id": "user1",
  "file_hash": "abc123",
  "query": "What is this document about?"
}
```

Response:

* Answer generated using retrieved context + LLM
* Recent chat history

👉 This backend can be used independently of any UI.

---

## 🧪 Frontend (Streamlit Demo - Experimental)

Located at:

```
frontend/streamlit_demo.py
```

This is:

* A **standalone interactive UI**
* Built for quick experimentation and understanding the RAG flow
* Based on the earlier version of the project
* **NOT connected to the FastAPI backend**

It directly runs the RAG pipeline inside Streamlit itself (upload → embed → retrieve → answer), so it serves as a **visual learning tool rather than the production flow**.

👉 Think of it as:

> “A sandbox version of the system before API separation”

---

## 🧱 How It Works (Simplified Flow)

### 1. PDF → Text

* Extracts all pages into raw text

### 2. Text → Chunks

* Fixed-size chunking (1000 chars + overlap)
* Simple, not semantic

### 3. Chunks → Embeddings

* Each chunk is converted into a vector
* Stored locally using file hash

### 4. Query → Retrieval

* User query is embedded
* Cosine similarity is computed
* Top relevant chunks are selected

### 5. Context → LLM

* Retrieved chunks + chat history
* Sent to GPT-4o-mini
* Response returned to user

---

## 💾 Embedding Cache System

Each uploaded PDF is hashed:

```
embeddings_store/<file_hash>.pkl
```

Stored data:

```python
{
  "chunks": [...],
  "embeddings": [...]
}
```

This avoids recomputing embeddings for the same document.

---

## ⚠️ Limitations

* Only supports one PDF per request flow (via file_hash tracking)
* Retrieval is basic cosine similarity only
* No reranking or hybrid search
* Chunking is purely character-based
* Chat memory is in-memory only (not persistent)
* No database or vector store yet
* Scaling is not handled (single-process design)

---

## 🔧 Setup

```bash
pip install fastapi uvicorn pdfplumber openai numpy python-dotenv python-multipart streamlit
```

Create `.env`:

```env
OPENROUTER_API_KEY=your_key_here
```

Run backend:

```bash
uvicorn backend.main:app --reload
```

Run Streamlit demo (optional):

```bash
streamlit run frontend/streamlit_demo.py
```

---

## 📌 Why I Built This

I wanted to understand RAG systems by building one manually instead of relying on frameworks like LangChain or LlamaIndex.

This project is my attempt to break down:

* how documents become embeddings
* how retrieval actually works
* how context affects LLM answers
* how backend architecture evolves from prototype → API design

---

## 🔮 Next Steps (Ideas I’m Exploring)

* Add semantic or sentence-based chunking
* Improve retrieval (hybrid search / reranking)
* Persist chat history properly (Redis or DB)
* Multi-PDF support per user session
* Streaming responses (ChatGPT-style UX)
* Add vector database instead of local pickle storage

---

## 🤝 Notes

This is not a production system.

It’s a **learning snapshot of how I’m building understanding of RAG systems step by step**, starting from a simple Streamlit prototype and evolving into a backend-first architecture with a separate experimental UI layer.

