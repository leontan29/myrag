---
name: query
description: Answer questions about the UN Staff Regulations and Rules (un2018.pdf) using the local RAG index. Use when user asks a question about UN staff rules, regulations, leave, salary, disciplinary procedures, or any content from the document.
---

The user is querying the UN Staff Regulations and Rules knowledge base.

## Input

The user's question is in the skill args (after `/query`). If no args,
ask the user what they want to know.

## Steps

1. **Rewrite the query in legal terminology** before searching.
   The index contains formal legal language; colloquial questions
   won't match well. Translate the user's question into the
   terminology the document uses. Examples:

   - "took money from vendor" →
     "accept remuneration gift favour source contractual relationship"
   - "got fired" → "separation from service termination"
   - "bonus" → "special post allowance incentive payment"
   - "sick days" → "sick leave entitlement full salary half salary"

2. Run the RAG query with the rewritten terms:
   ```
   python3 /home/sprite/p/myrag/scripts/query.py "<rewritten query>" --n 5
   ```

3. If scores are all below 0.55, also run a second query with
   different synonyms or a narrower focus, and merge the results.

4. Read the retrieved chunks carefully.

5. Synthesize a clear, direct answer using only the retrieved content.
   - Cite every claim: `(un2018.pdf, p. N, Section › Heading)`
   - Combine multiple relevant chunks into one coherent answer
   - If chunks don't contain enough to answer, say so explicitly

6. Format: lead with the direct answer, then supporting detail.
   End with a **Sources** list of regulations/rules cited.

## Rules

- Never invent content not in the retrieved chunks
- Always include page number citations
- Use the user's original question language in the answer,
  not the rewritten legal terms
