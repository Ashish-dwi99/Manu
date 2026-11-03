"""Stall signals: sourced facts about cases that are not moving — never blame."""

from datetime import date, timedelta

from manu import diary, stalls
from manu.case_state.models import Case, Hearing, Obligation, OrderRecord, SourceRef
from manu.case_state.store import CaseStore

TODAY = date(2026, 11, 3)
BLAME = ("fault", "negligen", "lazy", "blame", "fault of", "deliberate")


def source(kind="court_record"):
    return SourceRef(kind=kind, connector="fixture", uri="orders/x/order-1.pdf", verification="verified")


def hearing(days_ago, purpose="Arguments on charge", business=""):
    return Hearing(on=TODAY - timedelta(days=days_ago), purpose=purpose, outcome=business, source=source())


def order(days_ago, next_in=None):
    record = OrderRecord(
        on=TODAY - timedelta(days=days_ago),
        title="Order",
        text="Put up for arguments on charge.",
        source=source("order"),
    )
    if next_in is not None:
        record.next_date = TODAY + timedelta(days=next_in)
    return record


def case(**over):
    base = dict(id="case_x", title="State v. X", stage="arguments", case_type="criminal")
    base.update(over)
    base.setdefault("cnr", f"DLSE{abs(hash(base['id'])) % 10**10:010d}"[:16])
    return Case(**base)


def kinds(found):
    return {s.kind for s in found}


def test_three_dates_for_the_same_business_is_a_signal_with_its_evidence():
    c = case(hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
    found = stalls.signals(c, TODAY)
    assert "repeated_listing" in kinds(found)
    signal = next(s for s in found if s.kind == "repeated_listing")
    assert "3" in signal.title and "Arguments on charge" in signal.title
    assert len(signal.evidence) == 3
    assert all(e.source is not None for e in signal.evidence)
    assert signal.action  # a next step is proposed, not taken


def test_two_dates_for_the_same_business_is_ordinary():
    c = case(hearings=[hearing(60), hearing(30)])
    assert "repeated_listing" not in kinds(stalls.signals(c, TODAY))


def test_different_business_breaks_the_run():
    c = case(hearings=[hearing(90), hearing(60, purpose="Evidence"), hearing(30)])
    assert "repeated_listing" not in kinds(stalls.signals(c, TODAY))


def test_a_disposed_case_raises_no_signals():
    c = case(stage="disposed", hearings=[hearing(90), hearing(60), hearing(30)])
    assert stalls.signals(c, TODAY) == []


def test_missing_orders_are_a_record_gap_not_a_fact_about_the_court():
    c = case(hearings=[hearing(90), hearing(80), hearing(70), hearing(30)], orders=[order(90)])
    signal = next(s for s in stalls.signals(c, TODAY) if s.kind == "orders_missing")
    assert "3 of the last 4" in signal.title
    assert "not evidence" in signal.detail


def test_an_order_on_the_hearing_date_counts_as_read():
    hs = [hearing(90), hearing(80), hearing(70), hearing(30)]
    c = case(hearings=hs, orders=[order(90), order(80), order(70)])
    assert "orders_missing" not in kinds(stalls.signals(c, TODAY))


def test_order_and_record_disagreeing_on_the_next_date_is_flagged():
    c = case(hearings=[hearing(20)], orders=[order(20, next_in=30)], next_date=TODAY + timedelta(days=12))
    signal = next(s for s in stalls.signals(c, TODAY) if s.kind == "record_conflict")
    assert signal.tone == "attention"
    assert (TODAY + timedelta(days=30)).isoformat() in signal.title
    assert (TODAY + timedelta(days=12)).isoformat() in signal.title


def test_no_conflict_when_the_order_and_record_agree():
    c = case(hearings=[hearing(20)], orders=[order(20, next_in=12)], next_date=TODAY + timedelta(days=12))
    assert "record_conflict" not in kinds(stalls.signals(c, TODAY))


def test_a_later_hearing_means_the_orders_date_has_run_its_course():
    c = case(hearings=[hearing(20), hearing(5)], orders=[order(20, next_in=30)], next_date=TODAY + timedelta(days=12))
    assert "record_conflict" not in kinds(stalls.signals(c, TODAY))


def test_pending_with_no_date_and_no_movement_is_quiet_not_gone():
    c = case(stage="evidence", hearings=[hearing(120)], orders=[order(120)])
    signal = next(s for s in stalls.signals(c, TODAY) if s.kind == "quiet_record")
    assert "not proof" in signal.detail
    assert signal.tone == "attention"


def test_pending_with_no_date_but_recent_movement_is_just_awaiting_a_date():
    c = case(stage="evidence", hearings=[hearing(10)], orders=[order(10)])
    signal = next(s for s in stalls.signals(c, TODAY) if s.kind == "awaiting_date")
    assert signal.tone == "watch"


def test_overdue_direction_is_attention_with_the_orders_words():
    o = Obligation(
        id="obl_1",
        who="IO",
        what="File reply with previous-involvement report",
        due=TODAY - timedelta(days=6),
        source=SourceRef(kind="order", connector="fixture", uri="orders/x/order-1.pdf", quote="IO is directed to file a reply", verification="verified"),
    )
    c = case(obligations=[o], next_date=TODAY + timedelta(days=10))
    signal = next(s for s in stalls.signals(c, TODAY) if s.kind == "directions_waiting")
    assert signal.tone == "attention"
    assert signal.evidence[0].quote == "IO is directed to file a reply"
    assert signal.action == ""  # the direction itself is already on the to-do list


def test_done_directions_do_not_signal():
    o = Obligation(id="obl_1", who="IO", what="File reply", due=TODAY - timedelta(days=6), status="done", source=source("order"))
    c = case(obligations=[o], next_date=TODAY + timedelta(days=10))
    assert "directions_waiting" not in kinds(stalls.signals(c, TODAY))


def test_no_signal_says_whose_fault_anything_is():
    o = Obligation(id="obl_1", who="IO", what="File reply", due=TODAY - timedelta(days=6), source=source("order"))
    c = case(
        hearings=[hearing(90), hearing(80), hearing(70), hearing(30)],
        orders=[order(90, next_in=40)],
        obligations=[o],
        next_date=TODAY + timedelta(days=3),
    )
    for signal in stalls.signals(c, TODAY):
        text = (signal.title + " " + signal.detail).lower()
        assert not any(word in text for word in BLAME), signal.kind


def test_dismissal_hides_a_signal_until_its_evidence_changes():
    store = CaseStore()
    c = case(hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    signal_id = live[0]["id"]
    diary.dismiss_signal(store, c.id, signal_id, TODAY)
    remaining = diary.case_signals(store.get(c.id), TODAY)
    assert signal_id not in {s["id"] for s in remaining}
    # A fourth date for the same business changes the run's anchor: the signal returns.
    updated = store.get(c.id)
    updated.hearings.append(hearing(5))
    store.put(updated)
    revived = {s["kind"] for s in diary.case_signals(store.get(c.id), TODAY)}
    assert "repeated_listing" in revived


def test_accepting_a_next_step_makes_a_stamped_sourced_todo():
    store = CaseStore()
    c = case(hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    signal = next(s for s in live if s["kind"] == "repeated_listing")
    obligation = diary.accept_signal_action(store, c.id, signal["id"], TODAY)
    assert obligation["who"] == "You"
    assert obligation["due"] == (TODAY + timedelta(days=10)).isoformat()
    assert obligation["created_at"] and obligation["closed_at"] is None
    assert obligation["source"]["verification"] == "human_confirmed"
    assert signal["title"] in obligation["source"]["quote"]
    events = store.events(c.id)
    assert events[0].kind == "action_added"
    # The signal quiets to an "accepted" state; it is not treated as resolved.
    after = next(s for s in diary.case_signals(store.get(c.id), TODAY) if s["id"] == signal["id"])
    assert after["accepted"]["id"] == obligation["id"]


def test_accept_is_idempotent_across_tabs_and_retries():
    store = CaseStore()
    c = case(hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    signal_id = next(s for s in live if s["kind"] == "repeated_listing")["id"]
    first = diary.accept_signal_action(store, c.id, signal_id, TODAY)
    second = diary.accept_signal_action(store, c.id, signal_id, TODAY)
    assert first["id"] == second["id"]
    assert len(store.get(c.id).obligations) == 1
    assert len([e for e in store.events(c.id) if e.kind == "action_added"]) == 1


def test_accepted_step_stays_on_the_practice_view_until_done():
    store = CaseStore()
    c = case(
        hearings=[hearing(90), hearing(60), hearing(30)],
        orders=[order(90), order(60), order(30)],
        next_date=TODAY + timedelta(days=10),
    )
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    signal_id = next(s for s in live if s["kind"] == "repeated_listing")["id"]
    obligation = diary.accept_signal_action(store, c.id, signal_id, TODAY)
    body = diary.attention(store, TODAY)
    # The accepted signal no longer asks for triage, and the step is listed instead.
    assert body["count"] == 0
    assert body["in_progress"][0]["next_steps"][0]["id"] == obligation["id"]
    # Done: it leaves the practice view, and the quieted signal stays quiet.
    diary.set_obligation_status(store, c.id, obligation["id"], "done")
    assert diary.attention(store, TODAY)["in_progress"] == []
    assert signal_id not in {s["id"] for s in diary.case_signals(store.get(c.id), TODAY)}
    assert store.get(c.id).obligations[0].closed_at is not None
    # Dismissed instead: the signal returns to triage — the stall was never acted on.
    store2 = CaseStore()
    store2.put(
        case(
            hearings=[hearing(90), hearing(60), hearing(30)],
            orders=[order(90), order(60), order(30)],
            next_date=TODAY + timedelta(days=10),
        )
    )
    live2 = diary.case_signals(store2.get(c.id), TODAY)
    sid = next(s for s in live2 if s["kind"] == "repeated_listing")["id"]
    obl = diary.accept_signal_action(store2, c.id, sid, TODAY)
    diary.set_obligation_status(store2, c.id, obl["id"], "dismissed")
    assert sid in {s["id"] for s in diary.case_signals(store2.get(c.id), TODAY)}
    assert diary.attention(store2, TODAY)["count"] == 1


def test_accepted_step_survives_a_restart():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "manu.sqlite3"
        store = CaseStore(path)
        c = case(hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
        store.put(c)
        live = diary.case_signals(store.get(c.id), TODAY)
        signal_id = next(s for s in live if s["kind"] == "repeated_listing")["id"]
        accepted = diary.accept_signal_action(store, c.id, signal_id, TODAY)
        diary.set_obligation_status(store, c.id, accepted["id"], "done")
        reopened = CaseStore(path)
        stored = reopened.get(c.id)
        assert stored.obligations[0].status == "done"
        assert stored.obligations[0].closed_at is not None
        assert stored.signal_actions[signal_id] == accepted["id"]
        assert signal_id not in {s["id"] for s in diary.case_signals(stored, TODAY)}


def test_another_orderless_hearing_revives_a_tucked_gap_signal():
    store = CaseStore()
    c = case(hearings=[hearing(30), hearing(20)])
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    gap = next(s for s in live if s["kind"] == "orders_missing")
    assert gap["evidence"][0]["label"].startswith("Hearing ·")
    diary.dismiss_signal(store, c.id, gap["id"], TODAY)
    assert not any(s["kind"] == "orders_missing" for s in diary.case_signals(store.get(c.id), TODAY))
    updated = store.get(c.id)
    updated.hearings.append(hearing(5))  # a third date, still no orders read
    store.put(updated)
    revived = next(s for s in diary.case_signals(store.get(c.id), TODAY) if s["kind"] == "orders_missing")
    assert revived["id"] != gap["id"]
    assert "3 of the last 3" in revived["title"]


def test_hearings_arriving_out_of_order_still_read_as_a_run():
    c = case(hearings=[hearing(30), hearing(90), hearing(60)])
    found = stalls.signals(c, TODAY)
    signal = next(s for s in found if s.kind == "repeated_listing")
    assert [e.label for e in signal.evidence] == sorted(e.label for e in signal.evidence)


def test_an_undated_open_direction_is_not_a_stall_signal():
    o = Obligation(id="obl_u", who="You", what="Chase the order copy", source=source("order"))
    c = case(obligations=[o], next_date=TODAY + timedelta(days=3))
    assert "directions_waiting" not in kinds(stalls.signals(c, TODAY))


def test_attention_view_ranks_cases_with_attention_first():
    store = CaseStore()
    stuck = case(id="case_stuck", hearings=[hearing(90), hearing(60), hearing(30)], next_date=TODAY + timedelta(days=10))
    calm = case(id="case_calm", hearings=[hearing(10)], next_date=TODAY + timedelta(days=20))
    store.put(stuck)
    store.put(calm)
    body = diary.attention(store, TODAY)
    assert body["count"] == 1
    assert body["entries"][0]["id"] == "case_stuck"
    assert body["entries"][0]["signals"]


def test_accepting_a_signal_without_a_next_step_returns_none():
    store = CaseStore()
    o = Obligation(id="obl_1", who="IO", what="File reply", due=TODAY - timedelta(days=6), source=source("order"))
    c = case(obligations=[o], next_date=TODAY + timedelta(days=10))
    store.put(c)
    live = diary.case_signals(store.get(c.id), TODAY)
    signal = next(s for s in live if s["kind"] == "directions_waiting")
    assert diary.accept_signal_action(store, c.id, signal["id"], TODAY) is None
