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
from manu.clock import india_today
from manu.connectors import ConnectorLadder, DemoConnector
from manu.watcher import CourtWatcher, WatchReport

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "demo"


def seed(store: CaseStore, *, today: date | None = None, fixtures: Path = FIXTURES) -> WatchReport:
    today = today or india_today()
    yesterday = CourtWatcher(
        store, ConnectorLadder([DemoConnector(fixtures / "day0", today=today)]), today=lambda: today
    )
    for path in sorted((fixtures / "day0").glob("*.json")):
        yesterday.track(path.stem, tracked_by="demo")
    morning = CourtWatcher(store, ConnectorLadder([DemoConnector(fixtures / "day1", today=today)]), today=lambda: today)
    report = morning.run()
    seed_documents(store, fixtures)
    return report


def seed_documents(store: CaseStore, fixtures: Path = FIXTURES) -> None:
    """Papers for two demo cases, so search, Ask and the list of dates have a bundle."""
    from manu.documents import DocumentStore

    documents = DocumentStore(store)
    for folder in sorted((fixtures / "documents").glob("*")):
        case = store.by_cnr(folder.name)
        if case is None:
            continue
        for path in sorted(folder.glob("*.txt")):
            documents.add(case.id, path.name, path.read_bytes())


def demo_research_ladder():
    """The live research ladder plus the fictional demo library, labelled `demo`."""
    from manu.research import LibrarySource, ResearchLadder, default_research_ladder

    live = default_research_ladder()
    return ResearchLadder([LibrarySource(FIXTURES / "judgments", name="demo_library", standing="demo"), *live.sources])


def demo_ladder(today: date | None = None, fixtures: Path = FIXTURES) -> ConnectorLadder:
    """The live ladder plus the demo court, so "Check courts now" works in the demo."""
    from manu.api import default_ladder

    ladder = default_ladder()
    return ConnectorLadder([*ladder.connectors, DemoConnector(fixtures / "day1", today=today)])
