import streamlit as st
import pdfplumber
from openai import OpenAI
import os    
from dotenv import load_dotenv
import numpy as np
import hashlib
import pickle

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

st.title("RAG PDF")
st.subheader("Upload a PDF file and ask questions about its content")

def get_file_hash(file):
    hasher = hashlib.md5()
    for chunk in iter(lambda: file.read(4096), b""):
        hasher.update(chunk)
    file.seek(0)
    return hasher.hexdigest()

def save_embeddings(file_hash, data):
    os.makedirs("embeddings_store", exist_ok=True)
    with open(f"embeddings_store/{file_hash}.pkl", "wb") as f:
        pickle.dump(data, f)

def load_embeddings(file_hash):
    path = f"embeddings_store/{file_hash}.pkl"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

pdf_file = st.file_uploader("Upload a PDF file", type=["pdf"])

@st.cache_data
def create_embeddings(chunks):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunks
    )

    chunk_embeddings = []
    for i, chunk in enumerate(chunks):
        chunk_embeddings.append({
            "text": chunk,
            "embedding": response.data[i].embedding,
            "chunk_id": i
        })
    
    return chunk_embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

if pdf_file is not None:
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    
    chunk_size = 1000
    overlap = 200

    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i+chunk_size])
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    file_hash = get_file_hash(pdf_file)

    chunk_embeddings = load_embeddings(file_hash)

    if chunk_embeddings is None:
        st.write("Creating embeddings (first time)...")
        chunk_embeddings = create_embeddings(chunks)
        save_embeddings(file_hash, chunk_embeddings)
    else:
        st.write("Loaded cached embeddings!")
        
    query = st.chat_input("Ask a question about the PDF")

    if query:
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.write(query)
        
        # --- Embedding and Retrieval ---
        response = client.embeddings.create(
            model = "text-embedding-3-small",
            input = query
        )
        query_embedding = response.data[0].embedding
        
        scores = []

        for item in chunk_embeddings:
            score = cosine_similarity(query_embedding, item["embedding"])
            scores.append((score, item["text"]))
        
        scores.sort(reverse=True)

        filtered = [(s, c) for s, c in scores if s > 0.75]
        if len(filtered) == 0:
            top_chunks = scores[:3]
        else:
            top_chunks = filtered[:3]
        
        context = "\n\n".join([chunk for _, chunk in top_chunks])

        base_prompt = """
            You are a helpful assistant that answers questions ONLY based on the provided context. 
            If the answer is not in the context, say you don't know.
            Do not infer beyond the text.
        """

        
        # --- Message Memory and LLM ---
        messages = [
            {
                "role": "system", 
                "content": base_prompt
            },
        ]

        messages.extend(st.session_state.chat_history[-6:-1])  # exclude latest user query

        messages.append({"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"})

        response = client.chat.completions.create(
            model = "openai/gpt-4o-mini",
            messages = messages
        )
        
        answer = response.choices[0].message.content
    
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

        with st.chat_message("assistant"):
            st.write(answer)
            with st.expander("Retrieved Context"):
                for score, chunk in scores[:3]:
                    st.write(score)
                    st.write(chunk)
                    st.write("-----")



