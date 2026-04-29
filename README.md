# 📄 RAG PDF (Work in Progress)

This is a learning project where I’m building a **Retrieval-Augmented Generation (RAG) system from scratch**, step by step, instead of using high-level frameworks.

The goal is to understand what actually happens behind “chat with your PDF” systems—how documents are processed, embedded, retrieved, and used by LLMs.

The project has now evolved into a **FastAPI-based backend system with visual grounding (highlighted PDF regions)**, while the **frontend is still in progress**.

---

## 🧠 What I’m Trying to Learn

* How embeddings represent meaning in text
* How chunking strategies impact retrieval quality
* How to map LLM answers back to exact document locations
* How similarity search behaves in real-world documents
* How RAG systems evolve from prototypes → structured APIs
* Where naive RAG pipelines fail (and how to improve them)

---

## 🧱 Current Architecture

```text
RAG_PDF/
│
├── backend/
│   ├── main.py              # FastAPI app (upload + ask endpoints)
│   ├── rag.py               # embeddings, retrieval, LLM + highlighting logic
│   ├── pdf_utils.py         # PDF parsing, layout-aware chunking
│
├── pdf_store/               # stored PDFs (by hash)
├── embeddings_store/        # cached embeddings
├── images/                  # generated highlight images
│
├── frontend/
│   └── streamlit_demo.py    # standalone experimental UI
│
├── .env
├── requirements.txt
```

---

## ⚙️ Current Features

### 📄 PDF Processing (Layout-Aware)

* Extracts **word-level data with positions** using `pdfplumber`
* Reconstructs:

  * lines → paragraphs → chunks
* Preserves layout structure instead of raw text dumping

---

### ✂️ Smart Chunking (Major Upgrade)

* Paragraph-aware chunking (not naive character splitting)
* Keeps semantic units (lists, sections) intact
* Uses:

  * `max_words=150`
  * overlap between chunks
* Handles:

  * multi-line paragraphs
  * spacing-based paragraph detection

👉 This significantly improves retrieval quality.

---

### 🧠 Embeddings & Caching

* Uses OpenRouter (`text-embedding-3-small`)
* Each PDF is hashed (MD5)
* Embeddings cached locally:

```
embeddings_store/<file_hash>.pkl
```

Avoids recomputation entirely on re-upload.

---

### 🔍 Retrieval System

* Query → embedding
* Cosine similarity against chunk embeddings
* Top-K chunk selection

Still intentionally simple (no reranking yet) for learning clarity.

---

### 💬 Question Answering (Structured Output)

LLM returns **strict JSON**:

```json
{
  "answer": "...",
  "highlights": [
    {
      "text": "exact substring from document",
      "page": 1,
      "type": "direct | evidence"
    }
  ]
}
```

Key behavior:

* Forces **complete answers for list-type questions**
* Extracts **verbatim supporting text**
* Separates:

  * direct answers
  * supporting evidence

---

### 🎯 Grounded Highlights (New 🚀)

This is a major upgrade.

The system now:

1. Matches highlight text → exact word positions
2. Locates bounding boxes in the PDF
3. Draws rectangles on the page
4. Saves annotated images

Output:

```json
"images": [
  {
    "page": 2,
    "types": ["direct", "evidence"],
    "image_path": "images/<file_hash>_p2.png"
  }
]
```

Highlight colors:

* 🟢 Green → Direct answer
* 🟠 Orange → Supporting evidence

👉 This bridges the gap between **LLM answers and visual document grounding**.

---

### 🖼️ Image Rendering

* Uses `pdfplumber` page rendering
* Generates one annotated image per page
* Served via FastAPI static route:

```
/images/<file>.png
```

---

### 💬 Chat Memory

* Session-based (`session_id`)
* Maintains short conversation history
* Used in LLM prompt for context continuity
* Not persisted (in-memory only)

---

## 🚀 Backend API

### 📤 Upload PDF

```
POST /upload-pdf
```

Response:

```json
{
  "message": "Processed and saved",
  "file_hash": "...",
  "chunks": 120
}
```

OR (cached):

```json
{
  "message": "Loaded from cache",
  "file_hash": "...",
  "chunks": 120
}
```

---

### 💬 Ask Question

```
POST /ask
```

Request:

```json
{
  "session_id": "user1",
  "file_hash": "abc123",
  "query": "What are the main rules?"
}
```

Response:

```json
{
  "query": "...",
  "answer": "...",
  "highlights": [...],
  "history": [...],
  "images": [...]
}
```

---

## 🧪 Frontend (Streamlit Demo)

Located at:

```
frontend/streamlit_demo.py
```

* Standalone UI
* Runs its own RAG pipeline
* Not connected to backend

👉 Acts as a **learning sandbox**, not production flow.

---

## 🧱 How It Works (Updated Flow)

### 1. PDF → Words (with positions)

* Extract words + bounding boxes

### 2. Words → Structured Chunks

* Rebuild lines and paragraphs
* Chunk semantically

### 3. Chunks → Embeddings

* Convert each chunk into a vector

### 4. Query → Retrieval

* Embed query
* Find most relevant chunks

### 5. Context → LLM

* Send context + chat history
* Enforce structured JSON output

### 6. Highlights → Coordinates

* Match text → word tokens
* Compute bounding boxes

### 7. Render Images

* Draw highlights on PDF pages
* Save + return image paths

---

## 💾 Data Storage

### PDFs

```
pdf_store/<file_hash>.pdf
```

### Embeddings

```python
{
  "chunks": [...],
  "embeddings": [...]
}
```

### Images

```
images/<file_hash>_p<page>.png
```

---

## ⚠️ Limitations

* Single-PDF workflow (per query)
* No vector database (uses pickle)
* No reranking / hybrid search
* Highlight matching is token-based (can fail on edge cases)
* Chat memory not persistent
* No authentication or multi-user isolation
* Not optimized for large-scale PDFs

---

## 🔧 Setup

```bash
pip install fastapi uvicorn pdfplumber openai numpy python-dotenv python-multipart streamlit
```

`.env`:

```env
OPENROUTER_API_KEY=your_key_here
```

Run backend:

```bash
uvicorn backend.main:app --reload
```

---

## 🔮 Next Steps

* Better highlight matching (fuzzy / semantic alignment)
* Hybrid search (BM25 + embeddings)
* Reranking layer
* Persistent chat memory (Redis / DB)
* Multi-document querying
* Streaming responses
* Proper frontend (React or similar)
* Vector DB integration (FAISS / Pinecone / Weaviate)

---

## 📌 Why This Project Exists

I’m intentionally **not using frameworks like LangChain**.

The goal is to deeply understand:

* how retrieval actually works
* how chunking affects answers
* how LLMs use context
* how to ground answers back to source documents

---

## 🤝 Notes

This is not production-ready.

It’s a **learning-first system** that has now reached a stage where it:

✅ Retrieves relevant context
✅ Generates structured answers
✅ Grounds responses visually in the original PDF

And that last part—**closing the loop between LLM output and source document**—is where things are getting really interesting.
