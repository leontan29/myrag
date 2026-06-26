---
name: query
description: Answer questions about the UN Staff Regulations and Rules (un2018.pdf) using the local RAG index. Use when user asks a question about UN staff rules, regulations, leave, salary, disciplinary procedures, or any content from the document.
---

The user is querying the UN Staff Regulations and Rules knowledge base.

## Input

The user's question is in the skill args (after `/query`). If no args, ask the user what they want to know.

## Steps

1. Run the RAG query to retrieve relevant chunks:
   ```
   python3 /home/sprite/p/myrag/scripts/query.py "<user question>" --n 5
   ```

2. Read the retrieved chunks carefully.

3. Synthesize a clear, direct answer using only the retrieved content.
   - Cite every claim with its source: `(un2018.pdf, p. N, Section › Heading)`
   - If multiple chunks are relevant, combine them into a coherent answer
   - If the chunks don't contain enough information to answer, say so explicitly
     and suggest a more specific question

4. Format the answer in plain prose with citations inline. End with a
   "Sources" list of the specific regulations/rules cited.

## Rules

- Never invent content not present in the retrieved chunks
- Always include page number citations
- Keep the answer concise — lead with the direct answer, then detail
