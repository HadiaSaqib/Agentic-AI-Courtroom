import json
import math
from .db import get_conn
from .embedder import embed

def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0

def store_chunk(source, text, embedding):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)",
        (source, text, json.dumps(embedding))
    )
    conn.commit()
    conn.close()

def build_vector_db(chunks):
    for source, chunk in chunks:
        emb = embed(chunk)
        store_chunk(source, chunk, emb)

def retrieve(query, top_k=5):
    q_emb = embed(query)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, source, text, embedding FROM chunks")
    rows = cur.fetchall()

    scored = []
    for cid, source, text, emb_json in rows:
        emb = json.loads(emb_json)
        score = cosine_similarity(q_emb, emb)
        scored.append({
            "chunk_id": cid,
            "source": source,
            "text": text,
            "score": score
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate based on text
    seen_texts = set()
    unique_scored = []
    for item in scored:
        if item["text"] not in seen_texts:
            unique_scored.append(item)
            seen_texts.add(item["text"])
        if len(unique_scored) >= top_k:
            break

    # Insert query into queries table
    cur.execute(
        "INSERT INTO queries (question) VALUES (?)",
        (query,)
    )
    query_id = cur.lastrowid

    # Store only unique top-k retrievals in evidence_logs
    for r in unique_scored:
        cur.execute(
            "INSERT INTO evidence_logs (query_id, chunk_id, score) VALUES (?, ?, ?)",
            (query_id, r["chunk_id"], r["score"])
        )

    conn.commit()
    conn.close()

   # Return simplified evidence list
    return [
        {
            "chunk_id": r["chunk_id"],
            "source": r["source"],
            "text": r["text"],
            "score": r["score"]
        }
        for r in unique_scored
    ]

