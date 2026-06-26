#!/usr/bin/env python3
"""
Build ChromaDB vector index from docs/**/*.md.
Chunks at ### heading level (one chunk per Regulation/Rule).
Embeds with sentence-transformers (BAAI/bge-base-en-v1.5, runs locally).

Usage: python scripts/build_index.py
Re-running drops and rebuilds the collection cleanly.
"""

import os
import re
import glob
import yaml
import chromadb
from sentence_transformers import SentenceTransformer

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION = "un2018"
MODEL = "BAAI/bge-base-en-v1.5"
BATCH = 100


def parse_frontmatter(text):
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---", 4)
    meta = yaml.safe_load(text[4:end]) or {}
    body = text[end + 4:].strip()
    return meta, body


def split_chunks(body, meta, filepath):
    """Split body at ## / ### boundaries; return list of (heading, text) pairs."""
    # Split on any ## or ### heading line
    # Split at ##, ###, and #### boundaries for fine-grained chunks.
    # #### sub-sections (e.g. "Honours, gifts or remuneration") are the
    # level where specific prohibitions live inside large rules like 1.2.
    parts = re.split(r"^(#{2,4} .+)$", body, flags=re.MULTILINE)

    chunks = []
    heading = meta.get("title", os.path.basename(filepath))
    parent = heading  # tracks nearest ## or ### heading for context
    buf = []

    for part in parts:
        if re.match(r"^#{2,4} ", part):
            if "".join(buf).strip():
                chunks.append((heading, "".join(buf).strip()))
            level = len(re.match(r"^(#+)", part).group(1))
            label = re.sub(r"^#{2,4} ", "", part).strip()
            if level <= 3:
                parent = label
                heading = label
            else:
                # #### sub-section: prefix with parent rule for context
                heading = f"{parent} › {label}"
            buf = []
        else:
            buf.append(part)

    if "".join(buf).strip():
        chunks.append((heading, "".join(buf).strip()))

    return chunks


def main():
    model = SentenceTransformer(MODEL)
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        client.delete_collection(COLLECTION)
        print("Dropped existing collection.")
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    md_files = sorted(
        f for f in glob.glob(os.path.join(DOCS, "**", "*.md"), recursive=True)
        if not f.endswith("index.md")
    )

    ids, docs, metas = [], [], []

    for filepath in md_files:
        rel = os.path.relpath(filepath, os.path.join(DOCS, ".."))
        with open(filepath) as f:
            raw = f.read()

        meta, body = parse_frontmatter(raw)
        chunks = split_chunks(body, meta, filepath)
        print(f"{rel}: {len(chunks)} chunks")

        for i, (heading, text) in enumerate(chunks):
            ids.append(f"{rel}::{i}")
            docs.append(f"{heading}\n\n{text}")
            metas.append({
                "source":     str(meta.get("source", "")),
                "pages":      str(meta.get("pages", "")),
                "section":    str(meta.get("section", "")),
                "title":      str(meta.get("title", "")),
                "regulation": str(meta.get("regulation", "") or ""),
                "heading":    heading,
                "file":       rel,
            })

    print(f"\nEmbedding {len(docs)} chunks with {MODEL}...")
    embeddings = model.encode(docs, show_progress_bar=True).tolist()

    for i in range(0, len(ids), BATCH):
        collection.add(
            ids=ids[i:i + BATCH],
            documents=docs[i:i + BATCH],
            embeddings=embeddings[i:i + BATCH],
            metadatas=metas[i:i + BATCH],
        )

    print(f"\nIndexed {len(ids)} chunks → {DB_PATH}")


if __name__ == "__main__":
    main()
