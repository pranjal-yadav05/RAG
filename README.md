# 📄 RAG PDF (Work in Progress)

This is a small project I’m building while learning how **Retrieval-Augmented Generation (RAG)** works under the hood.

The app lets you upload a single PDF and ask questions about it. It extracts text, creates embeddings, retrieves relevant chunks, and uses an LLM to generate answers.

It’s not meant to be complete or production-ready. It’s a learning project where I’m building things manually instead of relying on full frameworks.

---

## 🧠 What I’m Trying to Learn

* How embeddings behave and how they’re used for retrieval
* How chunking affects answer quality
* How much context actually matters for LLM responses
* What a minimal RAG pipeline looks like end-to-end
* Where simple approaches break

---

## ⚙️ Current Features

* Upload **one PDF file**
* Extract text using `pdfplumber`
* Split text into overlapping chunks
* Generate embeddings using OpenRouter (`text-embedding-3-small`)
* Cache embeddings locally to avoid recomputation
* Retrieve relevant chunks using cosine similarity
* Ask questions in a chat interface
* Show retrieved chunks used for answering

---

## 🧱 How It Works

### 1. PDF → Text

* Reads all pages from the uploaded PDF
* Combines everything into a single text string

### 2. Text → Chunks

* Fixed-size chunking
* Chunk size: 1000 characters
* Overlap: 200 characters
* No semantic or sentence-based splitting

### 3. Embeddings

* Each chunk is converted into a vector
* Stored locally using a hash of the file

### 4. Retrieval

* User query is embedded
* Cosine similarity is computed against all chunks
* Top matches are selected:

  * Prefer chunks with similarity > 0.75
  * Otherwise fallback to top 3

### 5. LLM Response

* Sends:

  * system prompt (strictly context-based answering)
  * recent chat history (last few messages)
  * retrieved context
* Uses `gpt-4o-mini` via OpenRouter

---

## 💾 Embedding Cache

* Each PDF is hashed using MD5

* Embeddings stored at:

  ```
  embeddings_store/<file_hash>.pkl
  ```

* Prevents recomputing embeddings when the same file is uploaded again

---

## 💬 Chat Memory

* Stored in `st.session_state`
* Only recent messages are included in the prompt
* Not persisted across sessions
* No multi-user handling

---

## ⚠️ Limitations

* Works with **one PDF at a time only**
* Retrieval is basic (cosine similarity only)
* Fixed similarity threshold (0.75)
* Chunking is character-based (not semantic)
* No reranking
* No vector database (everything in memory / local file)
* Chat memory is temporary
* Performance may degrade with large PDFs

---

## 🔧 Setup

```bash
pip install streamlit pdfplumber openai python-dotenv numpy
```

Create a `.env` file:

```env
OPENROUTER_API_KEY=your_key_here
```

Run the app:

```bash
streamlit run app.py
```

---

## 📌 Why I Built This

I wanted to understand RAG by building it myself instead of relying on abstractions.

This is a simple implementation to explore:

* how retrieval works
* how context is constructed
* and how LLM responses change based on that

---

## 🔮 Possible Next Steps

* Improve chunking (sentence / semantic)
* Better retrieval strategy (not just cosine + threshold)
* Add reranking
* Store chat history persistently
* Experiment with vector databases

---

## 🤝 Notes

This is not a finished system. It’s a working snapshot of what I’ve built and understood so far. I’ll keep updating it as I learn more.

---
