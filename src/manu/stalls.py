"""Stall signals: what the record itself says about a case that is not moving.

Everything here is deterministic arithmetic over the case record — hearings, orders,
directions and dates. No model is involved, and no signal is a conclusion:

* A repeated listing is not, by itself, an adjournment.
* A gap in the record is not proof that nothing happened.
* A direction still open is a fact; whose fault it is, the record does not say.

Every signal carries the evidence it stands on, so the advocate can check it in one
glance and act or tuck it away. Signals are recomputed from the record on every read.
Dismissing one lasts until its evidence changes: the identifier is derived from the
evidence itself, so a new hearing or a new order revives the signal if the stall
continues. Nothing here predicts outcomes, measures the court, or assigns blame.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from manu.case_state.models import Case, Hearing, Obligation, SourceRef

# Heuristics, not law. They exist to say "worth a look", never "something is wrong".
REPEAT_RUN = 3  # this many consecutive dates for the same business is worth a look
REPEAT_STRONG = 4  # this many is worth real attention
ORDER_LOOKBACK = 4  # hearings considered when checking for missing orders
MISSING_ORDERS = 2  # this many hearings without an order on record is a gap
QUIET_DAYS = 60  # nothing recorded for this long, on a pending case with no date
DIRECTION_HORIZON_DAYS = 14  # an open direction with the hearing this close needs prep

ATTENTION = "attention"
WATCH = "watch"


@dataclass(slots=True)
class Evidence:
    """One fact a signal stands on: a hearing, an order, a direction, or the record."""

    label: str
    quote: str = ""
    source: SourceRef | None = None

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "quote": self.quote,
            "source": _source_dict(self.source) if self.source else None,
        }


@dataclass(slots=True)
class Signal:
    kind: str
    tone: str
    title: str
    """A factual statement about the record, with dates in ISO form for the UI to render."""
    detail: str
    """What the signal is, and — just as plainly — what it is not."""
    evidence: list[Evidence] = field(default_factory=list)
    action: str = ""
    """A proposed next step the advocate can confirm into their to-do list. A draft,
    never done by Manu itself."""
    id: str = ""
    dismissed: bool = False

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "tone": self.tone,
            "title": self.title,
            "detail": self.detail,
            "evidence": [e.as_dict() for e in self.evidence],
            "action": self.action,
            "dismissed": self.dismissed,
        }


def _source_dict(source: SourceRef) -> dict:
    return {
        "kind": source.kind,
        "connector": source.connector,
        "uri": source.uri,
        "quote": source.quote,
        "page": source.page,
        "span": [source.span_start, source.span_end],
        "verification": source.verification,
    }


def _signal_id(case: Case, kind: str, anchor: str) -> str:
    digest = hashlib.sha1(f"{case.id}:{kind}:{anchor}".encode()).hexdigest()
    return f"sig_{digest[:12]}"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower()).rstrip(".,;")


def _hearing_evidence(hearing: Hearing) -> Evidence:
    # Origin first, always: the business quoted is the hearing's recorded entry, never
    # an order's words — for a hearing whose order is missing, no order text exists.
    label = f"Hearing · {hearing.on.isoformat()}"
    if hearing.purpose:
        label += f" · {hearing.purpose}"
    return Evidence(label=label, quote=hearing.outcome, source=hearing.source)


def signals(case: Case, as_of: date) -> list[Signal]:
    """Every stall signal the record supports, dismissed ones marked, stable order."""
    if case.stage == "disposed":
        return []
    found: list[Signal] = []
    hearings = sorted(case.hearings, key=lambda h: h.on)
    open_directions = [o for o in case.obligations if o.status == "open"]

    for build in (
        _repeated_listing,
        _directions_waiting,
        _record_conflict,
        _orders_missing,
        _quiet_or_undated,
    ):
        signal = build(case, hearings, open_directions, as_of)
        if signal:
            found.append(signal)

    for signal in found:
        signal.dismissed = signal.id in case.dismissed_signals
    found.sort(key=lambda s: (s.tone != ATTENTION, s.kind))
    return found


def _repeated_listing(case: Case, hearings: list[Hearing], _: list[Obligation], as_of: date) -> Signal | None:
    run: list[Hearing] = []
    for hearing in reversed(hearings):
        if not hearing.purpose.strip():
            break
        if run and _norm(hearing.purpose) != _norm(run[-1].purpose):
            break
        run.append(hearing)
    if len(run) < REPEAT_RUN:
        return None
    run.reverse()
    purpose = run[-1].purpose.strip()
    anchor = f"{_norm(purpose)}:{run[0].on.isoformat()}"
    signal = Signal(
        id=_signal_id(case, "repeated_listing", anchor),
        kind="repeated_listing",
        tone=ATTENTION if len(run) >= REPEAT_STRONG else WATCH,
        title=f"Listed for “{purpose}” on the last {len(run)} dates",
        detail=(
            "The record does not say why each date was needed. A repeated listing is not, by itself, an "
            "adjournment — and it says nothing about who asked for the time. What it does say is that the "
            "same business has been before the court "
            f"{len(run)} times, so the next date is worth preparing to finish."
        ),
        evidence=[_hearing_evidence(h) for h in run],
    )
    if case.next_date:
        signal.action = (
            f"Read the last order, list what must happen before the hearing on "
            f"{case.next_date.isoformat()}, and prepare it"
        )
    else:
        signal.action = f"Confirm from the court file what “{purpose}” still needs, and note it"
    return signal


def _directions_waiting(case: Case, hearings: list[Hearing], open_directions: list[Obligation], as_of: date) -> Signal | None:
    # Next steps the advocate accepted from a signal are their own to-dos, not the
    # court's directions; they live in the To do list and never re-signal here.
    open_directions = [o for o in open_directions if o.source.connector != "manu"]
    overdue = [o for o in open_directions if o.due and o.due < as_of]
    horizon = case.next_date if case.next_date else None
    before_hearing = [
        o
        for o in open_directions
        if o not in overdue
        and o.due
        and horizon
        and o.due <= horizon
        and (horizon - as_of).days <= DIRECTION_HORIZON_DAYS
    ]
    if not overdue and not before_hearing:
        return None
    parts = []
    if overdue:
        parts.append(f"{len(overdue)} direction{'s' if len(overdue) != 1 else ''} past its date")
    if before_hearing:
        parts.append(
            f"{len(before_hearing)} still open with the hearing on {horizon.isoformat()}"
        )
    signal = Signal(
        kind="directions_waiting",
        tone=ATTENTION if overdue else WATCH,
        title="; ".join(parts),
        detail=(
            "Each direction below quotes the order it came from. Whether the time was enough, or the "
            "delay excusable, is for the advocate and the court — Manu only keeps the obligation visible "
            "so it is done before the date, not remembered after it."
        ),
        evidence=[
            Evidence(
                label=f"Direction · {o.who}" + (f" · due {o.due.isoformat()}" if o.due else ""),
                quote=o.source.quote or o.what,
                source=o.source,
            )
            for o in [*overdue, *before_hearing]
        ],
    )
    anchor = ",".join(sorted(o.id for o in [*overdue, *before_hearing]))
    signal.id = _signal_id(case, "directions_waiting", anchor)
    return signal


def _record_conflict(case: Case, hearings: list[Hearing], _: list[Obligation], as_of: date) -> Signal | None:
    order = case.last_order
    if order is None or order.next_date is None:
        return None
    if any(h.on > order.on for h in hearings):
        return None  # a later hearing means the order's date has run its course
    if case.next_date == order.next_date:
        return None
    listed = case.next_date.isoformat() if case.next_date else "no date"
    fixed = order.next_date.isoformat()
    return Signal(
        id=_signal_id(case, "record_conflict", f"{order.on.isoformat()}:{fixed}:{listed}"),
        kind="record_conflict",
        tone=ATTENTION,
        title=f"The last order fixes {fixed}; the record lists {listed}",
        detail=(
            "The date may have been moved by a cause-list change Manu cannot trace to an order, or the "
            "record may be wrong. Working to the wrong date is how a matter is heard without you — "
            "confirm which date stands before relying on either."
        ),
        evidence=[
            Evidence(label=f"Order dated {order.on.isoformat()} · put up on {fixed}", source=order.source),
            Evidence(label=f"Court record · next date {listed}"),
        ],
        action="Confirm the correct next date from the court's own portal or the court reader",
    )


def _orders_missing(case: Case, hearings: list[Hearing], _: list[Obligation], as_of: date) -> Signal | None:
    recent = hearings[-ORDER_LOOKBACK:]
    if len(recent) < MISSING_ORDERS:
        return None
    order_dates = {o.on for o in case.orders}
    missing = [h for h in recent if h.on not in order_dates]
    if len(missing) < MISSING_ORDERS:
        return None
    anchor = ",".join(h.on.isoformat() for h in missing)
    return Signal(
        id=_signal_id(case, "orders_missing", anchor),
        kind="orders_missing",
        tone=WATCH,
        title=f"No order on record for {len(missing)} of the last {len(recent)} dates",
        detail=(
            "Orders may exist that Manu has not read. What is missing from the record is not evidence of "
            "what happened in court — but until the orders are here, directions in them cannot be "
            "tracked, and the diary can only show what it holds."
        ),
        evidence=[_hearing_evidence(h) for h in missing],
        action="Upload the missing orders, or confirm from the court file what was ordered on each date",
    )


def _quiet_or_undated(case: Case, hearings: list[Hearing], _: list[Obligation], as_of: date) -> Signal | None:
    if case.next_date is not None:
        return None
    recorded = [h.on for h in hearings] + [o.on for o in case.orders]
    last = max(recorded) if recorded else None
    if last is not None and (as_of - last).days >= QUIET_DAYS:
        return Signal(
            id=_signal_id(case, "quiet_record", last.isoformat()),
            kind="quiet_record",
            tone=ATTENTION,
            title=f"Nothing on record since {last.isoformat()}",
            detail=(
                "No hearing or order is recorded in all that time, and no next date is listed. A gap in "
                "what Manu holds is not proof the court did nothing — but a case with no date and no "
                "record movement needs someone to ask after it."
            ),
            evidence=[Evidence(label=f"Record · last activity {last.isoformat()}")],
            action="Confirm the current position from the court file or the court's own portal",
        )
    return Signal(
        id=_signal_id(case, "awaiting_date", last.isoformat() if last else "none"),
        kind="awaiting_date",
        tone=WATCH,
        title="No next date in the record",
        detail=(
            "The case is shown as pending but no date is listed. The court may not have published one "
            "yet, or the record may be behind — Manu does not know which."
        ),
        evidence=[Evidence(label=f"Record · last activity {last.isoformat()}")] if last else [],
        action="Ask the court reader or check the court's own portal for the next date",
    )
