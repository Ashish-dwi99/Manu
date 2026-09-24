"""`manu serve`, `manu demo`, `manu watch`, `manu track CNR`."""

from __future__ import annotations

import argparse
import json
import os
import sys

from manu.case_state.store import CaseStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="manu", description="The case diary that reads the court for you.")
    parser.add_argument("--db", default=os.getenv("MANU_DB", "manu.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Run the API (and the built web app, if present).")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8790)
    serve.add_argument("--demo", action="store_true", help="Seed the demo court into an in-memory diary.")
    sub.add_parser("demo", help="Seed the demo court into --db.")
    sub.add_parser("watch", help="Check every tracked case now.")
    track = sub.add_parser("track", help="Start following a case by CNR.")
    track.add_argument("cnr")
    args = parser.parse_args(argv)

    if args.command == "serve":
        import uvicorn

        from manu.api import create_app

        store = CaseStore(":memory:" if args.demo else args.db)
        ladder = research = None
        if args.demo:
            from manu.demo import demo_ladder, demo_research_ladder, seed

            seed(store)
            ladder = demo_ladder()
            research = demo_research_ladder()
        uvicorn.run(create_app(store, ladder, research), host=args.host, port=args.port)
        return 0

    store = CaseStore(args.db)
    if args.command == "demo":
        from manu.demo import seed

        report = seed(store)
        print(f"Seeded {len(store.all())} cases; this morning's watch found {len(report.events)} change(s).")
        return 0

    from manu.api import default_ladder
    from manu.watcher import CourtWatcher

    watcher = CourtWatcher(store, default_ladder())
    if args.command == "watch":
        report = watcher.run()
        json.dump({"checked": report.checked, "changed": report.changed, "failed": report.failed}, sys.stdout, indent=2)
        print()
        return 1 if report.failed and not report.changed else 0
    if args.command == "track":
        case, events = watcher.track(args.cnr)
        for event in events:
            print(f"{event.kind}: {event.summary}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
