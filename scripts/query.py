#!/usr/bin/env python3
"""
Query the ChromaDB RAG index built by build_index.py.

Usage:
  python scripts/query.py "what are the rules for annual leave?"
  python scripts/query.py "disciplinary procedures" --n 5
  python scripts/query.py "salary scales" --section "Annex I"
"""

import os
import sys
import argparse
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION = "un2018"
MODEL = "all-MiniLM-L6-v2"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="Question or keywords to search")
    parser.add_argument(
        "--n", type=int, default=3,
        help="Number of results to return (default: 3)",
    )
    parser.add_argument(
        "--section",
        help='Filter by section metadata (e.g. "Chapter V", "Annex I")',
    )
    args = parser.parse_args()

    model = SentenceTransformer(MODEL)
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(COLLECTION)

    embedding = model.encode([args.query]).tolist()
    where = {"section": args.section} if args.section else None

    results = collection.query(
        query_embeddings=embedding,
        n_results=args.n,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits = list(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ))

    print(f'\nQuery: "{args.query}"')
    if args.section:
        print(f"Filter: section = {args.section!r}")
    print(f"Top {len(hits)} results:\n")

    for i, (doc, meta, dist) in enumerate(hits):
        score = 1 - dist
        print(f"{'─' * 60}")
        print(f"[{i+1}] score={score:.3f} | {meta['source']}, "
              f"pp. {meta['pages']}")
        print(f"     {meta['section']} › {meta['heading']}")
        print()
        excerpt = doc[:600]
        if len(doc) > 600:
            excerpt += "…"
        print(excerpt)
        print()


if __name__ == "__main__":
    main()
