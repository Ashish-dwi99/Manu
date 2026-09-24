"""Manu's HTTP API. Thin: every handler calls one function in `diary` or `watcher`."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from manu import diary, list_of_dates, messages
from manu.case_state.store import CaseStore
from manu.citations import verify_answer
from manu.clock import india_today
from manu.connectors import (
    BrowserPortalConnector,
    ConnectorLadder,
    ECourtsOpenApiConnector,
    FixtureConnector,
)
from manu.doc_intel import grammars
from manu.documents import DocumentError, DocumentStore
from manu.law import default_bail, limitation, s479
from manu.law.offences import OFFENCES
from manu.research import ResearchLadder, check_citations, default_research_ladder
from manu.watcher import CourtWatcher


class TrackRequest(BaseModel):
    cnr: str = Field(min_length=16, max_length=24)
    tracked_by: str = Field(default="", max_length=160)


class NoteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    on: str | None = None
    author: str = Field(default="", max_length=160)


class ClientRequest(BaseModel):
    name: str = Field(default="", max_length=160)


class CheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)


class AuthorityRequest(BaseModel):
    source: str
    doc_id: str
    paragraph: int = Field(ge=1)


class ImportRequest(BaseModel):
    cnrs: list[str] = Field(min_length=1, max_length=200)
    tracked_by: str = Field(default="", max_length=160)


class LimitationRequest(BaseModel):
    rule: str
    start: str
    copy_applied: str | None = None
    copy_ready: str | None = None
    on: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ObligationStatusRequest(BaseModel):
    status: Literal["confirmed", "open", "done", "dismissed"]


def default_ladder() -> ConnectorLadder:
    connectors: list = [ECourtsOpenApiConnector(), BrowserPortalConnector()]
    folder = os.getenv("MANU_RECORDS_DIR")
    if folder:
        connectors.append(FixtureConnector(folder))
    return ConnectorLadder(connectors)


def create_app(
    store: CaseStore | None = None, ladder: ConnectorLadder | None = None, research: ResearchLadder | None = None
) -> FastAPI:
    store = store or CaseStore(os.getenv("MANU_DB", "manu.sqlite3"))
    watcher = CourtWatcher(store, ladder or default_ladder())
    app = FastAPI(title="Manu", version="0.1.0")
    app.state.store = store
    app.state.watcher = watcher
    documents = DocumentStore(store)
    app.state.documents = documents
    research = research or default_research_ladder()
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
            return date.fromisoformat(value) if value else india_today()
        except ValueError as exc:
            raise HTTPException(400, "date must be YYYY-MM-DD") from exc

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "cases": len(store.all()), "offence_rows": len(OFFENCES)}

    @app.get("/api/diary/day")
    def diary_day(on: str | None = None) -> dict:
        return diary.day(store, as_of(on))

    @app.get("/api/diary/upcoming")
    def diary_upcoming(on: str | None = None, days: int = 7) -> dict:
        return diary.upcoming(store, as_of(on), days=max(1, min(days, 60)))

    @app.get("/api/diary/changes")
    def diary_changes(limit: int = 100) -> dict:
        return diary.changes(store, limit=max(1, min(limit, 500)))

    @app.get("/api/cases")
    def cases(on: str | None = None) -> dict:
        day = as_of(on)
        return {"cases": [diary._summary(c, day) for c in store.all()]}

    @app.post("/api/cases")
    def track(request: TrackRequest) -> dict:
        cnr = request.cnr.strip().upper().replace("-", "")
        if not grammars.find_cnr(cnr):
            raise HTTPException(400, "Not a CNR: expected 16 characters like DLSE010001232024.")
        case, events = watcher.track(cnr, tracked_by=request.tracked_by)
        return {"case_id": case.id, "events": [diary._event(e) for e in events]}

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: str, on: str | None = None) -> dict:
        detail = diary.case_detail(store, case_id, as_of(on))
        if detail is None:
            raise HTTPException(404, "case not found")
        return detail

    @app.get("/api/cases/{case_id}/orders/{on}")
    def order(case_id: str, on: str) -> dict:
        found = diary.order_text(store, case_id, as_of(on))
        if found is None:
            raise HTTPException(404, "order not found")
        return found

    @app.post("/api/cases/{case_id}/obligations/{obligation_id}")
    def obligation_status(case_id: str, obligation_id: str, request: ObligationStatusRequest) -> dict:
        result = diary.set_obligation_status(store, case_id, obligation_id, request.status)
        if result is None:
            raise HTTPException(404, "obligation not found")
        return result

    @app.post("/api/cases/{case_id}/notes")
    def add_note(case_id: str, request: NoteRequest) -> dict:
        note = diary.add_note(store, case_id, request.text, on=as_of(request.on), author=request.author)
        if note is None:
            raise HTTPException(404, "case not found")
        return note

    @app.delete("/api/cases/{case_id}/notes/{note_id}")
    def delete_note(case_id: str, note_id: str) -> dict:
        if not diary.delete_note(store, case_id, note_id):
            raise HTTPException(404, "note not found")
        return {"ok": True}

    @app.put("/api/cases/{case_id}/client")
    def set_client(case_id: str, request: ClientRequest) -> dict:
        found = diary.set_client(store, case_id, request.name)
        if found is None:
            raise HTTPException(404, "case not found")
        return found

    # -- drafts a person sends ------------------------------------------------------------

    @app.get("/api/messages/cause-list")
    def message_cause_list(on: str | None = None) -> dict:
        return messages.cause_list(store, as_of(on))

    @app.get("/api/messages/due")
    def message_due(on: str | None = None) -> dict:
        return {"on": as_of(on).isoformat(), "updates": messages.due_updates(store, as_of(on))}

    @app.get("/api/cases/{case_id}/messages/client-update")
    def message_client_update(case_id: str, on: str | None = None) -> dict:
        return messages.client_update(need_case(case_id), as_of(on))

    # -- research -------------------------------------------------------------------------

    @app.get("/api/research/search")
    def research_search(q: str) -> dict:
        if len(q.strip()) < 3:
            raise HTTPException(400, "Search for at least three letters.")
        hits, attempts = research.search(q.strip(), limit=12)
        return {
            "query": q,
            "hits": [h.as_dict() for h in hits],
            "searched": [{"source": a.source, "outcome": a.outcome} for a in attempts],
        }

    @app.get("/api/research/judgments/{source}/{doc_id}")
    def research_judgment(source: str, doc_id: str) -> dict:
        judgment = research.fetch(source, doc_id)
        if judgment is None:
            raise HTTPException(404, "judgment not found in that source")
        return judgment.as_dict()

    @app.post("/api/research/check")
    def research_check(request: CheckRequest) -> dict:
        return check_citations(request.text, research)

    @app.post("/api/cases/{case_id}/authorities")
    def add_authority(case_id: str, request: AuthorityRequest) -> dict:
        need_case(case_id)
        judgment = research.fetch(request.source, request.doc_id)
        if judgment is None:
            raise HTTPException(404, "judgment not found in that source")
        try:
            return diary.add_authority(store, case_id, judgment, request.paragraph)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/cases/{case_id}/research")
    def research_for_case(case_id: str, request: AskRequest) -> dict:
        """The researcher agent when the runtime is connected; otherwise the search results,
        so the advocate can read and rely on paragraphs by hand."""
        from manu.citations import locate, quotes_in
        from manu.runtime.agent import RuntimeUnavailable, research_case

        need_case(case_id)
        hits, attempts = research.search(request.question, limit=10)
        fallback = {
            "hits": [h.as_dict() for h in hits],
            "searched": [{"source": a.source, "outcome": a.outcome} for a in attempts],
        }
        try:
            run = research_case(
                store, case_id, request.question, research=research, documents=documents, timeout_seconds=300
            )
        except RuntimeUnavailable as exc:
            return {"answer": None, "runtime": "unavailable", "reason": str(exc), **fallback}
        authorities = need_case(case_id).authorities
        quotes = []
        for quote in quotes_in(run.result.text):
            found = next((a for a in authorities if locate(a.quote, quote)), None)
            quotes.append(
                {
                    "quote": quote,
                    "verified": found is not None,
                    "source": f"{found.citation or found.title}, para {found.paragraph}" if found else None,
                    "authority_id": found.id if found else None,
                }
            )
        return {"answer": run.result.text, "runtime": "ok", "quotes": quotes, "receipts": run.receipts, **fallback}

    @app.delete("/api/cases/{case_id}/authorities/{authority_id}")
    def delete_authority(case_id: str, authority_id: str) -> dict:
        if not diary.delete_authority(store, case_id, authority_id):
            raise HTTPException(404, "authority not found")
        return {"ok": True}

    @app.get("/api/boards")
    def boards(on: str | None = None) -> dict:
        return diary.boards(store, watcher.ladder, as_of(on))

    @app.get("/api/import/advocate")
    def find_by_advocate(name: str) -> dict:
        name = name.strip()
        if len(name) < 3:
            raise HTTPException(400, "Enter at least three letters of the advocate's name.")
        hits, connector, attempts = watcher.ladder.search_advocate(name)
        following = {c.cnr for c in store.all()}
        return {
            "name": name,
            "connector": connector,
            "hits": [{**h.model_dump(mode="json"), "following": h.cnr in following} for h in hits],
            "attempts": [{"connector": a.connector, "outcome": a.outcome} for a in attempts],
        }

    @app.post("/api/cases/import")
    def import_cases(request: ImportRequest) -> dict:
        followed: list[str] = []
        failed: dict[str, str] = {}
        for raw in dict.fromkeys(request.cnrs):
            cnr = raw.strip().upper().replace("-", "")
            if not grammars.find_cnr(cnr):
                failed[raw] = "Not a CNR."
                continue
            case, events = watcher.track(cnr, tracked_by=request.tracked_by)
            problem = next((e.summary for e in events if e.kind == "fetch_failed"), None)
            if problem:
                failed[cnr] = problem
            followed.append(case.id)
        return {"followed": followed, "failed": failed}

    @app.get("/api/law/limitation")
    def limitation_rules() -> dict:
        return {
            "rules": [
                {
                    "key": r.key,
                    "title": r.title,
                    "group": r.group,
                    "provision": r.provision,
                    "days": r.days,
                    "reckoned_from": r.reckoned_from,
                    "copy_exclusion": r.copy_exclusion,
                    "outer_days": r.outer_days,
                    "reviewed": r.reviewed,
                }
                for r in limitation.RULES.values()
            ]
        }

    def compute_limitation(request: LimitationRequest) -> limitation.LimitationResult:
        def optional(value: str | None):
            return as_of(value) if value else None

        try:
            return limitation.compute(
                request.rule,
                as_of(request.start),
                as_of=as_of(request.on),
                copy_applied=optional(request.copy_applied),
                copy_ready=optional(request.copy_ready),
            )
        except KeyError as exc:
            raise HTTPException(400, f"Unknown limitation rule {request.rule!r}.") from exc

    @app.post("/api/law/limitation")
    def limitation_compute(request: LimitationRequest) -> dict:
        return diary.limitation_view(compute_limitation(request))

    @app.post("/api/cases/{case_id}/deadlines")
    def add_deadline(case_id: str, request: LimitationRequest) -> dict:
        result = compute_limitation(request)
        obligation = diary.add_deadline(store, case_id, result)
        if obligation is None:
            raise HTTPException(404, "case not found")
        return {"obligation": obligation, "limitation": diary.limitation_view(result)}

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

    def need_case(case_id: str):
        case = store.get(case_id)
        if case is None:
            raise HTTPException(404, "case not found")
        return case

    # -- documents -------------------------------------------------------------------

    @app.get("/api/cases/{case_id}/documents")
    def list_documents(case_id: str) -> dict:
        need_case(case_id)
        return {"documents": [d.summary() for d in documents.for_case(case_id)]}

    @app.post("/api/cases/{case_id}/documents")
    async def upload_document(case_id: str, file: UploadFile = File(...)) -> dict:
        need_case(case_id)
        data = await file.read()
        try:
            doc = documents.add(case_id, file.filename or "document", data)
        except DocumentError as exc:
            raise HTTPException(400, str(exc)) from exc
        return doc.summary()

    @app.get("/api/cases/{case_id}/search")
    def search(case_id: str, q: str) -> dict:
        need_case(case_id)
        return {"query": q, "matches": documents.search(case_id, q)}

    @app.get("/api/documents/{document_id}/pages/{page}")
    def document_page(document_id: str, page: int) -> dict:
        doc = documents.get(document_id)
        if doc is None or not 1 <= page <= len(doc.pages):
            raise HTTPException(404, "page not found")
        return {"document": doc.summary(), "page": page, "text": doc.pages[page - 1]}

    # -- workflows -------------------------------------------------------------------

    @app.get("/api/cases/{case_id}/list-of-dates")
    def dates(case_id: str) -> dict:
        return {"rows": list_of_dates.rows(need_case(case_id))}

    @app.get("/api/cases/{case_id}/list-of-dates.docx")
    def dates_docx(case_id: str) -> Response:
        case = need_case(case_id)
        filename = f"List of dates - {case.title or case.cnr}.docx".replace('"', "")
        return Response(
            list_of_dates.to_docx(case),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/runtime")
    def runtime_status() -> dict:
        from manu.runtime.agent import RuntimeUnavailable, kimi_binary

        try:
            kimi_binary()
            ready = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
            reason = "" if ready else "No model key: set OPENROUTER_API_KEY."
        except RuntimeUnavailable as exc:
            ready, reason = False, str(exc)
        return {"ready": ready, "reason": reason}

    @app.post("/api/cases/{case_id}/ask")
    def ask(case_id: str, request: AskRequest) -> dict:
        """Answer from the Chotu runtime when it is connected. Without it, say so, and
        still return the pages that match — the lawyer is never left with nothing."""
        from manu.runtime.agent import RuntimeUnavailable, ask_case

        need_case(case_id)
        matches = documents.search(case_id, request.question)
        try:
            run = ask_case(store, case_id, request.question, documents=documents, timeout_seconds=180)
        except RuntimeUnavailable as exc:
            return {"answer": None, "runtime": "unavailable", "reason": str(exc), "matches": matches}
        return {
            "answer": run.result.text,
            "runtime": "ok",
            "status": run.result.status,
            "receipts": run.receipts,
            "quotes": verify_answer(documents, case_id, run.result.text),
            "matches": matches,
        }

    @app.post("/api/cases/{case_id}/brief")
    def brief(case_id: str) -> dict:
        from manu.runtime.agent import RuntimeUnavailable, prepare_hearing_brief

        need_case(case_id)
        try:
            run = prepare_hearing_brief(store, case_id, documents=documents, timeout_seconds=300)
        except RuntimeUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        return {"status": run.result.status, "summary": run.result.text, "brief": latest_brief(case_id)}

    @app.get("/api/cases/{case_id}/brief")
    def get_brief(case_id: str) -> dict:
        need_case(case_id)
        return {"brief": latest_brief(case_id)}

    def latest_brief(case_id: str) -> dict | None:
        for event in store.events(case_id, limit=200):
            if event.kind == "brief_prepared":
                return {"at": event.at.isoformat(), "markdown": event.after}
        return None

    web_dist = Path(os.getenv("MANU_WEB_DIST", Path(__file__).resolve().parents[2] / "apps" / "web" / "dist"))
    if web_dist.is_dir():
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")
    return app
