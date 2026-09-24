"""A case's documents: the petition, the reply, the FIR, the chargesheet, every order.

Stored page by page, because a lawyer cites pages. Search answers with the file, the page
and the words, never with a paraphrase. Orders the watcher collected are searchable too,
alongside what the lawyer uploads, so "where did the court say that" has one answer box.

Extraction:
* PDF   — pypdf, one entry per page. A page with no text layer is recorded as empty and
          flagged, so a scanned bundle says it needs OCR instead of silently matching nothing.
* DOCX  — paragraphs, one page (Word has no fixed pages).
* TXT/MD — form feeds (\\f) split pages, as court copies exported to text often carry them.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from xml.etree import ElementTree

from manu.case_state.store import CaseStore, new_id

_SCHEMA = """
create table if not exists documents (
  id text primary key,
  case_id text not null,
  name text not null,
  kind text not null,
  sha256 text not null,
  pages text not null,
  uploaded_at text not null
);
create index if not exists documents_case on documents(case_id);
create unique index if not exists documents_case_sha on documents(case_id, sha256);
"""

MAX_BYTES = 40 * 1024 * 1024
SUPPORTED = (".pdf", ".docx", ".txt", ".md")


class DocumentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    case_id: str
    name: str
    kind: str
    sha256: str
    pages: list[str]
    uploaded_at: str

    def summary(self) -> dict:
        empty = sum(1 for p in self.pages if not p.strip())
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "pages": len(self.pages),
            "pages_without_text": empty,
            "sha256": self.sha256,
            "uploaded_at": self.uploaded_at,
        }


def extract_pages(name: str, data: bytes) -> list[str]:
    lower = name.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            reader = PdfReader(io.BytesIO(data))
            return [(page.extract_text() or "").strip() for page in reader.pages]
        except (PdfReadError, ValueError) as exc:
            raise DocumentError(f"Could not read the PDF: {exc}") from exc
    if lower.endswith(".docx"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                root = ElementTree.fromstring(archive.read("word/document.xml"))
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise DocumentError(f"Could not read the Word file: {exc}") from exc
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = ["".join(t.text or "" for t in p.iter(f"{ns}t")) for p in root.iter(f"{ns}p")]
        return ["\n".join(p for p in paragraphs if p.strip())]
    if lower.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
        return [page.strip() for page in text.split("\f")]
    raise DocumentError(f"Unsupported file type. Upload {', '.join(SUPPORTED)}.")


class DocumentStore:
    def __init__(self, cases: CaseStore) -> None:
        self.cases = cases
        self._db: sqlite3.Connection = cases._db  # one database file per installation
        self._db.executescript(_SCHEMA)

    def add(self, case_id: str, name: str, data: bytes, *, kind: str = "") -> Document:
        if self.cases.get(case_id) is None:
            raise DocumentError("case not found")
        if len(data) > MAX_BYTES:
            raise DocumentError("File is larger than 40 MB.")
        name = name.strip().replace("/", "_")[:200] or "document"
        digest = hashlib.sha256(data).hexdigest()
        existing = self._db.execute(
            "select id from documents where case_id=? and sha256=?", (case_id, digest)
        ).fetchone()
        if existing:
            return self.get(existing[0])  # type: ignore[return-value]
        pages = extract_pages(name, data)
        doc = Document(
            id=new_id("doc"),
            case_id=case_id,
            name=name,
            kind=kind or _guess_kind(name, pages),
            sha256=digest,
            pages=pages,
            uploaded_at=datetime.now(UTC).isoformat(),
        )
        with self.cases._tx() as db:
            db.execute(
                "insert into documents(id, case_id, name, kind, sha256, pages, uploaded_at) values(?,?,?,?,?,?,?)",
                (doc.id, doc.case_id, doc.name, doc.kind, doc.sha256, json.dumps(doc.pages), doc.uploaded_at),
            )
        return doc

    def get(self, document_id: str) -> Document | None:
        row = self._db.execute(
            "select id, case_id, name, kind, sha256, pages, uploaded_at from documents where id=?", (document_id,)
        ).fetchone()
        return _row(row) if row else None

    def for_case(self, case_id: str) -> list[Document]:
        rows = self._db.execute(
            "select id, case_id, name, kind, sha256, pages, uploaded_at from documents where case_id=? order by uploaded_at",
            (case_id,),
        ).fetchall()
        return [_row(r) for r in rows]

    def search(self, case_id: str, query: str, *, limit: int = 12) -> list[dict]:
        """Pages that best match the query, with a quote around the first hit.

        Question words and particles are dropped ("what was recovered?" searches for
        "recovered"). A page must contain as many of the remaining words as the best page
        does, so a strong match is never buried under pages that share one common word.
        Orders collected by the watcher are searched with the uploaded documents, cited
        by their date.
        """
        terms = [t for t in dict.fromkeys(re.findall(r"[\w./-]+", query.lower())) if len(t) > 1 and t not in _STOPWORDS]
        if not terms:
            return []
        sources: list[tuple[str, str, str, int, str]] = []
        for doc in self.for_case(case_id):
            for number, text in enumerate(doc.pages, start=1):
                sources.append(("document", doc.id, doc.name, number, text))
        case = self.cases.get(case_id)
        for order in case.orders if case else []:
            sources.append(
                ("order", order.on.isoformat(), f"Order dated {order.on.strftime('%d.%m.%Y')}", 1, order.text)
            )
        hits: list[dict] = []
        for kind, ref, name, page, text in sources:
            lower = text.lower()
            found = [t for t in terms if t in lower]
            if not found:
                continue
            first = min(lower.find(t) for t in found)
            hits.append(
                {
                    "kind": kind,
                    "ref": ref,
                    "name": name,
                    "page": page,
                    "matched": len(found),
                    "score": sum(lower.count(t) for t in found),
                    "terms": found,
                    "quote": _quote(text, first, len(found[0])),
                }
            )
        if not hits:
            return []
        best = max(h["matched"] for h in hits)
        hits = [h for h in hits if h["matched"] == best]
        hits.sort(key=lambda h: -h["score"])
        return hits[:limit]


_STOPWORDS = frozenset(
    "a an the of to in on at by for from with and or is are was were be been being it its this that these those "
    "what which who whom whose when where why how did does do has have had can could should would will shall may "
    "any all there their his her he she they them i we you me my our your about into as than then so not no yes "
    "case matter please tell show give".split()
)


def _quote(text: str, start: int, length: int, *, around: int = 160) -> str:
    left = max(0, text.rfind(".", 0, max(0, start - 20)) + 1, start - around)
    right = min(len(text), start + length + around)
    snippet = " ".join(text[left:right].split())
    return ("… " if left > 0 else "") + snippet + (" …" if right < len(text) else "")


def _guess_kind(name: str, pages: list[str]) -> str:
    """A first guess from the title, most specific first: a bail application cites the
    FIR on its first page, so "fir" must not win just because the letters appear."""
    title = name.lower()
    head = title + " " + (pages[0][:600].lower() if pages else "")
    for kind, words in (
        (
            "bail_application",
            ("bail application", "application for bail", "application for regular bail", "section 483", "u/s 483"),
        ),
        ("chargesheet", ("chargesheet", "charge sheet", "final report u/s 193", "final report under section 193")),
        ("fir", ("first information report",)),
        ("reply", ("reply", "written statement", "counter affidavit")),
        ("petition", ("petition", "plaint", "suit for")),
        ("order", ("present:",)),
    ):
        if any(word in head for word in words):
            return kind
    return "fir" if re.search(r"\bfir\b", title) else "document"


def _row(row: tuple) -> Document:
    return Document(row[0], row[1], row[2], row[3], row[4], json.loads(row[5]), row[6])
