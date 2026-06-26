# myrag — Design and Reproduction Guide

This document explains how this RAG system was built
and how to reproduce it from scratch.

## What This Is

A retrieval-augmented generation (RAG) system over
the UN Staff Regulations and Rules
(ST/SGB/2018/1, 2018 edition, 120 pages).

Source document: `un2018.pdf`

The pipeline:

1. Extract text from PDF (PyMuPDF)
2. Reformat each section into clean Markdown
   (Claude API, `claude-opus-4-8`)
3. Chunk at Regulation/Rule level and embed
   (sentence-transformers, `all-MiniLM-L6-v2`)
4. Store in a local vector database (ChromaDB)
5. Query via CLI or `/query` skill in Claude Code

---

## Directory Structure

```
myrag/
  un2018.pdf                   source document
  docs/
    index.md                   table of contents
    chapters/01-*.md … 12-*   Article + Chapter pairs
    annexes/i-*.md … iv-*     Annexes I–IV
    appendices/a-*.md … d-*   Appendices A–D
  scripts/
    extract_pdf.py             PDF → Markdown
    build_index.py             Markdown → ChromaDB
    query.py                   CLI search tool
  chroma_db/                   vector store (gitignored)
  .claude/
    skills/query/SKILL.md      /query skill for Claude Code
```

---

## PDF Structure Discovery

The PDF has no embedded table of contents
(`doc.get_toc()` returns empty). Structure was
discovered by scanning all pages for text spans
with font size ≈ 12.1pt, which mark section
headings.

Document layout:

| Pages | Content |
|-------|---------|
| 1–9 | Preamble, legal basis, ToC |
| 10–91 | Articles I–XII (Staff Regulations) interleaved with Chapters I–XIII (Staff Rules) |
| 92–99 | Annexes I–IV to the Staff Regulations |
| 100–120 | Appendices A–D to the Staff Rules |

The interleaving pattern is:
Article I (p.10) → Chapter I (p.14) →
Article II (p.19) → Chapter II (p.20) → …

Each output file covers one topic area and contains
both the Regulation (Article) and its corresponding
Rules (Chapter).

---

## Step 1 — Extract PDF to Markdown

**Script:** `scripts/extract_pdf.py`

**Dependencies:**
```
pip install pymupdf anthropic
```

**Requires:** `ANTHROPIC_API_KEY` in environment
or `.env` file.

**How it works:**

- Page boundaries for each section are hardcoded
  based on the structure discovery above.
- PyMuPDF (`fitz`) extracts raw text page by page,
  prefixed with `[Page N]` markers.
- Each section's raw text is sent to
  `claude-opus-4-8` via the Anthropic streaming
  API to reformat into clean Markdown:
  - `###` headings per Regulation/Rule
  - 65-char prose line wrap
  - Markdown tables for salary/indemnity tables
  - PDF artifacts stripped (running headers,
    page numbers embedded in body text)
  - Inline source citations added:
    `> Source: un2018.pdf, p. N`
- Output files include YAML frontmatter:
  ```yaml
  ---
  source: un2018.pdf
  pages: 10-18
  section: Chapter I
  title: Duties, Obligations and Privileges
  regulation: Article I
  ---
  ```
- Files that already exist are skipped, enabling
  safe re-runs after interruption.

**Run:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python3 scripts/extract_pdf.py
```

Produces 20 `.md` files and `docs/index.md`.

**Cost:** ~20 Claude API calls (one per section),
up to 16K output tokens each. Runs in ~10 minutes.

---

## Step 2 — Build the Vector Index

**Script:** `scripts/build_index.py`

**Dependencies:**
```
pip install chromadb sentence-transformers
```

**How it works:**

- Reads all `docs/**/*.md` (excluding `index.md`).
- Parses YAML frontmatter for metadata.
- Splits each file's body at `##` / `###`
  heading boundaries — one chunk per
  Regulation/Rule.
- Embeds all chunks with
  `sentence-transformers all-MiniLM-L6-v2`
  (runs locally, no API key needed).
- Persists to ChromaDB at `./chroma_db/`
  with cosine similarity metric.
- Each chunk stored with metadata:
  `source`, `pages`, `section`, `title`,
  `regulation`, `heading`, `file`.
- Re-running drops and rebuilds cleanly.

**Run:**
```bash
python3 scripts/build_index.py
```

Produces 248 chunks from 20 files in ~10 seconds.

---

## Step 3 — Query

**Script:** `scripts/query.py`

**How it works:**

- Embeds the query string with the same model.
- Runs cosine similarity search against ChromaDB.
- Prints top-N results with score, source citation,
  section path, and a 600-char excerpt.

**Usage:**
```bash
python3 scripts/query.py "your question" --n 5
python3 scripts/query.py "salary scales" --section "Annex I"
```

**Claude Code skill:** `.claude/skills/query/SKILL.md`

Invoke as `/query your question` inside Claude Code.
Claude runs `query.py`, reads the retrieved chunks,
and synthesizes a cited answer.

---

## Reproducing From Scratch

```bash
# 1. Clone and enter project
git clone https://github.com/leontan29/myrag.git
cd myrag

# 2. Install dependencies
pip install pymupdf anthropic chromadb sentence-transformers

# 3. Set API key
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Extract PDF → Markdown (takes ~10 min, costs API credits)
python3 scripts/extract_pdf.py

# 5. Build vector index (takes ~10 sec, free)
python3 scripts/build_index.py

# 6. Query
python3 scripts/query.py "what is the sick leave entitlement?"
```

The `docs/` Markdown files are committed to the
repository, so Step 4 can be skipped if you only
want to query without re-extracting.

---

## Adding More PDFs

`extract_pdf.py` is scoped to `un2018.pdf` and has
hardcoded section boundaries. To add another PDF:

1. Copy `extract_pdf.py` → `extract_<name>.py`
2. Scan the new PDF for heading font sizes:
   ```python
   import fitz
   doc = fitz.open("new.pdf")
   for pnum in range(doc.page_count):
       for b in doc[pnum].get_text("dict")["blocks"]:
           for line in b.get("lines", []):
               for span in line["spans"]:
                   if span["size"] > 11:
                       print(pnum+1, span["size"], span["text"][:60])
   ```
3. Identify section boundaries and update `SECTIONS`
4. Point output at a new subdirectory under `docs/`
5. Re-run `build_index.py` — it reads all `docs/**/*.md`

---

## Known Limitations

- `query.py` loads the embedding model cold on
  every invocation (~3s startup). For faster
  repeated queries, a persistent embedding server
  would keep the model in memory.
- The 600-char excerpt in `query.py` output can
  truncate long rules before the key numbers appear.
  The skill works around this by reading the source
  `.md` file directly when needed.
- `all-MiniLM-L6-v2` is optimized for speed, not
  legal/domain text. A domain-tuned model or
  larger model (e.g., `all-mpnet-base-v2`) would
  improve retrieval precision at higher cost.
