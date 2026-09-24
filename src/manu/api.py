"""Manu's HTTP API. Thin: every handler calls one function in `diary` or `watcher`."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from manu import diary
from manu.case_state.store import CaseStore
from manu.connectors import (
    BrowserPortalConnector,
    ConnectorLadder,
    ECourtsOpenApiConnector,
    FixtureConnector,
)
from manu.doc_intel import grammars
from manu.law import default_bail, s479
from manu.law.offences import OFFENCES
from manu.watcher import CourtWatcher

Lens = Literal["advocate", "judge"]


class TrackRequest(BaseModel):
    cnr: str = Field(min_length=16, max_length=24)
    tracked_by: str = Field(default="", max_length=160)


class ObligationStatusRequest(BaseModel):
    status: Literal["confirmed", "open", "done", "dismissed"]


def default_ladder() -> ConnectorLadder:
    connectors: list = [ECourtsOpenApiConnector(), BrowserPortalConnector()]
    folder = os.getenv("MANU_RECORDS_DIR")
    if folder:
        connectors.append(FixtureConnector(folder))
    return ConnectorLadder(connectors)


def create_app(store: CaseStore | None = None, ladder: ConnectorLadder | None = None) -> FastAPI:
    store = store or CaseStore(os.getenv("MANU_DB", "manu.sqlite3"))
    watcher = CourtWatcher(store, ladder or default_ladder())
    app = FastAPI(title="Manu", version="0.1.0")
    app.state.store = store
    app.state.watcher = watcher
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            o for o in os.getenv("MANU_WEB_ORIGINS", "http://127.0.0.1:5180,http://localhost:5180").split(",") if o
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def as_of(value: str | None) -> date:
        try:
            return date.fromisoformat(value) if value else date.today()
        except ValueError as exc:
            raise HTTPException(400, "date must be YYYY-MM-DD") from exc

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "cases": len(store.all()), "offence_rows": len(OFFENCES)}

    @app.get("/api/diary/day")
    def diary_day(on: str | None = None, lens: Lens = "advocate") -> dict:
        return diary.day(store, as_of(on), lens=lens)

    @app.get("/api/diary/upcoming")
    def diary_upcoming(on: str | None = None, days: int = 7) -> dict:
        return diary.upcoming(store, as_of(on), days=max(1, min(days, 60)))

    @app.get("/api/diary/changes")
    def diary_changes(limit: int = 100) -> dict:
        return diary.changes(store, limit=max(1, min(limit, 500)))

    @app.get("/api/cases")
    def cases(on: str | None = None, lens: Lens = "advocate") -> dict:
        day = as_of(on)
        return {"cases": [diary._summary(c, day, lens) for c in store.all()]}

    @app.post("/api/cases")
    def track(request: TrackRequest) -> dict:
        cnr = request.cnr.strip().upper().replace("-", "")
        if not grammars.find_cnr(cnr):
            raise HTTPException(400, "Not a CNR: expected 16 characters like DLSE010001232024.")
        case, events = watcher.track(cnr, tracked_by=request.tracked_by)
        return {"case_id": case.id, "events": [diary._event(e) for e in events]}

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, on: str | None = None, lens: Lens = "advocate") -> dict:
        detail = diary.case_detail(store, case_id, as_of(on), lens=lens)
        if detail is None:
            raise HTTPException(404, "case not found")
        return detail

    @app.post("/api/cases/{case_id}/obligations/{obligation_id}")
    def obligation_status(case_id: str, obligation_id: str, request: ObligationStatusRequest) -> dict:
        result = diary.set_obligation_status(store, case_id, obligation_id, request.status)
        if result is None:
            raise HTTPException(404, "obligation not found")
        return result

    @app.post("/api/watch/run")
    def run_watch() -> dict:
        report = watcher.run()
        return {
            "checked": report.checked,
            "changed": report.changed,
            "failed": report.failed,
            "events": [diary._event(e) for e in report.events],
        }

    @app.get("/api/law/meta")
    def law_meta() -> dict:
        return {
            "s479_alert_window_days": s479.ALERT_WINDOW_DAYS,
            "default_bail_alert_window_days": default_bail.ALERT_WINDOW_DAYS,
            "offences": [
                {
                    "key": o.key,
                    "title": o.title,
                    "counterpart": o.counterpart,
                    "reviewed": o.reviewed,
                    "max_years": o.punishment.max_years,
                    "life": o.punishment.life,
                    "death": o.punishment.death,
                }
                for o in OFFENCES.values()
            ],
        }

    web_dist = Path(os.getenv("MANU_WEB_DIST", Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"))
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app
