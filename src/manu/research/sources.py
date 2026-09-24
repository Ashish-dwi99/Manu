"""Where judgments come from, and how far each source can be trusted.

Standing, most to least:

* `official`  — the court's own copy (SCI, a High Court, the eCourts judgments portal).
* `licensed`  — a reporter the firm subscribes to (SCC Online, Manupatra) or its own library.
* `lead`      — a free index such as Indian Kanoon. Good for finding; confirm before citing.
* `demo`      — the fictional demo library. Not law.

A source answers like a court connector: a result, `None` (not covered), or
`SourceUnavailable`. The ladder asks every source and keeps the attempts, so the screen can
say what was searched.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from html import unescape
from pathlib import Path
from typing import Literal, Protocol

Standing = Literal["official", "licensed", "lead", "demo"]
STANDING_RANK = {"official": 0, "licensed": 1, "lead": 2, "demo": 3}


class SourceUnavailable(RuntimeError):
    """The source exists but cannot answer now (no token, no network)."""


@dataclass(slots=True)
class JudgmentHit:
    source: str
    doc_id: str
    title: str
    court: str = ""
    decided_on: date | None = None
    citations: list[str] = field(default_factory=list)
    snippet: str = ""
    standing: Standing = "lead"

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "doc_id": self.doc_id,
            "title": self.title,
            "court": self.court,
            "decided_on": self.decided_on.isoformat() if self.decided_on else None,
            "citations": self.citations,
            "snippet": self.snippet,
            "standing": self.standing,
        }


@dataclass(slots=True)
class Judgment:
    source: str
    doc_id: str
    title: str
    paragraphs: list[str]
    """Paragraph 1 is `paragraphs[0]`. Indian judgments are cited by paragraph."""
    court: str = ""
    decided_on: date | None = None
    citations: list[str] = field(default_factory=list)
    uri: str = ""
    standing: Standing = "lead"

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "doc_id": self.doc_id,
            "title": self.title,
            "court": self.court,
            "decided_on": self.decided_on.isoformat() if self.decided_on else None,
            "citations": self.citations,
            "uri": self.uri,
            "standing": self.standing,
            "paragraphs": [{"n": i, "text": text} for i, text in enumerate(self.paragraphs, start=1)],
        }


class JudgmentSource(Protocol):
    name: str
    standing: Standing

    def search(self, query: str, limit: int = 10) -> list[JudgmentHit] | None: ...

    def fetch(self, doc_id: str) -> Judgment | None: ...


_NUMBERED = re.compile(r"^\s*(\d{1,3})\.\s+", re.MULTILINE)


def split_paragraphs(text: str) -> list[str]:
    """Paragraphs as the judgment numbers them ("12. …"), else by blank lines."""
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    marks = list(_NUMBERED.finditer(text))
    numbers = [int(m.group(1)) for m in marks]
    if len(marks) >= 2 and numbers[:2] == [1, 2]:
        parts = []
        for i, mark in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            parts.append(" ".join(text[mark.end() : end].split()))
        return [p for p in parts if p]
    return [" ".join(block.split()) for block in re.split(r"\n\s*\n", text) if block.strip()]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


class LibrarySource:
    """Judgments kept as JSON files: a firm's own library, or the demo's fictional one.

    Each file: {"id", "title", "court", "decided_on", "citations": [...], "text", "uri"}.
    """

    def __init__(self, root: str | Path, *, name: str = "library", standing: Standing = "licensed") -> None:
        self.root = Path(root)
        self.name = name
        self.standing = standing

    def _all(self) -> list[Judgment]:
        out = []
        for path in sorted(self.root.glob("*.json")):
            data = json.loads(path.read_text())
            out.append(
                Judgment(
                    source=self.name,
                    doc_id=str(data["id"]),
                    title=data["title"],
                    court=data.get("court", ""),
                    decided_on=date.fromisoformat(data["decided_on"]) if data.get("decided_on") else None,
                    citations=list(data.get("citations") or []),
                    uri=data.get("uri", ""),
                    paragraphs=split_paragraphs(data.get("text", "")),
                    standing=self.standing,
                )
            )
        return out

    def search(self, query: str, limit: int = 10) -> list[JudgmentHit] | None:
        if not self.root.is_dir():
            return None
        terms = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
        wanted = _norm(query)
        hits: list[tuple[int, JudgmentHit]] = []
        for judgment in self._all():
            by_citation = any(wanted and wanted == _norm(c) for c in judgment.citations)
            haystack = " ".join([judgment.title, *judgment.citations, *judgment.paragraphs]).lower()
            score = 100 if by_citation else sum(haystack.count(t) for t in terms)
            if not score or (terms and not by_citation and not all(t in haystack for t in terms)):
                continue
            best = max(judgment.paragraphs, key=lambda p: sum(p.lower().count(t) for t in terms), default="")
            hits.append(
                (
                    score,
                    JudgmentHit(
                        source=self.name,
                        doc_id=judgment.doc_id,
                        title=judgment.title,
                        court=judgment.court,
                        decided_on=judgment.decided_on,
                        citations=judgment.citations,
                        snippet=best[:280],
                        standing=self.standing,
                    ),
                )
            )
        hits.sort(key=lambda item: -item[0])
        return [hit for _score, hit in hits[:limit]]

    def fetch(self, doc_id: str) -> Judgment | None:
        if not self.root.is_dir():
            return None
        return next((j for j in self._all() if j.doc_id == doc_id), None)


class IndianKanoonSource:
    """Indian Kanoon's API (paid token). A lead: it finds judgments; an official or licensed
    copy confirms them. Set `MANU_INDIANKANOON_TOKEN` to enable."""

    name = "indiankanoon"
    standing: Standing = "lead"
    base = "https://api.indiankanoon.org"

    def __init__(self, token: str | None = None, *, opener=None) -> None:
        self.token = token if token is not None else os.getenv("MANU_INDIANKANOON_TOKEN", "")
        self._open = opener or urllib.request.urlopen

    def _post(self, path: str, params: dict | None = None) -> dict:
        if not self.token:
            raise SourceUnavailable("Indian Kanoon is not configured (set MANU_INDIANKANOON_TOKEN)")
        url = f"{self.base}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        request = urllib.request.Request(
            url, data=b"", method="POST", headers={"Authorization": f"Token {self.token}", "Accept": "application/json"}
        )
        try:
            with self._open(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError) as exc:
            raise SourceUnavailable(f"Indian Kanoon did not answer: {exc}") from exc

    def search(self, query: str, limit: int = 10) -> list[JudgmentHit] | None:
        data = self._post("/search/", {"formInput": query, "pagenum": 0})
        hits = []
        for doc in (data.get("docs") or [])[:limit]:
            hits.append(
                JudgmentHit(
                    source=self.name,
                    doc_id=str(doc.get("tid")),
                    title=_strip_html(doc.get("title", "")),
                    court=doc.get("docsource", ""),
                    decided_on=_ik_date(doc.get("publishdate")),
                    snippet=_strip_html(doc.get("headline", ""))[:280],
                    standing=self.standing,
                )
            )
        return hits

    def fetch(self, doc_id: str) -> Judgment | None:
        if not doc_id.isdigit():
            return None
        data = self._post(f"/doc/{doc_id}/")
        text = _strip_html(re.sub(r"</p>|<br\s*/?>", "\n\n", data.get("doc", ""), flags=re.I))
        return Judgment(
            source=self.name,
            doc_id=doc_id,
            title=_strip_html(data.get("title", "")),
            court=data.get("docsource", ""),
            decided_on=_ik_date(data.get("publishdate")),
            uri=f"https://indiankanoon.org/doc/{doc_id}/",
            paragraphs=split_paragraphs(text),
            standing=self.standing,
        )


def _strip_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def _ik_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


@dataclass(slots=True)
class Attempt:
    source: str
    outcome: str


class ResearchLadder:
    def __init__(self, sources: list) -> None:
        self.sources = sources

    def search(self, query: str, limit: int = 10) -> tuple[list[JudgmentHit], list[Attempt]]:
        hits: list[JudgmentHit] = []
        attempts: list[Attempt] = []
        for source in self.sources:
            try:
                found = source.search(query, limit)
            except SourceUnavailable as exc:
                attempts.append(Attempt(source.name, str(exc)))
                continue
            if found is None:
                attempts.append(Attempt(source.name, "not_covered"))
                continue
            attempts.append(Attempt(source.name, f"{len(found)} found"))
            hits.extend(found)
        hits.sort(key=lambda h: STANDING_RANK[h.standing])
        return hits[:limit], attempts

    def fetch(self, source_name: str, doc_id: str) -> Judgment | None:
        source = next((s for s in self.sources if s.name == source_name), None)
        if source is None:
            return None
        return source.fetch(doc_id)


def default_research_ladder() -> ResearchLadder:
    sources: list = []
    folder = os.getenv("MANU_JUDGMENTS_DIR")
    if folder:
        sources.append(LibrarySource(folder, name="library", standing="licensed"))
    sources.append(IndianKanoonSource())
    return ResearchLadder(sources)
