from datetime import date

from manu.case_state.store import CaseStore
from manu.connectors import ConnectorLadder, ConnectorUnavailable, CourtOrder, CourtRecord, Tier
from manu.demo import seed
from manu.watcher import CourtWatcher

TODAY = date(2026, 9, 24)


class Fake:
    def __init__(self, record=None, *, name="fake", tier=Tier.OFFICIAL_API, fail=False):
        self.record, self.name, self.tier, self.fail = record, name, tier, fail

    def fetch(self, cnr):
        if self.fail:
            raise ConnectorUnavailable("down")
        return self.record


def test_ladder_falls_through_and_records_attempts():
    record = CourtRecord(cnr="DLSE010001232024")
    ladder = ConnectorLadder(
        [
            Fake(record, name="clerk", tier=Tier.HUMAN),
            Fake(name="api", fail=True),
            Fake(None, name="portal", tier=Tier.BROWSER),
        ]
    )
    result = ladder.fetch("DLSE010001232024")
    assert result.connector == "clerk"
    assert [a.outcome for a in result.attempts] == ["down", "not_covered", "ok"]


def test_demo_morning_produces_the_expected_changes():
    store = CaseStore()
    report = seed(store, today=TODAY)
    kinds = sorted(e.kind for e in report.events)
    assert kinds == ["hearing_date_changed", "new_order", "obligation_found", "status_changed"]
    moved = next(e for e in report.events if e.kind == "hearing_date_changed")
    assert "2026-10-01" in moved.after


def test_rewatching_without_court_changes_is_silent():
    store = CaseStore()
    seed(store, today=TODAY)
    from manu.connectors import DemoConnector
    from manu.demo import FIXTURES

    watcher = CourtWatcher(store, ConnectorLadder([DemoConnector(FIXTURES / "day1", today=TODAY)]))
    assert watcher.run().events == []


def test_fetch_failure_is_an_event_not_an_exception():
    store = CaseStore()
    watcher = CourtWatcher(store, ConnectorLadder([Fake(fail=True)]))
    case, events = watcher.track("DLSE010001232024")
    assert [e.kind for e in events] == ["tracked", "fetch_failed"]


def test_new_order_is_read_and_date_change_recorded():
    store = CaseStore()
    first = CourtRecord(cnr="DLSE010001232024", next_date=date(2026, 10, 1), next_purpose="evidence")
    connector = Fake(first)
    watcher = CourtWatcher(store, ConnectorLadder([connector]))
    case, _ = watcher.track("DLSE010001232024")
    connector.record = CourtRecord(
        cnr="DLSE010001232024",
        next_date=date(2026, 10, 20),
        next_purpose="evidence",
        orders=[
            CourtOrder(
                on=date(2026, 10, 1),
                text="The complainant shall produce the original agreement. Put up on 20.10.2026 for evidence.",
            )
        ],
    )
    report = watcher.run()
    kinds = {e.kind for e in report.events}
    assert {"hearing_date_changed", "obligation_found"} <= kinds
    stored = store.get(case.id)
    assert stored.obligations[0].who == "complainant"
    assert stored.obligations[0].due is None  # no date, no "within", no "next date": unknown, not guessed


def test_first_follow_is_one_summary_event_not_a_burst_of_changes():
    store = CaseStore()
    from manu.connectors import DemoConnector
    from manu.demo import FIXTURES

    watcher = CourtWatcher(store, ConnectorLadder([DemoConnector(FIXTURES / "day0", today=TODAY)]))
    case, events = watcher.track("DLSE010001232024")
    assert [e.kind for e in events] == ["tracked"]
    assert "listed 2026-09-24" in events[0].summary and "direction(s)" in events[0].summary
    assert case.obligations, "directions from the latest order are still recorded"
