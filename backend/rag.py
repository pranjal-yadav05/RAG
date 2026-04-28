import os
import pickle
import numpy as np
import hashlib
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

EMBEDDING_MODEL = "text-embedding-3-small"

def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def create_embeddings(chunks):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=chunks
    )

    embeddings = []

    for i, chunk in enumerate(chunks):
        embeddings.append({
            "text": chunk,
            "embedding": response.data[i].embedding,
            "chunk_id": i
        })
    
    return embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve_top_chunks(query_embedding, chunk_embeddings, top_k=3):
    scores = []

    for item in chunk_embeddings:
        score = cosine_similarity(query_embedding, item["embedding"])
        scores.append((score, item["text"]))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_k]

def generate_answer(query, context):
    system_prompt = """
    You are a helpful assistant.
    Answer ONLY using the provided context.
    If answer is not in context, say you don't know.
    """

    messages = [
        { "role": "system", "content": system_prompt },
        {
            "role": "user",
            "content": f"Context:\n{context}\n\nQuestion: {query}"
        }
    ]

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content

def answer_from_chunks(query, chunk_embeddings):
    query_embedding = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    top_chunks = retrieve_top_chunks(query_embedding, chunk_embeddings)
    context = "\n\n".join([chunk for _, chunk in top_chunks])

    return generate_answer(query, context)

def save_embeddings(file_hash, data):
    os.makedirs("embeddings_store", exist_ok=True)
    path = f"embeddings_store/{file_hash}.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

def load_embeddings(file_hash):
    path = f"embeddings_store/{file_hash}.pkl"

    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)   

    return None