"""The case record Manu keeps. It is the truth; everything else is a view of it.

The shape follows how a matter actually moves: a case has hearings, a hearing produces
an order, an order imposes obligations on someone by some date. Every fact carries a
`SourceRef` — where it came from and how sure we are — because a diary entry nobody can
trace back to the court is a rumour.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Verification = Literal["verified", "lead", "unverified", "human_confirmed"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceRef(BaseModel):
    """Where one fact came from, precise enough to click through to it."""

    kind: Literal["court_record", "order", "upload", "human"]
    connector: str = ""
    """Which connector produced it (e.g. `ecourts_api`, `fixture`, `human`)."""
    uri: str = ""
    retrieved_at: datetime = Field(default_factory=utc_now)
    sha256: str = ""
    page: int | None = None
    span_start: int | None = None
    span_end: int | None = None
    quote: str = ""
    verification: Verification = "unverified"


class Party(BaseModel):
    name: str
    role: Literal["petitioner", "respondent", "complainant", "accused", "state", "appellant", "other"]
    advocate: str = ""


class CustodySpan(BaseModel):
    start: date
    end: date | None = None
    place: str = ""
    source: SourceRef | None = None


class Accused(BaseModel):
    name: str
    gender: Literal["female", "male", "other", "unknown"] = "unknown"
    juvenile: bool = False
    first_offender: bool | None = None
    """None until an antecedent report says so."""
    other_pending_cases: int | None = None
    delay_attributable_days: int = 0
    """Only ever set from an order that records it; see s.479 Explanation."""
    custody: list[CustodySpan] = Field(default_factory=list)

    @property
    def in_custody(self) -> bool:
        return any(span.end is None for span in self.custody)


class Charge(BaseModel):
    text: str
    """As written in the record, e.g. "Sec. 303(2) BNS"."""
    offence_date: date | None = None


class Hearing(BaseModel):
    on: date
    purpose: str = ""
    court: str = ""
    judge: str = ""
    outcome: str = ""
    source: SourceRef | None = None


class OrderRecord(BaseModel):
    on: date
    title: str = ""
    text: str = ""
    """Extracted text; the document itself lives at `source.uri`."""
    next_date: date | None = None
    next_purpose: str = ""
    source: SourceRef


class Obligation(BaseModel):
    """Something an order requires someone to do."""

    id: str
    who: str
    what: str
    due: date | None = None
    status: Literal["open", "done", "dismissed"] = "open"
    source: SourceRef
    """The order, page and words that impose it. Required: an obligation with no source
    is not shown."""


class Note(BaseModel):
    """What a person wrote about the case: what happened in court before the order is
    uploaded, what the client said, what to carry next time. A human fact, sourced to
    the person who wrote it; never mixed up with what the court recorded."""

    id: str
    on: date
    """The court day the note is about."""
    text: str
    author: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    source: SourceRef


class Client(BaseModel):
    """Who the advocate reports to on this case. Entered by a person; Manu uses it only
    to address a draft it never sends."""

    name: str = ""
    source: SourceRef


class Listing(BaseModel):
    """Where a case sits on a cause list: the item number, the court hall, the bench."""

    on: date
    item: str = ""
    """As printed: "14", "14A", "S-3"."""
    court_hall: str = ""
    bench: str = ""
    list_type: str = ""
    """"Regular", "Supplementary", "Advance" — as the court names it."""
    source: SourceRef


Stage = Literal[
    "investigation",
    "pre_charge",
    "charge",
    "evidence",
    "arguments",
    "reserved",
    "disposed",
    "pleadings",
    "unknown",
]


class Case(BaseModel):
    id: str
    cnr: str = ""
    case_number: str = ""
    court: str = ""
    title: str = ""
    """"State v. Aamir Khan" — how the diary names it."""
    case_type: Literal["criminal", "civil", "writ", "other"] = "other"
    stage: Stage = "unknown"
    status: str = ""
    """The court's own status string, verbatim."""
    parties: list[Party] = Field(default_factory=list)
    accused: list[Accused] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    chargesheet_filed_on: date | None = None
    next_date: date | None = None
    next_purpose: str = ""
    hearings: list[Hearing] = Field(default_factory=list)
    orders: list[OrderRecord] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    special_statute: bool = False
    listing: Listing | None = None
    """Position on the cause list for `listing.on`, when a connector carries it."""
    notes: list[Note] = Field(default_factory=list)
    client: Client | None = None
    tracked_by: list[str] = Field(default_factory=list)
    """Who follows this case: advocate ids, a court id, a client."""
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def last_order(self) -> OrderRecord | None:
        return max(self.orders, key=lambda order: order.on) if self.orders else None


EventKind = Literal[
    "tracked",
    "new_order",
    "hearing_date_changed",
    "listed",
    "status_changed",
    "stage_changed",
    "disposed",
    "obligation_found",
    "fetch_failed",
    "brief_prepared",
    "note_added",
    "deadline_added",
]


class CaseEvent(BaseModel):
    """Something that changed. Events are append-only: the diary is their sum."""

    id: str
    case_id: str
    kind: EventKind
    at: datetime = Field(default_factory=utc_now)
    summary: str
    before: str = ""
    after: str = ""
    source: SourceRef | None = None
