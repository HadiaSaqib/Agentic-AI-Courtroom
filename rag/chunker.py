import os
from pathlib import Path
import json
from .db import init_db, get_conn
from .embedder import embed

# Step 1: Initialize DB
init_db()

# Step 2: Load all text files from KB folder
def load_kb_texts(kb_dir="data/kb"):
    docs = []
    for p in Path(kb_dir).glob("*.txt"):
        docs.append((p.name, p.read_text(encoding="utf-8")))
    return docs

# Step 3: Chunking function
def chunk_text(text, max_words=180):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# Step 4: Store chunk in DB (prevents duplicates)
def store_chunk(source, text, embedding):
    conn = get_conn()
    cur = conn.cursor()
    # Check if chunk already exists
    cur.execute("SELECT id FROM chunks WHERE source=? AND text=?", (source, text))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO chunks (source, text, embedding) VALUES (?, ?, ?)",
            (source, text, json.dumps(embedding))
        )
    conn.commit()
    conn.close()

# Step 5: Insert chunks + embeddings into DB
documents = load_kb_texts("data/kb")  # folder containing .txt files

for source, text in documents:
    for chunk in chunk_text(text):
        emb = embed(chunk)
        store_chunk(source, chunk, emb)

print("Chunks inserted and embeddings generated.")