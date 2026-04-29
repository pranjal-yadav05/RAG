import os
import pickle
import numpy as np
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from pdf_utils import get_pdf_image
import re
from typing import List, Dict, Any
import json


load_dotenv()
BASE_URL = "http://localhost:8000"
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

EMBEDDING_MODEL = "text-embedding-3-small"


def normalize_tokens(text):
    return text.replace("\n", " ").split()

def parse_llm_response(raw):
    try:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
    except:
        pass

    return {
        "answer": raw,
        "highlights": []
    }
    
def get_file_hash(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()

def create_embeddings(chunks):
    texts = [chunk["text"] for chunk in chunks]

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )

    embeddings = []

    for i, chunk in enumerate(chunks):
        embeddings.append({
            "text": chunk["text"],
            "embedding": response.data[i].embedding,
            "chunk_id": i,
            "page_number": chunk["page_number"],
            "words": chunk.get("words")
            # "bbox": chunk.get("bbox")
        })
    
    return embeddings

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def retrieve_top_chunks(query_embedding, chunk_embeddings, top_k=5):
    scores = []

    for item in chunk_embeddings:
        score = cosine_similarity(query_embedding, item["embedding"])
        scores.append((
            score,
            item["text"],
            item["page_number"],
            item.get("words")
            # item.get("bbox")
        ))

    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:top_k]

def generate_answer(query, context, history=None):
    system_prompt = """
    You are a helpful assistant answering questions from a document.

    Return ONLY valid JSON in this exact format:
    {
    "answer": "...",
    "highlights": [
        {
        "text": "EXACT substring copied character-for-character from context",
        "page": <number>,
        "type": "direct" | "evidence"
        }
    ]
    }

    RULES:
    - For list questions (e.g. "What are the X commandments/rules/steps?"), 
    your answer must include ALL items in the list, written out fully.
    - "direct" = sentence/passage that directly answers the question.
    - "evidence" = supporting context when no direct answer exists.
    - Copy highlight text EXACTLY from context — no rephrasing, no added words.
    - You may include multiple highlights from different pages.
    - If the answer spans multiple passages, synthesize them into one complete answer.
    - Never give a one-fragment answer when the question asks for a complete list.
    """

    messages = [{ "role": "system", "content": system_prompt }]

    if history:
        for turn in history[-4:]:  # last 2 exchanges
            messages.append(turn)

    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}"
    })

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content

def answer_from_chunks(query, chunk_embeddings, file_hash, history=None):
    query_embedding = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query
    ).data[0].embedding

    top_chunks = retrieve_top_chunks(query_embedding, chunk_embeddings, top_k=5)
    
    context = "\n\n".join([
        f"[Page {page}]\n{chunk}"
        for _, chunk, page, _ in top_chunks
    ])

    raw = generate_answer(query, context, history=history)
    parsed = parse_llm_response(raw)

    answer = parsed["answer"]
    highlights = parsed.get("highlights", [])
    images = highlight_sources(file_hash, top_chunks, highlights)

    return answer, highlights, images


def highlight_sources(file_hash, top_chunks, highlights):
    images = []
    pdf_path = f"pdf_store/{file_hash}.pdf"

    page_images = {}
    page_highlight_types = {}

    for highlight in highlights:
        target_tokens = normalize_tokens(highlight["text"])
        target_page = highlight["page"]

        for _, _, page, words in top_chunks:
            if not words or page != target_page:
                continue

            if page not in page_images:
                page_images[page] = get_pdf_image(pdf_path, page)

            im = page_images[page]

            word_texts = [w["text"] for w in words]

            for i in range(len(word_texts)):
                window = word_texts[i:i + len(target_tokens)]

                if window == target_tokens:
                    matched_words = words[i:i + len(target_tokens)]

                    x0 = min(w["x0"] for w in matched_words)
                    x1 = max(w["x1"] for w in matched_words)
                    top = min(w["top"] for w in matched_words)
                    bottom = max(w["bottom"] for w in matched_words)

                    color = "green" if highlight["type"] == "direct" else "orange"

                    im.draw_rect(
                        (x0, top, x1, bottom),
                        stroke=color,
                        stroke_width=3
                    )

                    page_highlight_types.setdefault(page, set()).add(highlight["type"])
                    break

    # ✅ Save ONE image per page
    for page in page_highlight_types:
        image_path = f"images/{file_hash}_p{page}.png"
        page_images[page].save(image_path)

        images.append({
            "page": page,
            "types": list(page_highlight_types[page]),
            "image_path": image_path
        })

    return images

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