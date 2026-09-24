"""Messages Manu drafts and a person sends.

Two kinds, both built by fixed templates from the case record, never by a model:

* **The morning cause list** — every matter listed on a day, grouped by court, in item
  order, with what it is listed for, the last order, what is due and your last note.
  Formatted for WhatsApp (`*bold*`), because that is where chambers read it.
* **A client update** — where and when the client's matter is listed and what happened
  last time. Due seven days and two days before each hearing.

Manu never sends either. There is no tool that contacts anyone (`FORBIDDEN_ACTIONS`); the
person copies the draft, or opens WhatsApp with the text and chooses whom to send it to.
Every draft lists the sources its facts came from, and anything the record does not say
is left out rather than guessed.
"""

from __future__ import annotations

from datetime import date

from manu.case_state.models import Case
from manu.case_state.store import CaseStore

REMIND_DAYS = (7, 2)
"""A client update is due this many days before a hearing."""

def long_date(value: date) -> str:
    return value.strftime("%A, %-d %B %Y")


def short_date(value: date) -> str:
    return value.strftime("%-d %b")


def court_name(court: str) -> str:
    """ "Court of ASJ-03, South District, Saket, New Delhi" → "ASJ-03, Saket"."""
    parts = [p.strip() for p in (court or "").split(",") if p.strip()]
    if not parts:
        return "the court"
    name = parts[0]
    for prefix in ("Court of the ", "Court of "):
        if name.startswith(prefix):
            name = name[len(prefix) :]
    place = parts[-2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else "")
    return f"{name}, {place}" if place else name


def _item_number(case: Case) -> int:
    item = case.listing.item if case.listing else ""
    digits = "".join(ch for ch in item if ch.isdigit())
    return int(digits) if digits else 10**6


def _sources(case: Case) -> list[str]:
    sources = []
    if case.listing and case.listing.source.connector:
        sources.append(f"cause list via {case.listing.source.connector}")
    if case.last_order:
        order = case.last_order
        sources.append(f"order dated {order.on.isoformat()}" + (f" ({order.source.uri})" if order.source.uri else ""))
    return sources


# -- the morning cause list ----------------------------------------------------------------


def cause_list(store: CaseStore, on: date) -> dict:
    """The day's list as one message for chambers: courts, items, purposes, what's due."""
    cases = store.listed_on(on)
    courts: dict[str, list[Case]] = {}
    for case in cases:
        courts.setdefault(case.court, []).append(case)

    lines = [f"*Cause list · {on.strftime('%a, %-d %b %Y')}*"]
    if not cases:
        lines.append("Nothing listed.")
    else:
        lines.append(f"_{len(cases)} {'matter' if len(cases) == 1 else 'matters'}, read from the court record_")
    sources: list[str] = []
    serial = 0
    for court, items in sorted(courts.items()):
        items.sort(key=lambda c: (_item_number(c), c.case_number))
        hall = next((c.listing.court_hall for c in items if c.listing and c.listing.court_hall), "")
        lines += ["", f"*{court_name(court)}*" + (f" — {hall}" if hall else "")]
        for case in items:
            serial += 1
            item = case.listing.item if case.listing and case.listing.on == on else ""
            head = f"{serial}. " + (f"Item {item} · " if item else "") + (case.title or case.cnr)
            if case.case_number:
                head += f" ({case.case_number})"
            lines.append(head)
            lines.append(f"   For: {case.next_purpose or 'purpose not recorded'}")
            if case.last_order:
                order = case.last_order
                lines.append(f"   Last: {short_date(order.on)} — {order.title or 'order'}")
            due = [o for o in case.obligations if o.status == "open" and o.due and o.due <= on]
            for obligation in due:
                when = "today" if obligation.due == on else f"overdue since {short_date(obligation.due)}"
                lines.append(f"   Due: {obligation.who} — {_clip(obligation.what, 90)} ({when})")
            if case.notes:
                note = max(case.notes, key=lambda n: (n.on, n.created_at))
                lines.append(f"   Note ({short_date(note.on)}): {_clip(note.text, 110)}")
            sources += [f"{case.title}: {s}" for s in _sources(case)]
    lines += ["", "_Prepared by Manu from the court record. Check before relying on it._"]
    return {"on": on.isoformat(), "count": len(cases), "text": "\n".join(lines), "sources": sources}


def _clip(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# -- client updates --------------------------------------------------------------------------


def client_update(case: Case, as_of: date) -> dict:
    """A short update for the client about the next hearing. Facts from the record only."""
    name = case.client.name if case.client and case.client.name else ""
    gaps: list[str] = []
    if not name:
        gaps.append("No client name on this case; the greeting is left generic.")
    if case.next_date is None:
        gaps.append("The case has no next date on record, so there is nothing to tell the client yet.")

    listing = case.listing if case.listing and case.listing.on == case.next_date else None
    order = case.last_order
    purpose = case.next_purpose or ""
    number = f" ({case.case_number})" if case.case_number else ""
    court = court_name(case.court)
    lines = [f"Dear {name}," if name else "Hello,", ""]
    if case.next_date:
        lines.append(
            f"Your matter {case.title}{number} is listed on {long_date(case.next_date)} before {court}"
            + (f", for {purpose[0].lower() + purpose[1:]}." if purpose else ".")
        )
    if listing and listing.item:
        lines.append(f"It is item {listing.item}" + (f" in {listing.court_hall}." if listing.court_hall else "."))
    if order:
        lines.append(f"At the last hearing on {long_date(order.on)}: {order.title or 'an order was passed'}.")
    lines += ["", "We will update you after the hearing."]

    days = (case.next_date - as_of).days if case.next_date else None
    return {
        "case_id": case.id,
        "title": case.title,
        "client": name,
        "text": "\n".join(lines),
        "sources": _sources(case),
        "gaps": gaps,
        "days_to_hearing": days,
        "next_date": case.next_date.isoformat() if case.next_date else None,
    }


def due_updates(store: CaseStore, on: date) -> list[dict]:
    """Client updates due today: hearings exactly seven or two days away."""
    due = []
    for case in store.all():
        if case.next_date and (case.next_date - on).days in REMIND_DAYS and case.stage != "disposed":
            due.append(client_update(case, on))
    due.sort(key=lambda d: (d["days_to_hearing"], d["title"]))
    return due
