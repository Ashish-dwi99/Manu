"""Check every quotation in an answer against the case's own papers.

The same discipline Mike applies to its document citations (studied, not copied): a
quote is located in the source text by progressively more tolerant matching — exact,
then whitespace- and case-insensitive, then also ignoring punctuation (OCR and PDF text
extraction mangle both). A quote that cannot be located anywhere in this case's
documents or orders is reported as unverified, and the UI says so beside the answer.
"""

from __future__ import annotations

import re

from manu.documents import DocumentStore

_QUOTED = re.compile(r"[\"“]([^\"”]{12,600})[\"”]")


def _norm(text: str, *, punctuation: bool) -> str:
    text = text.lower()
    if punctuation:
        text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def locate(source: str, quote: str) -> bool:
    if not source or not quote:
        return False
    if quote in source:
        return True
    if _norm(quote, punctuation=False) in _norm(source, punctuation=False):
        return True
    return _norm(quote, punctuation=True) in _norm(source, punctuation=True)


def quotes_in(answer: str) -> list[str]:
    return [m.group(1).strip() for m in _QUOTED.finditer(answer or "")]


def verify_answer(documents: DocumentStore, case_id: str, answer: str) -> list[dict]:
    """Each quotation in `answer`, with where it was found or `verified: False`."""
    sources: list[tuple[str, int | None, str]] = []
    for doc in documents.for_case(case_id):
        for number, text in enumerate(doc.pages, start=1):
            sources.append((doc.name, number, text))
    case = documents.cases.get(case_id)
    for order in case.orders if case else []:
        sources.append((f"Order dated {order.on.strftime('%d.%m.%Y')}", None, order.text))
    results = []
    for quote in quotes_in(answer):
        found = next(((name, page) for name, page, text in sources if locate(text, quote)), None)
        results.append(
            {
                "quote": quote,
                "verified": found is not None,
                "source": found[0] if found else None,
                "page": found[1] if found else None,
            }
        )
    return results
