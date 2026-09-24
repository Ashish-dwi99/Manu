"""Read an order: when is the case next listed, and who has to do what by when.

This is the deterministic first pass. It finds the sentences an Indian court uses to
direct someone ("the IO is directed to file…", "let reply be filed within two weeks",
"put up on 14.11.2026 for arguments") and turns each into a *candidate* obligation
carrying the exact words and their position in the text.

Every candidate is a `lead`, not a fact, until a person confirms it — the diary shows
it with [Confirm] [Dismiss]. The `order-reader` agent (see `manu/runtime/agents`) may
refine who/what on top of this, but it starts from these spans and has to cite them;
it never adds an obligation this pass cannot point to.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from manu.case_state.models import Obligation, SourceRef
from manu.case_state.store import new_id
from manu.doc_intel import grammars

_NEXT_DATE_CUES = re.compile(
    r"\b(?:list(?:ed)?|re-?list|put\s+up|re-?notify|adjourned\s+to|fixed\s+for|next\s+date|"
    r"NDOH|come\s+up|stands?\s+over\s+to|renotified|posted\s+(?:to|on)|matter\s+on)\b",
    re.IGNORECASE,
)
_PURPOSE = re.compile(
    r"^\W{0,4}(?:at\s+[\d.:]+\s*(?:a\.?m\.?|p\.?m\.?)\s*)?for\s+([A-Za-z][A-Za-z /&-]{2,60}?)(?:[.;,]|$)",
    re.IGNORECASE,
)
_DIRECTIVE = re.compile(
    r"\b(?:(?:is|are|be|stands?)\s+(?:hereby\s+)?directed\s+to|shall\s+(?:file|furnish|produce|deposit|"
    r"appear|submit|serve|place|comply|remain\s+present|pay)|let\s+(?:the\s+)?[a-z ]{2,40}?\s+be\s+"
    r"(?:filed|served|produced|summoned|issued)|(?:issue|issued)\s+(?:notice|summons|warrants?)|"
    r"(?:to|may)\s+file\s+(?:reply|written\s+statement|status\s+report|affidavit|rejoinder|chargesheet))\b",
    re.IGNORECASE,
)
_WITHIN = re.compile(
    r"\bwithin\s+(\d{1,3}|one|two|three|four|six|eight|ten|fifteen|thirty)\s+(day|week|month)s?\b",
    re.IGNORECASE,
)
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "six": 6, "eight": 8, "ten": 10, "fifteen": 15, "thirty": 30}
_BEFORE_NEXT = re.compile(r"\b(?:before|prior\s+to|on\s+or\s+before)\s+the\s+next\s+date\b", re.IGNORECASE)
_ABBREVIATIONS = (
    "Ld",
    "Sh",
    "Smt",
    "No",
    "Nos",
    "Hon'ble",
    "Hon",
    "Mr",
    "Mrs",
    "Ms",
    "Dr",
    "Sr",
    "Jr",
    "Crl",
    "vs",
    "v",
    "u/s",
    "Sec",
    "S",
    "Rs",
    "Addl",
    "Spl",
    "Govt",
    "Insp",
    "SI",
    "ASI",
    "Const",
)


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    start: int
    end: int


@dataclass(slots=True)
class OrderReading:
    next_date: date | None = None
    next_purpose: str = ""
    next_date_quote: str = ""
    obligations: list[Obligation] = field(default_factory=list)
    dates: list[date] = field(default_factory=list)


def sentences(text: str) -> list[Sentence]:
    """Split on sentence ends a court would write, not on "Ld." or "No."."""
    out: list[Sentence] = []
    start = 0
    for match in re.finditer(r"[.;!?](?=\s+[A-Z(\"'0-9]|\s*\n|\s*$)|\n\s*\n", text):
        end = match.end()
        head = text[start : match.start()].rstrip()
        last_word = re.split(r"[\s(]", head)[-1] if head else ""
        if match.group(0) == "." and (
            last_word in _ABBREVIATIONS
            or re.fullmatch(r"[A-Z]", last_word or "")
            or re.fullmatch(r"\d{1,2}", last_word or "")
        ):
            continue
        chunk = text[start:end]
        if chunk.strip():
            lead = len(chunk) - len(chunk.lstrip())
            out.append(Sentence(chunk.strip(), start + lead, end))
        start = end
    tail = text[start:]
    if tail.strip():
        lead = len(tail) - len(tail.lstrip())
        out.append(Sentence(tail.strip(), start + lead, len(text)))
    return out


def _dates_in(text: str) -> list[tuple[date, int, int]]:
    found = []
    for match in grammars.find_dates(text):
        try:
            found.append((date.fromisoformat(match.value), match.start, match.end))
        except ValueError:
            continue
    return found


def _subject(sentence: str, directive: re.Match[str]) -> str:
    """Who the direction is addressed to: the words before the directive verb.

    "Ld. counsel for the accused shall furnish…" → "Ld. counsel for the accused". A
    "let … be summoned" or "issue notice" direction is on the court's own office.
    """
    verb = directive.group(0).lower()
    if verb.startswith(("let ", "issue")):
        return "Court office (process)"
    head = sentence[: directive.start()]
    head = re.sub(
        r"^(?:it\s+is\s+(?:further\s+)?ordered\s+that|accordingly|further|hence|also)[,\s]+",
        "",
        head.strip(),
        flags=re.IGNORECASE,
    )
    head = re.sub(r"^(?:the)\s+", "", head, flags=re.IGNORECASE).strip(" ,.")
    if not head:
        return "Unspecified"
    words = head.split()
    return " ".join(words[-8:]) if len(words) > 8 else head


def _within(sentence: str, order_on: date) -> date | None:
    match = _WITHIN.search(sentence)
    if not match:
        return None
    raw = match.group(1).lower()
    count = int(raw) if raw.isdigit() else _WORDS[raw]
    unit = match.group(2).lower()
    days = count * {"day": 1, "week": 7, "month": 30}[unit]
    return order_on + timedelta(days=days)


def read_order(text: str, *, order_on: date, source: SourceRef) -> OrderReading:
    reading = OrderReading()
    body = text or ""
    reading.dates = sorted({d for d, _, _ in _dates_in(body)})

    for sentence in sentences(body):
        cue = _NEXT_DATE_CUES.search(sentence.text)
        if reading.next_date is None and cue:
            for day, start, end in _dates_in(sentence.text):
                if day > order_on and start >= cue.start() - 40:
                    reading.next_date = day
                    reading.next_date_quote = sentence.text
                    purpose = _PURPOSE.search(sentence.text[end:])
                    if purpose:
                        reading.next_purpose = purpose.group(1).strip().lower()
                    break

    for sentence in sentences(body):
        directive = _DIRECTIVE.search(sentence.text)
        if not directive:
            continue
        due = None
        dated = [d for d, _, _ in _dates_in(sentence.text) if d > order_on]
        if dated:
            due = dated[0]
        elif (within := _within(sentence.text, order_on)) is not None:
            due = within
        elif _BEFORE_NEXT.search(sentence.text) or (reading.next_date and "next date" in sentence.text.lower()):
            due = reading.next_date
        reading.obligations.append(
            Obligation(
                id=new_id("obl"),
                who=_subject(sentence.text, directive),
                what=sentence.text,
                due=due,
                source=source.model_copy(
                    update={
                        "span_start": sentence.start,
                        "span_end": sentence.end,
                        "quote": sentence.text[:400],
                        "verification": "lead",
                    }
                ),
            )
        )
    return reading
