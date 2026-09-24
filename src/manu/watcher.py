"""The court watcher: fetch every tracked case, notice what changed, read new orders.

Runs every morning (and on demand). For each case:

    fetch through the connector ladder
      → compare with what the diary already holds
      → append one event per change (new order, date moved, disposed…)
      → read each new order for the next date and for obligations
      → save the raw snapshot, so the change can be re-derived and audited

This part is deterministic on purpose. The model is not needed to see that a date moved.
It is needed to read an order well, and that happens in `orders.read_order` first and the
`order-reader` agent second, both anchored to the order's own words.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from manu.case_state.models import Accused, Case, CaseEvent, Charge, Hearing, Listing, OrderRecord, Party, SourceRef
from manu.case_state.store import CaseStore, new_id
from manu.clock import india_today
from manu.connectors.base import ConnectorLadder, CourtOrder, CourtRecord, FetchResult, Tier
from manu.orders import read_order

_TIER_VERIFICATION = {
    Tier.OFFICIAL_API: "verified",
    Tier.OFFICIAL_PUBLIC_DATA: "verified",
    Tier.BROWSER: "verified",
    Tier.HUMAN: "human_confirmed",
}


def _order_key(order: CourtOrder | OrderRecord) -> str:
    """Identity of an order across fetches: its date plus the digest of its content.

    Both sides must derive the digest the same way — a stored order keeps the digest it
    was given or the one computed from its text — or every watch re-announces old orders.
    """
    if isinstance(order, CourtOrder):
        return f"{order.on.isoformat()}|{order.sha256 or _digest(order.text) or order.uri or order.title}"
    return f"{order.on.isoformat()}|{order.source.sha256 or order.source.uri or order.title}"


def _source(fetch: FetchResult, *, kind: str = "court_record", uri: str = "", sha256: str = "") -> SourceRef:
    return SourceRef(
        kind=kind,  # type: ignore[arg-type]
        connector=fetch.connector,
        uri=uri,
        retrieved_at=fetch.fetched_at,
        sha256=sha256,
        verification=_TIER_VERIFICATION.get(fetch.tier, "unverified") if fetch.tier else "unverified",  # type: ignore[arg-type]
    )


def apply_record(case: Case, fetch: FetchResult, *, read_old_orders: bool = False) -> list[CaseEvent]:
    """Bring `case` up to date with `fetch.record`, returning what changed.

    `read_old_orders` is False after the first sync: obligations from orders the diary
    had already seen were already offered to the user, and re-offering dismissed ones
    would teach them to ignore the diary.
    """
    record = fetch.record
    assert record is not None
    # The first sync is not news: everything in it was already true before the diary
    # knew the case. It is summarised in one `tracked` event by the caller, and only
    # later syncs produce change events.
    first_sync = not case.orders and not case.status and case.next_date is None
    events: list[CaseEvent] = []
    record_source = _source(fetch)

    def event(kind: str, summary: str, *, before: str = "", after: str = "", source: SourceRef | None = None) -> None:
        if first_sync:
            return
        events.append(
            CaseEvent(
                id=new_id("evt"),
                case_id=case.id,
                kind=kind,  # type: ignore[arg-type]
                summary=summary,
                before=before,
                after=after,
                source=source or record_source,
            )
        )

    _apply_particulars(case, record, record_source)
    for attr in ("case_number", "court", "title"):
        value = getattr(record, attr)
        if value and not getattr(case, attr):
            setattr(case, attr, value)

    if record.status and record.status != case.status:
        if case.status:
            event("status_changed", f"Status changed to “{record.status}”.", before=case.status, after=record.status)
        case.status = record.status
    if record.stage and record.stage != case.stage and record.stage in Case.model_fields["stage"].annotation.__args__:  # type: ignore[union-attr]
        if case.stage != "unknown":
            event("stage_changed", f"Stage moved to {record.stage}.", before=case.stage, after=record.stage)
        case.stage = record.stage  # type: ignore[assignment]

    if record.next_date != case.next_date or (record.next_purpose and record.next_purpose != case.next_purpose):
        before = f"{case.next_date.isoformat() if case.next_date else '—'} {case.next_purpose}".strip()
        after = f"{record.next_date.isoformat() if record.next_date else '—'} {record.next_purpose}".strip()
        if case.next_date is None and record.next_date is not None:
            event(
                "listed",
                f"Listed on {record.next_date.isoformat()}"
                + (f" for {record.next_purpose}." if record.next_purpose else "."),
                after=after,
            )
        elif record.next_date != case.next_date:
            event("hearing_date_changed", f"Next date moved from {before} to {after}.", before=before, after=after)
        case.next_date = record.next_date
        case.next_purpose = record.next_purpose or case.next_purpose

    # The cause-list position is today's fact, not history: it follows the record, and
    # it is dropped once the date it was printed for has passed.
    if record.listing is not None:
        case.listing = Listing(**record.listing.model_dump(), source=record_source)
    elif case.listing is not None and case.listing.on != case.next_date:
        case.listing = None

    seen = {_order_key(order) for order in case.orders}
    new_orders = sorted((o for o in record.orders if _order_key(o) not in seen), key=lambda o: o.on)
    latest_on = max((o.on for o in record.orders), default=None)
    for order in new_orders:
        source = _source(fetch, kind="order", uri=order.uri, sha256=order.sha256 or _digest(order.text))
        stored = OrderRecord(on=order.on, title=order.title, text=order.text, source=source)
        case.orders.append(stored)
        if not (first_sync and not read_old_orders and order.on != latest_on):
            reading = read_order(order.text, order_on=order.on, source=source)
            stored.next_date = reading.next_date
            stored.next_purpose = reading.next_purpose
            for obligation in reading.obligations:
                case.obligations.append(obligation)
                event(
                    "obligation_found",
                    f"{obligation.who}: {obligation.what}",
                    after=obligation.due.isoformat() if obligation.due else "",
                    source=obligation.source,
                )
        if not first_sync:
            event(
                "new_order",
                f"New order dated {order.on.isoformat()}" + (f": {order.title}." if order.title else "."),
                source=source,
            )

    known_hearings = {(h.on, h.purpose) for h in case.hearings}
    for hearing in record.hearings:
        if (hearing.on, hearing.purpose) not in known_hearings:
            case.hearings.append(
                Hearing(
                    on=hearing.on,
                    purpose=hearing.purpose,
                    judge=hearing.judge,
                    outcome=hearing.business,
                    source=record_source,
                )
            )
    case.hearings.sort(key=lambda h: h.on)

    if record.disposed and case.stage != "disposed":
        event("disposed", f"Case disposed{': ' + record.disposal if record.disposal else ''}.")
        case.stage = "disposed"
        case.next_date = None

    case.updated_at = datetime.now(UTC)
    return events


def _apply_particulars(case: Case, record: CourtRecord, source: SourceRef) -> None:
    """Parties, accused, charges and custody, when the connector carries them.

    Criminal particulars come from the FIR, chargesheet and prison records rather than
    the case-status page. A connector that has them puts them under `raw["particulars"]`.
    They fill empty fields only: once a person has corrected a particular in the diary,
    a later fetch does not overwrite it.
    """
    particulars = record.raw.get("particulars") if isinstance(record.raw, dict) else None
    if not isinstance(particulars, dict):
        return
    if particulars.get("case_type") and case.case_type == "other":
        case.case_type = particulars["case_type"]
    if not case.parties and particulars.get("parties"):
        case.parties = [Party.model_validate(p) for p in particulars["parties"]]
    if not case.charges and particulars.get("charges"):
        case.charges = [Charge.model_validate(c) for c in particulars["charges"]]
    if not case.accused and particulars.get("accused"):
        accused = [Accused.model_validate(a) for a in particulars["accused"]]
        for person in accused:
            for span in person.custody:
                span.source = span.source or source
        case.accused = accused
    if case.chargesheet_filed_on is None and particulars.get("chargesheet_filed_on"):
        case.chargesheet_filed_on = date.fromisoformat(particulars["chargesheet_filed_on"])
    if particulars.get("special_statute"):
        case.special_statute = True


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest() if text else ""


@dataclass(slots=True)
class WatchReport:
    checked: int = 0
    changed: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    events: list[CaseEvent] = field(default_factory=list)


class CourtWatcher:
    def __init__(self, store: CaseStore, ladder: ConnectorLadder, *, today: Callable[[], date] = india_today) -> None:
        self.store = store
        self.ladder = ladder
        self.today = today

    def track(self, cnr: str, *, tracked_by: str = "") -> tuple[Case, list[CaseEvent]]:
        """Start following a case by CNR. Idempotent: tracking twice adds a follower."""
        cnr = cnr.strip().upper().replace("-", "")
        case = self.store.by_cnr(cnr)
        events: list[CaseEvent] = []
        if case is None:
            case = Case(id=new_id("case"), cnr=cnr)
            synced = self._sync(case)
            failed = [e for e in synced if e.kind == "fetch_failed"]
            events.append(CaseEvent(id=new_id("evt"), case_id=case.id, kind="tracked", summary=_tracked_summary(case)))
            events += failed
        else:
            events += self._sync(case)
        if tracked_by and tracked_by not in case.tracked_by:
            case.tracked_by.append(tracked_by)
        self.store.put(case)
        self.store.append(events)
        return case, events

    def run(self, case_ids: list[str] | None = None) -> WatchReport:
        report = WatchReport()
        cases = [c for c in (self.store.get(i) for i in case_ids) if c] if case_ids else self.store.all()
        for case in cases:
            if case.stage == "disposed" or not case.cnr:
                continue
            report.checked += 1
            events = self._sync(case)
            failed = [e for e in events if e.kind == "fetch_failed"]
            if failed:
                report.failed[case.id] = failed[0].summary
            elif events:
                report.changed.append(case.id)
            self.store.put(case)
            self.store.append(events)
            report.events.extend(events)
        return report

    def _sync(self, case: Case) -> list[CaseEvent]:
        fetch = self.ladder.fetch(case.cnr)
        if fetch.record is None:
            tried = "; ".join(f"{a.connector}: {a.outcome}" for a in fetch.attempts) or "no connectors"
            return [
                CaseEvent(
                    id=new_id("evt"),
                    case_id=case.id,
                    kind="fetch_failed",
                    summary=f"Could not read the court record ({tried}).",
                )
            ]
        self.store.save_snapshot(
            case.id, fetch.connector, fetch.fetched_at.isoformat(), fetch.record.model_dump(mode="json")
        )
        return apply_record(case, fetch)


def _tracked_summary(case: Case) -> str:
    parts = [f"Now following {case.cnr}"]
    if case.next_date:
        parts.append(
            f"listed {case.next_date.isoformat()}" + (f" for {case.next_purpose}" if case.next_purpose else "")
        )
    if case.orders:
        parts.append(f"{len(case.orders)} order(s) on record")
    open_obligations = sum(1 for o in case.obligations if o.status == "open")
    if open_obligations:
        parts.append(f"{open_obligations} direction(s) from the latest order to confirm")
    return "; ".join(parts) + "."


def record_from_case(case: Case) -> CourtRecord:
    """The court record a case implies — for tests and for seeding fixtures."""
    return CourtRecord(
        cnr=case.cnr,
        case_number=case.case_number,
        court=case.court,
        title=case.title,
        status=case.status,
        stage=case.stage,
        next_date=case.next_date,
        next_purpose=case.next_purpose,
        orders=[
            CourtOrder(on=o.on, title=o.title, uri=o.source.uri, text=o.text, sha256=o.source.sha256)
            for o in case.orders
        ],
    )
