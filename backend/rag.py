"""
rag.py
======
Embedding creation, storage, retrieval, and answer generation.

All disk I/O goes through storage_paths.paths(user_id, file_id) —
no path strings are constructed here.
"""

import os
import pickle
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
from pdf_utils import get_pdf_image
from storage_paths import paths as file_paths
import re
import json

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

EMBEDDING_MODEL = "text-embedding-3-small"


# ── helpers ───────────────────────────────────────────────────────────────────

def normalize_tokens(text: str) -> list[str]:
    return text.replace("\n", " ").split()


def parse_llm_response(raw: str) -> dict:
    try:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    return {"answer": raw, "highlights": []}


# ── embeddings persistence ────────────────────────────────────────────────────

def save_embeddings(user_id: str, file_id: str, data: dict) -> None:
    """
    Persist chunks + embeddings to disk.
    Keyed by (user_id, file_id) — path resolved via storage_paths.
    """
    p = file_paths(user_id, file_id)
    p.makedirs()

    payload = {
        "user_id": user_id,
        "file_id": file_id,
        "chunks":  data["chunks"],
        "embeddings": data["embeddings"],
    }
    with open(p.embeddings, "wb") as f:
        pickle.dump(payload, f)


def load_embeddings(user_id: str, file_id: str) -> dict | None:
    """
    Load embeddings for (user_id, file_id).
    Returns None if not found.
    Includes a safety check so data can never cross user boundaries.
    """
    p = file_paths(user_id, file_id)
    if not os.path.exists(p.embeddings):
        return None

    with open(p.embeddings, "rb") as f:
        data = pickle.load(f)

    # Defensive: reject if ownership metadata doesn't match
    if data.get("user_id") != user_id or data.get("file_id") != file_id:
        return None

    return data


# ── embedding creation ────────────────────────────────────────────────────────

def create_embeddings(chunks: list[dict]) -> list[dict]:
    texts    = [c["text"] for c in chunks]
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)

    return [
        {
            "chunk_id":    i,
            "text":        chunks[i]["text"],
            "page_number": chunks[i]["page_number"],
            "words":       chunks[i].get("words"),
            "embedding":   response.data[i].embedding,
        }
        for i in range(len(chunks))
    ]


# ── retrieval ─────────────────────────────────────────────────────────────────

def cosine_similarity(a, b) -> float:
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def retrieve_top_chunks(
    query_embedding: list[float],
    chunk_embeddings: list[dict],
    top_k: int = 5,
) -> list[tuple]:
    """Returns list of (score, text, page_number, words)."""
    scored = [
        (
            cosine_similarity(query_embedding, item["embedding"]),
            item["text"],
            item["page_number"],
            item.get("words"),
        )
        for item in chunk_embeddings
    ]
    scored.sort(reverse=True, key=lambda x: x[0])
    return scored[:top_k]


# ── generation ────────────────────────────────────────────────────────────────

def generate_answer(query: str, context: str, history: list | None = None) -> str:
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
- "direct"   = sentence/passage that directly answers the question.
- "evidence" = supporting context when no direct answer exists.
- Copy highlight text EXACTLY from context — no rephrasing, no added words.
- You may include multiple highlights from different pages.
- If the answer spans multiple passages, synthesize them into one complete answer.
- Never give a one-fragment answer when the question asks for a complete list.
"""

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        for turn in history[-4:]:   # last 2 exchanges
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {query}",
    })

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
    )
    return response.choices[0].message.content


# ── main RAG pipeline ─────────────────────────────────────────────────────────

def answer_from_chunks(
    query: str,
    chunk_embeddings: list[dict],
    user_id: str,
    file_id: str,
    history: list | None = None,
) -> tuple[str, list, list]:
    """
    Returns (answer, highlights, images).
    Note: user_id + file_id are explicit args — no ambiguity.
    """
    query_emb = client.embeddings.create(
        model=EMBEDDING_MODEL, input=query
    ).data[0].embedding

    top_chunks = retrieve_top_chunks(query_emb, chunk_embeddings, top_k=5)

    context = "\n\n".join(
        f"[Page {page}]\n{chunk}"
        for _, chunk, page, _ in top_chunks
    )

    raw    = generate_answer(query, context, history=history)
    parsed = parse_llm_response(raw)

    answer     = parsed["answer"]
    highlights = parsed.get("highlights", [])
    images     = highlight_sources(user_id, file_id, top_chunks, highlights)

    return answer, highlights, images


# ── highlighting ──────────────────────────────────────────────────────────────

def highlight_sources(
    user_id: str,
    file_id: str,
    top_chunks: list[tuple],
    highlights: list[dict],
) -> list[dict]:
    p = file_paths(user_id, file_id)

    page_images: dict[int, object]      = {}
    page_highlight_types: dict[int, set] = {}

    for highlight in highlights:
        target_tokens = normalize_tokens(highlight["text"])
        target_page   = highlight.get("page")
        if target_page is None:
            continue

        for _, _, page, words in top_chunks:
            if not words or page != target_page:
                continue

            if page not in page_images:
                page_images[page] = get_pdf_image(p.pdf, page)

            im         = page_images[page]
            word_texts = [w["text"] for w in words]

            def normalize(s: str) -> str:
                return s.lower().replace("\n", " ").strip()

            target_norm = [normalize(t) for t in target_tokens]

            for i in range(len(word_texts)):
                window_norm = [normalize(w) for w in word_texts[i: i + len(target_tokens)]]
                if window_norm == target_norm:
                    matched = words[i: i + len(target_tokens)]
                    x0     = min(w["x0"]     for w in matched)
                    x1     = max(w["x1"]     for w in matched)
                    top    = min(w["top"]    for w in matched)
                    bottom = max(w["bottom"] for w in matched)
                    color  = "green" if highlight["type"] == "direct" else "orange"
                    im.draw_rect((x0, top, x1, bottom), stroke=color, stroke_width=3)
                    page_highlight_types.setdefault(page, set()).add(highlight["type"])
                    break

    images = []
    for page in page_highlight_types:
        image_path = p.page_image(page)
        page_images[page].save(image_path)
        images.append({
            "page":       page,
            "types":      list(page_highlight_types[page]),
            "image_url":  p.page_image_url(page),   # serve URL, not raw path
        })

    return images