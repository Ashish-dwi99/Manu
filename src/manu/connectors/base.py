"""How Manu reads a court: a ladder of connectors, most official first.

    1. official API          — eCourts Open API / NJDG / a High Court's own service
    2. official public data  — downloadable cause lists, published orders
    3. browser               — the public portal, driven by the Chotu runtime's page tool
    4. human                 — ask a person (clerk, advocate) to fetch it

A connector says one of three things: here is the record, this court is not something I
cover (`None`), or I cover it but failed right now (`ConnectorUnavailable`). The ladder
moves down on either of the last two and records every attempt, so the diary can say
*how* it knows what it shows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import IntEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class Tier(IntEnum):
    OFFICIAL_API = 1
    OFFICIAL_PUBLIC_DATA = 2
    BROWSER = 3
    HUMAN = 4


class ConnectorUnavailable(RuntimeError):
    """The connector covers this case but could not answer now."""


class CourtOrder(BaseModel):
    on: date
    title: str = ""
    uri: str = ""
    text: str = ""
    sha256: str = ""


class CourtHearing(BaseModel):
    on: date
    purpose: str = ""
    business: str = ""
    judge: str = ""


class CourtListing(BaseModel):
    """A case's place on a published cause list."""

    on: date
    item: str = ""
    court_hall: str = ""
    bench: str = ""
    list_type: str = ""


class BoardStatus(BaseModel):
    """What a court's display board shows right now."""

    court: str
    court_hall: str = ""
    state: Literal["in_session", "not_started", "risen", "unknown"] = "unknown"
    current_item: str = ""
    as_of: datetime
    note: str = ""


class CaseHit(BaseModel):
    """A case a search found, before anyone follows it."""

    cnr: str
    title: str = ""
    case_number: str = ""
    court: str = ""
    next_date: date | None = None
    advocate: str = ""
    """The advocate name as the court record prints it."""


class CourtRecord(BaseModel):
    """What a court says about one case, normalised across connectors."""

    cnr: str
    case_number: str = ""
    court: str = ""
    title: str = ""
    status: str = ""
    stage: str = ""
    next_date: date | None = None
    next_purpose: str = ""
    disposed: bool = False
    disposal: str = ""
    hearings: list[CourtHearing] = Field(default_factory=list)
    orders: list[CourtOrder] = Field(default_factory=list)
    listing: CourtListing | None = None
    raw: dict = Field(default_factory=dict)


class Connector(Protocol):
    name: str
    tier: Tier

    def fetch(self, cnr: str) -> CourtRecord | None: ...


# Two optional capabilities. A connector that has them defines
#   board(court: str, court_hall: str) -> BoardStatus | None
#   search_advocate(name: str) -> list[CaseHit] | None
# with the same three answers as `fetch`: a result, `None` (not covered), or
# `ConnectorUnavailable`.


@dataclass(slots=True)
class Attempt:
    connector: str
    tier: Tier
    outcome: str
    """`ok`, `not_covered`, or the failure message."""


@dataclass(slots=True)
class FetchResult:
    record: CourtRecord | None
    connector: str = ""
    tier: Tier | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    attempts: list[Attempt] = field(default_factory=list)


class ConnectorLadder:
    def __init__(self, connectors: list[Connector]) -> None:
        self.connectors = sorted(connectors, key=lambda c: c.tier)

    def fetch(self, cnr: str) -> FetchResult:
        result = FetchResult(record=None)
        for connector in self.connectors:
            try:
                record = connector.fetch(cnr)
            except ConnectorUnavailable as exc:
                result.attempts.append(Attempt(connector.name, connector.tier, str(exc) or "unavailable"))
                continue
            if record is None:
                result.attempts.append(Attempt(connector.name, connector.tier, "not_covered"))
                continue
            result.attempts.append(Attempt(connector.name, connector.tier, "ok"))
            result.record = record
            result.connector = connector.name
            result.tier = connector.tier
            return result
        return result

    def _first(self, capability: str, *args) -> tuple[object | None, str, Tier | None, list[Attempt]]:
        attempts: list[Attempt] = []
        for connector in self.connectors:
            method = getattr(connector, capability, None)
            if method is None:
                continue
            try:
                answer = method(*args)
            except ConnectorUnavailable as exc:
                attempts.append(Attempt(connector.name, connector.tier, str(exc) or "unavailable"))
                continue
            if answer is None:
                attempts.append(Attempt(connector.name, connector.tier, "not_covered"))
                continue
            attempts.append(Attempt(connector.name, connector.tier, "ok"))
            return answer, connector.name, connector.tier, attempts
        return None, "", None, attempts

    def board(self, court: str, court_hall: str = "") -> tuple[BoardStatus | None, str, list[Attempt]]:
        """The display board for one court, from the most official connector that has it."""
        status, name, _tier, attempts = self._first("board", court, court_hall)
        return status, name, attempts  # type: ignore[return-value]

    def search_advocate(self, name: str) -> tuple[list[CaseHit], str, list[Attempt]]:
        """Cases where `name` appears as an advocate, from the first connector that can search."""
        hits, connector, _tier, attempts = self._first("search_advocate", name)
        return list(hits or []), connector, attempts  # type: ignore[arg-type]
