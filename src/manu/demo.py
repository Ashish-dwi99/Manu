"""Seed a diary with the demo court: yesterday's records, then this morning's watch.

`fixtures/demo/day0` is what the court showed yesterday; `day1` is what it shows this
morning (one bail hearing adjourned with a fresh order, one civil suit referred to
mediation). Seeding tracks every case against day0 and then runs the watcher against
day1, so the diary opens with real "what changed" events — the product's first moment.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from manu.case_state.store import CaseStore
from manu.connectors import ConnectorLadder, DemoConnector
from manu.watcher import CourtWatcher, WatchReport

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "demo"


def seed(store: CaseStore, *, today: date | None = None, fixtures: Path = FIXTURES) -> WatchReport:
    today = today or date.today()
    yesterday = CourtWatcher(
        store, ConnectorLadder([DemoConnector(fixtures / "day0", today=today)]), today=lambda: today
    )
    for path in sorted((fixtures / "day0").glob("*.json")):
        yesterday.track(path.stem, tracked_by="demo")
    morning = CourtWatcher(store, ConnectorLadder([DemoConnector(fixtures / "day1", today=today)]), today=lambda: today)
    return morning.run()
