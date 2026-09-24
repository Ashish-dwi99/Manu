"""The diary: what Manu shows. Three views over the same case record.

* **Day** — every case listed on a date, what it is listed for, what happened last time,
  what is due, and what changed since yesterday. An advocate's diary and a judge's cause
  list are the same page: one record, one view, liberty labels for everyone.
* **Changes** — the feed of events across all cases, newest first.
* **Case** — one case in full: header, last order, open obligations with their source,
  timeline, and (for criminal matters) the statutory arithmetic with its working.
"""

from __future__ import annotations

from datetime import date, timedelta

from manu import judge
from manu.case_state.models import Case, CaseEvent, Client, Note, Obligation, SourceRef
from manu.case_state.store import CaseStore, new_id
from manu.law import limitation


def _obligation(o: Obligation) -> dict:
    return {
        "id": o.id,
        "who": o.who,
        "what": o.what,
        "due": o.due.isoformat() if o.due else None,
        "status": o.status,
        "source": {
            "kind": o.source.kind,
            "connector": o.source.connector,
            "uri": o.source.uri,
            "quote": o.source.quote,
            "page": o.source.page,
            "span": [o.source.span_start, o.source.span_end],
            "verification": o.source.verification,
        },
    }


def _note(n: Note) -> dict:
    return {
        "id": n.id,
        "on": n.on.isoformat(),
        "text": n.text,
        "author": n.author,
        "created_at": n.created_at.isoformat(),
        "source": {"kind": n.source.kind, "connector": n.source.connector, "verification": n.source.verification},
    }


def _client(case: Case) -> dict | None:
    if case.client is None:
        return None
    return {"name": case.client.name, "source": {"kind": case.client.source.kind}}


def set_client(store: CaseStore, case_id: str, name: str) -> dict | None:
    case = store.get(case_id)
    if case is None:
        return None
    case.client = Client(
        name=name.strip(),
        source=SourceRef(kind="human", connector="human", verification="human_confirmed"),
    )
    store.put(case)
    return _client(case)


def _listing(case: Case) -> dict | None:
    listing = case.listing
    if listing is None or listing.on != case.next_date:
        return None
    return {
        "on": listing.on.isoformat(),
        "item": listing.item,
        "court_hall": listing.court_hall,
        "bench": listing.bench,
        "list_type": listing.list_type,
        "source": {"connector": listing.source.connector, "verification": listing.source.verification},
    }


def _event(e: CaseEvent) -> dict:
    return {
        "id": e.id,
        "case_id": e.case_id,
        "kind": e.kind,
        "at": e.at.isoformat(),
        "summary": e.summary,
        "before": e.before,
        "after": e.after,
        "source": {"connector": e.source.connector, "uri": e.source.uri, "verification": e.source.verification}
        if e.source
        else None,
    }


def _last_order(case: Case) -> dict | None:
    order = case.last_order
    if order is None:
        return None
    return {
        "on": order.on.isoformat(),
        "title": order.title,
        "next_date": order.next_date.isoformat() if order.next_date else None,
        "next_purpose": order.next_purpose,
        "excerpt": order.text[:600],
        "source": {"uri": order.source.uri, "sha256": order.source.sha256, "connector": order.source.connector},
    }


def _summary(case: Case, as_of: date) -> dict:
    open_obligations = [o for o in case.obligations if o.status == "open"]
    entry = {
        "id": case.id,
        "cnr": case.cnr,
        "case_number": case.case_number,
        "title": case.title or case.cnr,
        "court": case.court,
        "stage": case.stage,
        "status": case.status,
        "next_date": case.next_date.isoformat() if case.next_date else None,
        "next_purpose": case.next_purpose,
        "last_order": _last_order(case),
        "listing": _listing(case),
        "last_note": _note(max(case.notes, key=lambda n: (n.on, n.created_at))) if case.notes else None,
        "open_obligations": len(open_obligations),
        "overdue_obligations": sum(1 for o in open_obligations if o.due and o.due < as_of),
    }
    assessment = judge.assess_case(case, as_of)
    entry["labels"] = [label.as_dict() for label in judge.labels(case, as_of, assessment)]
    custody = [a.s479.days_detained for a in (assessment.accused if assessment else []) if a.accused.in_custody]
    entry["custody_days"] = max(custody) if custody else None
    return entry


def day(store: CaseStore, on: date) -> dict:
    cases = store.listed_on(on)
    cases.sort(key=lambda c: (c.court, _item_key(c), c.case_number, c.id))
    since = on - timedelta(days=1)
    entries = []
    for serial, case in enumerate(cases, start=1):
        entry = _summary(case, on)
        entry["serial"] = serial
        entry["due_by_today"] = [
            _obligation(o) for o in case.obligations if o.status == "open" and o.due and o.due <= on
        ]
        entry["changed_since"] = [
            _event(e) for e in store.events(case.id, limit=20) if e.at.date() >= since and e.kind not in {"tracked"}
        ]
        entries.append(entry)
    return {"date": on.isoformat(), "count": len(entries), "entries": entries}


def _item_key(case: Case) -> tuple[int, str]:
    """Cause-list order: by item number where the list gives one, numerically."""
    item = case.listing.item if case.listing else ""
    digits = "".join(ch for ch in item if ch.isdigit())
    return (int(digits) if digits else 10**6, item)


def upcoming(store: CaseStore, as_of: date, *, days: int = 7) -> dict:
    horizon = as_of + timedelta(days=days)
    items = []
    for case in store.all():
        for o in case.obligations:
            if o.status == "open" and o.due and o.due <= horizon:
                items.append(
                    {
                        **_obligation(o),
                        "case_id": case.id,
                        "case_title": case.title or case.cnr,
                        "overdue": o.due < as_of,
                    }
                )
        if case.next_date and as_of <= case.next_date <= horizon:
            items.append(
                {
                    "id": f"hearing:{case.id}",
                    "kind": "hearing",
                    "case_id": case.id,
                    "case_title": case.title or case.cnr,
                    "due": case.next_date.isoformat(),
                    "what": f"Hearing — {case.next_purpose or 'purpose not recorded'}",
                    "overdue": False,
                }
            )
    items.sort(key=lambda item: item["due"])
    return {"as_of": as_of.isoformat(), "days": days, "items": items}


def changes(store: CaseStore, *, limit: int = 100) -> dict:
    titles = {case.id: case.title or case.cnr for case in store.all()}
    return {"events": [{**_event(e), "case_title": titles.get(e.case_id, "")} for e in store.events(limit=limit)]}


def case_detail(store: CaseStore, case_id: str, as_of: date) -> dict | None:
    case = store.get(case_id)
    if case is None:
        return None
    detail = _summary(case, as_of)
    detail.update(
        {
            "parties": [p.model_dump() for p in case.parties],
            "charges": [c.text for c in case.charges],
            "obligations": [_obligation(o) for o in case.obligations],
            "orders": [
                {
                    "on": o.on.isoformat(),
                    "title": o.title,
                    "next_date": o.next_date.isoformat() if o.next_date else None,
                    "uri": o.source.uri,
                }
                for o in sorted(case.orders, key=lambda o: o.on, reverse=True)
            ],
            "client": _client(case),
            "notes": [_note(n) for n in sorted(case.notes, key=lambda n: (n.on, n.created_at), reverse=True)],
            "timeline": _timeline(case),
            "events": [_event(e) for e in store.events(case.id, limit=50)],
        }
    )
    assessment = judge.assess_case(case, as_of)
    if assessment is not None:
        detail["criminal"] = {
            "charges": [
                {
                    "raw": c.raw,
                    "offence": c.offence.key if c.offence else None,
                    "title": c.offence.title if c.offence else None,
                    "suggested": c.suggested.key if c.suggested else None,
                    "warnings": list(c.warnings),
                }
                for c in assessment.charges
            ],
            "accused": [
                {
                    "name": a.accused.name,
                    "in_custody": a.accused.in_custody,
                    "s479": {
                        "status": a.s479.status,
                        "days_detained": a.s479.days_detained,
                        "threshold": a.s479.applicable.ratio_label if a.s479.applicable else None,
                        "crossing_date": a.s479.applicable.crossing_date.isoformat() if a.s479.applicable else None,
                        "percent": a.s479.percent_of_applicable,
                        "working": a.s479.working,
                        "flags": a.s479.flags,
                        "gaps": a.s479.gaps,
                    },
                    "default_bail": {
                        "status": a.default_bail.status,
                        "period_days": a.default_bail.period_days,
                        "accrual_date": a.default_bail.accrual_date.isoformat()
                        if a.default_bail.accrual_date
                        else None,
                        "working": a.default_bail.working,
                        "flags": a.default_bail.flags,
                        "gaps": a.default_bail.gaps,
                    },
                }
                for a in assessment.accused
            ],
        }
        detail["bail_facts"] = judge.bail_facts(case, as_of)
    return detail


def order_text(store: CaseStore, case_id: str, on: date) -> dict | None:
    """One order in full, so a quoted direction can be read in place."""
    case = store.get(case_id)
    if case is None:
        return None
    for order in case.orders:
        if order.on == on:
            return {
                "on": order.on.isoformat(),
                "title": order.title,
                "text": order.text,
                "next_date": order.next_date.isoformat() if order.next_date else None,
                "source": {
                    "uri": order.source.uri,
                    "sha256": order.source.sha256,
                    "connector": order.source.connector,
                    "verification": order.source.verification,
                },
            }
    return None


def _timeline(case: Case) -> list[dict]:
    items: list[dict] = []
    for hearing in case.hearings:
        items.append(
            {
                "on": hearing.on.isoformat(),
                "kind": "hearing",
                "label": hearing.purpose or "Hearing",
                "detail": hearing.outcome,
            }
        )
    for order in case.orders:
        items.append(
            {"on": order.on.isoformat(), "kind": "order", "label": order.title or "Order", "detail": order.next_purpose}
        )
    for note in case.notes:
        items.append({"on": note.on.isoformat(), "kind": "note", "label": "Your note", "detail": note.text[:160]})
    if case.chargesheet_filed_on:
        items.append(
            {
                "on": case.chargesheet_filed_on.isoformat(),
                "kind": "chargesheet",
                "label": "Chargesheet filed",
                "detail": "",
            }
        )
    if case.next_date:
        items.append(
            {
                "on": case.next_date.isoformat(),
                "kind": "next",
                "label": f"Next: {case.next_purpose or 'hearing'}",
                "detail": "",
            }
        )
    items.sort(key=lambda item: item["on"])
    return items


def set_obligation_status(store: CaseStore, case_id: str, obligation_id: str, status: str) -> dict | None:
    """A person confirms, completes or dismisses what Manu read. Confirmation upgrades the
    source from `lead` to `human_confirmed`."""
    case = store.get(case_id)
    if case is None:
        return None
    for o in case.obligations:
        if o.id == obligation_id:
            if status == "confirmed":
                o.source.verification = "human_confirmed"
            elif status in {"open", "done", "dismissed"}:
                o.status = status  # type: ignore[assignment]
            else:
                raise ValueError(f"unknown status {status!r}")
            store.put(case)
            return _obligation(o)
    return None


# -- notes ------------------------------------------------------------------------------


def add_note(store: CaseStore, case_id: str, text: str, *, on: date, author: str = "") -> dict | None:
    """A person's own note on a court day. Sourced to them, never to the court."""
    case = store.get(case_id)
    if case is None:
        return None
    note = Note(
        id=new_id("note"),
        on=on,
        text=text.strip(),
        author=author,
        source=SourceRef(kind="human", connector="human", verification="human_confirmed"),
    )
    case.notes.append(note)
    store.put(case)
    store.append(
        [
            CaseEvent(
                id=new_id("evt"),
                case_id=case.id,
                kind="note_added",
                summary=f"Note for {on.isoformat()}: {note.text[:120]}",
                source=note.source,
            )
        ]
    )
    return _note(note)


def delete_note(store: CaseStore, case_id: str, note_id: str) -> bool:
    case = store.get(case_id)
    if case is None:
        return False
    kept = [n for n in case.notes if n.id != note_id]
    if len(kept) == len(case.notes):
        return False
    case.notes = kept
    store.put(case)
    return True


# -- limitation -------------------------------------------------------------------------


def limitation_view(result: limitation.LimitationResult) -> dict:
    rule = result.rule
    return {
        "rule": {
            "key": rule.key,
            "title": rule.title,
            "provision": rule.provision,
            "days": rule.days,
            "reckoned_from": rule.reckoned_from,
            "reviewed": rule.reviewed,
        },
        "start": result.start.isoformat(),
        "last_day": result.last_day.isoformat(),
        "file_by": result.file_by.isoformat(),
        "outer_day": result.outer_day.isoformat() if result.outer_day else None,
        "excluded_days": result.excluded_days,
        "days_left": result.days_left,
        "status": result.status,
        "working": result.working,
        "flags": result.flags,
        "gaps": result.gaps,
    }


def add_deadline(store: CaseStore, case_id: str, result: limitation.LimitationResult) -> dict | None:
    """Put a computed limitation date in the diary as a to-do, sourced to the working."""
    case = store.get(case_id)
    if case is None:
        return None
    due = result.outer_day if result.status == "extension_only" else result.file_by
    obligation = Obligation(
        id=new_id("obl"),
        who="You",
        what=f"{result.rule.title} — last day under {result.rule.provision}",
        due=due,
        source=SourceRef(
            kind="human",
            connector="limitation",
            quote="\n".join(result.working),
            verification="human_confirmed",
        ),
    )
    case.obligations.append(obligation)
    store.put(case)
    store.append(
        [
            CaseEvent(
                id=new_id("evt"),
                case_id=case.id,
                kind="deadline_added",
                summary=f"Deadline added: {result.rule.title}, by {due.isoformat()}.",
                source=obligation.source,
            )
        ]
    )
    return _obligation(obligation)


# -- display boards ---------------------------------------------------------------------


def boards(store: CaseStore, ladder, on: date) -> dict:
    """For each court with your cases listed on `on`: where its board is, and where you are."""
    courts: dict[str, list[Case]] = {}
    for case in store.listed_on(on):
        courts.setdefault(case.court, []).append(case)
    out = []
    for court, cases in sorted(courts.items()):
        cases.sort(key=_item_key)
        hall = next((c.listing.court_hall for c in cases if c.listing and c.listing.court_hall), "")
        status, connector, attempts = ladder.board(court, hall)
        current = _number(status.current_item) if status and status.current_item else None
        yours = []
        for c in cases:
            item = c.listing.item if c.listing and c.listing.on == on else ""
            number = _number(item)
            yours.append(
                {
                    "case_id": c.id,
                    "title": c.title or c.cnr,
                    "item": item,
                    "ahead": (number - current) if number is not None and current is not None else None,
                }
            )
        out.append(
            {
                "court": court,
                "court_hall": (status.court_hall if status else "") or hall,
                "state": status.state if status else "unknown",
                "current_item": status.current_item if status else "",
                "as_of": status.as_of.isoformat() if status else None,
                "note": status.note if status else "",
                "connector": connector,
                "unavailable": None
                if status
                else "; ".join(f"{a.connector}: {a.outcome}" for a in attempts) or "No connector reads this court's board.",
                "yours": yours,
            }
        )
    return {"on": on.isoformat(), "boards": out}


def _number(item: str) -> int | None:
    digits = "".join(ch for ch in item or "" if ch.isdigit())
    return int(digits) if digits else None
