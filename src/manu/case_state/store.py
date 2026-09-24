"""SQLite store for cases, their append-only event log, and raw court snapshots.

Cases are stored as JSON documents because their shape follows the court, not a schema
we control. Events are append-only rows. Snapshots keep exactly what a connector
returned so a diff can always be re-run and a disputed change traced back.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from uuid import uuid4

from manu.case_state.models import Case, CaseEvent

_SCHEMA = """
create table if not exists cases (
  id text primary key,
  cnr text,
  body text not null,
  updated_at text not null
);
create unique index if not exists cases_cnr on cases(cnr) where cnr <> '';
create table if not exists events (
  seq integer primary key autoincrement,
  id text not null unique,
  case_id text not null,
  kind text not null,
  at text not null,
  body text not null
);
create index if not exists events_case on events(case_id, seq);
create table if not exists snapshots (
  seq integer primary key autoincrement,
  case_id text not null,
  connector text not null,
  fetched_at text not null,
  sha256 text not null,
  body text not null
);
create index if not exists snapshots_case on snapshots(case_id, seq);
"""


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


class CaseStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("pragma journal_mode=wal")
        self._db.executescript(_SCHEMA)

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._db
                self._db.commit()
            except Exception:
                self._db.rollback()
                raise

    # -- cases ------------------------------------------------------------------------

    def put(self, case: Case) -> Case:
        with self._tx() as db:
            db.execute(
                "insert into cases(id, cnr, body, updated_at) values(?,?,?,?) "
                "on conflict(id) do update set cnr=excluded.cnr, body=excluded.body, updated_at=excluded.updated_at",
                (case.id, case.cnr, case.model_dump_json(), case.updated_at.isoformat()),
            )
        return case

    def get(self, case_id: str) -> Case | None:
        row = self._db.execute("select body from cases where id=?", (case_id,)).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def by_cnr(self, cnr: str) -> Case | None:
        row = self._db.execute("select body from cases where cnr=?", (cnr,)).fetchone()
        return Case.model_validate_json(row[0]) if row else None

    def all(self) -> list[Case]:
        rows = self._db.execute("select body from cases order by id").fetchall()
        return [Case.model_validate_json(body) for (body,) in rows]

    def listed_on(self, day: date) -> list[Case]:
        return [case for case in self.all() if case.next_date == day]

    # -- events -----------------------------------------------------------------------

    def append(self, events: list[CaseEvent]) -> None:
        if not events:
            return
        with self._tx() as db:
            db.executemany(
                "insert into events(id, case_id, kind, at, body) values(?,?,?,?,?)",
                [(e.id, e.case_id, e.kind, e.at.isoformat(), e.model_dump_json()) for e in events],
            )

    def events(self, case_id: str | None = None, *, limit: int = 200) -> list[CaseEvent]:
        if case_id:
            rows = self._db.execute(
                "select body from events where case_id=? order by seq desc limit ?", (case_id, limit)
            ).fetchall()
        else:
            rows = self._db.execute("select body from events order by seq desc limit ?", (limit,)).fetchall()
        return [CaseEvent.model_validate_json(body) for (body,) in rows]

    # -- snapshots --------------------------------------------------------------------

    def save_snapshot(self, case_id: str, connector: str, fetched_at: str, body: dict) -> str:
        text = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(text.encode()).hexdigest()
        with self._tx() as db:
            db.execute(
                "insert into snapshots(case_id, connector, fetched_at, sha256, body) values(?,?,?,?,?)",
                (case_id, connector, fetched_at, digest, text),
            )
        return digest

    def last_snapshot(self, case_id: str) -> dict | None:
        row = self._db.execute(
            "select body from snapshots where case_id=? order by seq desc limit 1", (case_id,)
        ).fetchone()
        return json.loads(row[0]) if row else None
