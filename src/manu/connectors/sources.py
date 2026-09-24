"""The connectors Manu ships with.

`FixtureConnector` reads JSON court records from a directory. It powers the demo, the
tests, and — pointed at a folder a clerk keeps — the human tier.

`ECourtsOpenApiConnector` is the tier-1 slot. eCourts exposes an Open API to onboarded
institutional litigants; access is granted per institution, so this connector reports
itself unavailable until `MANU_ECOURTS_API_BASE` and `MANU_ECOURTS_API_TOKEN` are set.
It does not scrape.

`DemoConnector` also answers the two optional capabilities for the demo court: advocate
search over its fixtures, and a display board that advances through the day by a fixed
timetable. The board is a simulation and is labelled `via demo` wherever it is shown.

`BrowserPortalConnector` is the tier-3 slot. It will run a Kimi turn with the page tool
against the public portal (services.ecourts.gov.in); captchas and consent screens go to
a human through the runtime's approval path. Until that agent spec ships it reports
itself unavailable, so the ladder falls through honestly.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from manu.connectors.base import BoardStatus, CaseHit, ConnectorUnavailable, CourtRecord, Tier


class FixtureConnector:
    name = "fixture"

    def __init__(self, root: str | Path, *, tier: Tier = Tier.OFFICIAL_PUBLIC_DATA) -> None:
        self.root = Path(root)
        self.tier = tier

    def fetch(self, cnr: str) -> CourtRecord | None:
        path = self.root / f"{cnr}.json"
        if not path.is_file():
            return None
        try:
            return CourtRecord.model_validate(json.loads(path.read_text()))
        except (OSError, ValueError) as exc:
            raise ConnectorUnavailable(f"fixture {path.name} unreadable: {exc}") from exc


_RELATIVE = re.compile(r"^@([+-]\d+)$")
_INLINE = re.compile(r"\{@([+-]\d+)\}")


def _resolve_relative(value: Any, today: date) -> Any:
    if isinstance(value, str):
        match = _RELATIVE.match(value)
        if match:
            return (today + timedelta(days=int(match.group(1)))).isoformat()
        # Inside prose (an order's text) a date is written the way courts write it.
        return _INLINE.sub(lambda m: (today + timedelta(days=int(m.group(1)))).strftime("%d.%m.%Y"), value)
    if isinstance(value, list):
        return [_resolve_relative(v, today) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_relative(v, today) for k, v in value.items()}
    return value


class DemoConnector(FixtureConnector):
    """Fixtures whose dates are written relative to today ("@-14", "@+3"), so the demo
    diary is always current. Demo only; never registered outside `manu demo`."""

    name = "demo"

    def __init__(self, root: str | Path, *, today: date | None = None) -> None:
        super().__init__(root)
        self.today = today or date.today()

    def fetch(self, cnr: str) -> CourtRecord | None:
        path = self.root / f"{cnr}.json"
        if not path.is_file():
            return None
        return CourtRecord.model_validate(_resolve_relative(json.loads(path.read_text()), self.today))

    def search_advocate(self, name: str) -> list[CaseHit] | None:
        wanted = _name_key(name)
        if len(wanted) < 3:
            return []
        hits: list[CaseHit] = []
        for path in sorted(self.root.glob("*.json")):
            record = self.fetch(path.stem)
            if record is None:
                continue
            parties = (record.raw.get("particulars") or {}).get("parties") or []
            advocate = next((p.get("advocate", "") for p in parties if wanted in _name_key(p.get("advocate", ""))), "")
            if advocate:
                hits.append(
                    CaseHit(
                        cnr=record.cnr,
                        title=record.title,
                        case_number=record.case_number,
                        court=record.court,
                        next_date=record.next_date,
                        advocate=advocate,
                    )
                )
        return hits

    def board(self, court: str, court_hall: str = "", *, now: datetime | None = None) -> BoardStatus | None:
        path = self.root.parent / "boards.json"
        if not path.is_file():
            return None
        boards = json.loads(path.read_text())
        spec = boards.get(court)
        if spec is None:
            return None
        status = _simulated_board(court, court_hall or spec.get("court_hall", ""), spec, now or _demo_now())
        if now is None:
            status.as_of = datetime.now(UTC)  # when it was read, even on a fixed demo clock
        return status


def _name_key(name: str) -> str:
    return re.sub(r"[^a-z]", "", (name or "").lower())


_IST = timedelta(hours=5, minutes=30)


def _demo_now() -> datetime:
    """Wall-clock time, or a fixed India time of day from `MANU_DEMO_BOARD_AT` ("11:42"),
    so the demo board can be shown mid-session at any hour."""
    now = datetime.now(UTC)
    fixed = os.getenv("MANU_DEMO_BOARD_AT", "").strip()
    if not fixed:
        return now
    local_day = (now + _IST).date()
    return datetime.combine(local_day, time.fromisoformat(fixed), tzinfo=UTC) - _IST


def _simulated_board(court: str, court_hall: str, spec: dict, now: datetime) -> BoardStatus:
    """The demo court's board: items called at a steady pace from the sitting time,
    paused for lunch, until the court rises."""
    local = (now + _IST).replace(tzinfo=None)
    start = datetime.combine(local.date(), time.fromisoformat(spec.get("sits", "10:30")))
    lunch_from = datetime.combine(local.date(), time.fromisoformat(spec.get("lunch_from", "13:30")))
    lunch_to = datetime.combine(local.date(), time.fromisoformat(spec.get("lunch_to", "14:00")))
    rises = datetime.combine(local.date(), time.fromisoformat(spec.get("rises", "16:30")))
    pace = max(1, int(spec.get("minutes_per_item", 8)))
    last = int(spec.get("items", 40))
    base = dict(court=court, court_hall=court_hall, as_of=now)
    if local.weekday() == 6:
        return BoardStatus(**base, state="risen", note="Court closed on Sunday.")
    if local < start:
        return BoardStatus(**base, state="not_started", note=f"Sits at {spec.get('sits', '10:30')}.")
    if local >= rises:
        return BoardStatus(**base, state="risen", note="Court has risen for the day.")
    minutes = (min(local, lunch_from) - start).total_seconds() / 60
    if local >= lunch_to:
        minutes += (local - lunch_to).total_seconds() / 60
    item = min(last, 1 + int(minutes // pace))
    if lunch_from <= local < lunch_to:
        return BoardStatus(**base, state="in_session", current_item=str(item), note="Lunch; resumes at 2:00.")
    return BoardStatus(**base, state="in_session", current_item=str(item))


class ECourtsOpenApiConnector:
    name = "ecourts_api"
    tier = Tier.OFFICIAL_API

    def __init__(self) -> None:
        self.base = os.getenv("MANU_ECOURTS_API_BASE", "").rstrip("/")
        self.token = os.getenv("MANU_ECOURTS_API_TOKEN", "")

    def fetch(self, cnr: str) -> CourtRecord | None:
        if not (self.base and self.token):
            raise ConnectorUnavailable("eCourts Open API not configured for this installation")
        raise ConnectorUnavailable("eCourts Open API client not implemented yet")


class BrowserPortalConnector:
    name = "ecourts_portal_browser"
    tier = Tier.BROWSER

    def fetch(self, cnr: str) -> CourtRecord | None:
        raise ConnectorUnavailable("portal browser agent not enabled")
