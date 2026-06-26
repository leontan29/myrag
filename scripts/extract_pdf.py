#!/usr/bin/env python3
"""
Extract UN Staff Regulations & Rules (un2018.pdf) into docs/ hierarchy.
Each section is reformatted by Claude API into clean Markdown for RAG.

Usage: python scripts/extract_pdf.py
Skips files that already exist. Delete a file to re-extract it.
"""

import os
import sys
import fitz
import anthropic

PDF = os.path.join(os.path.dirname(__file__), "..", "un2018.pdf")
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")
MODEL = "claude-opus-4-8"

# (rel_path, section_label, regulation_label, start_page, end_page, title)
# Pages are 1-indexed as printed in the PDF.
SECTIONS = [
    (
        "chapters/01-duties-obligations.md",
        "Chapter I", "Article I", 10, 18,
        "Duties, Obligations and Privileges",
    ),
    (
        "chapters/02-classification.md",
        "Chapter II", "Article II", 19, 20,
        "Classification of Posts and Staff",
    ),
    (
        "chapters/03-salaries.md",
        "Chapter III", "Article III", 21, 36,
        "Salaries and Related Allowances",
    ),
    (
        "chapters/04-appointment-promotion.md",
        "Chapter IV", "Article IV", 37, 43,
        "Appointment and Promotion",
    ),
    (
        "chapters/05-leave.md",
        "Chapter V", "Article V", 44, 49,
        "Annual and Special Leave",
    ),
    (
        "chapters/06-social-security.md",
        "Chapter VI", "Article VI", 50, 53,
        "Social Security",
    ),
    (
        "chapters/07-travel-relocation.md",
        "Chapter VII", "Article VII", 54, 65,
        "Travel and Relocation Expenses",
    ),
    (
        "chapters/08-staff-relations.md",
        "Chapter VIII", "Article VIII", 66, 68,
        "Staff Relations",
    ),
    (
        "chapters/09-separation.md",
        "Chapter IX", "Article IX", 69, 76,
        "Separation from Service",
    ),
    (
        "chapters/10-disciplinary.md",
        "Chapter X", "Article X", 77, 79,
        "Disciplinary Measures",
    ),
    (
        "chapters/11-appeals.md",
        "Chapter XI", "Article XI", 80, 84,
        "Appeals",
    ),
    (
        "chapters/12-general.md",
        "Chapter XII / XIII", "Article XII", 85, 91,
        "General Provisions and Transitional Measures",
    ),
    # Annexes to the Staff Regulations
    (
        "annexes/i-salary-scales.md",
        "Annex I", None, 92, 95,
        "Salary Scales and Related Provisions",
    ),
    (
        "annexes/ii-letters-of-appointment.md",
        "Annex II", None, 96, 96,
        "Letters of Appointment",
    ),
    (
        "annexes/iii-termination-indemnity.md",
        "Annex III", None, 97, 98,
        "Termination Indemnity",
    ),
    (
        "annexes/iv-repatriation-grant.md",
        "Annex IV", None, 99, 99,
        "Repatriation Grant",
    ),
    # Appendices to the Staff Rules
    (
        "appendices/a-pensionable-remuneration.md",
        "Appendix A", None, 100, 103,
        "Pensionable Remuneration",
    ),
    (
        "appendices/b-education-grant.md",
        "Appendix B", None, 104, 104,
        "Education Grant Entitlements",
    ),
    (
        "appendices/c-military-service.md",
        "Appendix C", None, 105, 106,
        "Arrangements Relating to Military Service",
    ),
    (
        "appendices/d-compensation.md",
        "Appendix D", None, 107, 120,
        "Compensation for Death, Injury or Illness",
    ),
]

INDEX_ENTRIES = {
    "chapters": [
        ("chapters/01-duties-obligations.md", "I",
         "Duties, Obligations and Privileges", "10-18"),
        ("chapters/02-classification.md", "II",
         "Classification of Posts and Staff", "19-20"),
        ("chapters/03-salaries.md", "III",
         "Salaries and Related Allowances", "21-36"),
        ("chapters/04-appointment-promotion.md", "IV",
         "Appointment and Promotion", "37-43"),
        ("chapters/05-leave.md", "V",
         "Annual and Special Leave", "44-49"),
        ("chapters/06-social-security.md", "VI",
         "Social Security", "50-53"),
        ("chapters/07-travel-relocation.md", "VII",
         "Travel and Relocation Expenses", "54-65"),
        ("chapters/08-staff-relations.md", "VIII",
         "Staff Relations", "66-68"),
        ("chapters/09-separation.md", "IX",
         "Separation from Service", "69-76"),
        ("chapters/10-disciplinary.md", "X",
         "Disciplinary Measures", "77-79"),
        ("chapters/11-appeals.md", "XI",
         "Appeals", "80-84"),
        ("chapters/12-general.md", "XII/XIII",
         "General Provisions and Transitional Measures", "85-91"),
    ],
    "annexes": [
        ("annexes/i-salary-scales.md",
         "Annex I", "Salary Scales and Related Provisions", "92-95"),
        ("annexes/ii-letters-of-appointment.md",
         "Annex II", "Letters of Appointment", "96"),
        ("annexes/iii-termination-indemnity.md",
         "Annex III", "Termination Indemnity", "97-98"),
        ("annexes/iv-repatriation-grant.md",
         "Annex IV", "Repatriation Grant", "99"),
    ],
    "appendices": [
        ("appendices/a-pensionable-remuneration.md",
         "Appendix A", "Pensionable Remuneration", "100-103"),
        ("appendices/b-education-grant.md",
         "Appendix B", "Education Grant Entitlements", "104"),
        ("appendices/c-military-service.md",
         "Appendix C", "Arrangements Relating to Military Service", "105-106"),
        ("appendices/d-compensation.md",
         "Appendix D",
         "Compensation for Death, Injury or Illness", "107-120"),
    ],
}


def extract_pages(doc, start_page, end_page):
    parts = []
    for i in range(start_page - 1, end_page):
        parts.append(f"[Page {i + 1}]\n{doc[i].get_text()}")
    return "\n\n".join(parts)


def reformat_with_claude(client, raw_text, section_label, title,
                         start_page, end_page):
    prompt = f"""You are reformatting extracted text from the UN Staff \
Regulations and Rules (ST/SGB/2018/1, 2018 edition).

The text below is from {section_label} ({title}), \
pages {start_page}–{end_page} of the PDF.

Reformat into clean, well-structured Markdown for a knowledge base.

Rules:
- Preserve ALL content — do not omit, summarize, or paraphrase
- Use ## and ### headings for sections and sub-sections
- Format each numbered rule/regulation as a ### heading
  (e.g., ### Rule 1.1 — Title)
- Wrap prose lines so no line exceeds 65 characters
- Render tables as Markdown tables
- Strip PDF artifacts: running headers/footers, page numbers
  embedded in body text, repeated document title lines
- Add a source citation at each major section start:
  `> Source: un2018.pdf, p. N`
- Output ONLY the Markdown body — no YAML frontmatter,
  no preamble, no explanation

Raw extracted text:
{raw_text}"""

    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()

    text_blocks = [b for b in msg.content if b.type == "text"]
    if not text_blocks:
        raise RuntimeError(f"No text block in response for {section_label}")
    return text_blocks[-1].text


def frontmatter(section_label, regulation_label, title, start_page, end_page):
    lines = [
        "---",
        "source: un2018.pdf",
        f"pages: {start_page}-{end_page}",
        f"section: {section_label}",
        f"title: {title}",
    ]
    if regulation_label:
        lines.append(f"regulation: {regulation_label}")
    lines.append("---")
    return "\n".join(lines)


def write_index():
    lines = [
        "---",
        "source: un2018.pdf",
        "title: UN Staff Regulations and Rules (ST/SGB/2018/1)",
        "---",
        "",
        "# UN Staff Regulations and Rules",
        "",
        "ST/SGB/2018/1. Secretary-General's bulletin,",
        "2018 edition. 120 pages.",
        "",
        "## Staff Regulations and Rules (Chapters)",
        "",
    ]
    for path, num, title, pages in INDEX_ENTRIES["chapters"]:
        lines.append(f"- [{num}. {title}]({path}) (pp. {pages})")

    lines += ["", "## Annexes to the Staff Regulations", ""]
    for path, label, title, pages in INDEX_ENTRIES["annexes"]:
        lines.append(f"- [{label} — {title}]({path}) (pp. {pages})")

    lines += ["", "## Appendices to the Staff Rules", ""]
    for path, label, title, pages in INDEX_ENTRIES["appendices"]:
        lines.append(f"- [{label} — {title}]({path}) (pp. {pages})")

    out = os.path.join(DOCS, "index.md")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {out}")


def main():
    doc = fitz.open(PDF)
    client = anthropic.Anthropic()

    for subdir in ("chapters", "annexes", "appendices"):
        os.makedirs(os.path.join(DOCS, subdir), exist_ok=True)

    for (rel_path, section_label, regulation_label,
         start_page, end_page, title) in SECTIONS:
        out_path = os.path.join(DOCS, rel_path)

        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            print(f"skip (exists): {rel_path}")
            continue

        print(f"processing: {rel_path} (pp. {start_page}–{end_page}) ...",
              end=" ", flush=True)
        raw = extract_pages(doc, start_page, end_page)
        body = reformat_with_claude(
            client, raw, section_label, title, start_page, end_page
        )
        fm = frontmatter(section_label, regulation_label,
                         title, start_page, end_page)

        with open(out_path, "w") as f:
            f.write(fm + "\n\n" + body + "\n")
        print("done")

    write_index()
    print("complete.")


if __name__ == "__main__":
    main()
