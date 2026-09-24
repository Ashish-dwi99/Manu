# Manu

**The case diary that reads the court for you.**

For Indian advocates, law firms and judges. Add a case by its CNR. Every morning Manu
reads the court, notices what changed, reads each new order, and tells you what you have
to do and by when. Everything it tells you points back to the order and the words it came
from.

```text
"Something changed this morning."

State v. Aamir Khan — next date moved 24 Sep → 1 Oct (arguments on bail).
New order, 23 Sep: IO to file reply with previous-involvement report by 29 Sep,
failing which the SHO shall remain present in person.
                                   Source: order dated 23.09.2026 · [Confirm] [Done]
```

One product, one record, two lenses:

| | Advocate / firm | Judge |
| --- | --- | --- |
| **Diary** | My cases listed today, what each is listed for, last order, what's due | Today's cause list |
| **What changed** | New orders, moved dates, directions found | same |
| **Due** | Directions and hearings in the next 14 days | same |
| **Case** | Last order, directions with source, timeline | + Section 479 BNSS and default-bail arithmetic with working, bail facts (never a recommendation) |

## Quick start

```bash
uv sync
uv run manu serve --demo          # API + demo court on http://127.0.0.1:8790
cd apps/web && npm install && npm run dev   # UI on http://127.0.0.1:5180
```

Or `cd apps/web && npm run build` once, and `manu serve --demo` serves the built UI too.

The demo court has five cases in Saket, New Delhi. It seeds "yesterday" and then runs
this morning's watch, so the diary opens on real changes: an adjourned bail hearing with a
fresh order, a civil suit sent to mediation, a Section 479 threshold four days away, a
default-bail right about to accrue, and a record with a wrongly labelled section.

## Tests

```bash
uv run pytest            # law engine, order reader, watcher, API, runtime bridge
uv run ruff check src tests
cd apps/web && npm test && npm run build
```

## How it is built

```text
                apps/web  (Tura's shell, Chotu's workspace design language)
                    │
              manu.api  (FastAPI)
                    │
   ┌────────────────┼──────────────────────────┐
   │                │                          │
 diary          watcher ── connectors ladder   judge lens
 (views)        (fetch → diff → events)        (labels, bail facts)
   │                │                          │
   └──────── case_state (SQLite: cases, append-only events, snapshots)
                    │
        orders (deterministic reader)     law (s.479, default bail, IPC↔BNS)
                    │
        runtime → kimi-agent-rs (Chotu runtime: Jev director, approvals,
                  completion gate) with Manu's tools, scoped to one case
```

* **Case state is the truth.** Every fact carries a `SourceRef`: connector, URI, hash,
  page/span, quote, and whether it is from the court, confirmed by a person, or only read
  by Manu.
* **Law is code, not a model.** `manu.law` computes Section 479 BNSS and BNSS s.187(3)
  default bail with the working shown, and picks IPC or BNS by offence date. It cannot
  import a model client (enforced by `tests/test_architecture.py`).
* **Agents run on the Chotu runtime.** `kimi-agent-rs` owns the loop. Manu gives it
  agent specs (`src/manu/runtime/agents/`) and tools for one case. An agent may propose a
  direction only with a verbatim quote from the order; anything else is refused.
* **Nothing irreversible.** No filing, payment, portal submission or contact with a party.
  Those actions don't exist as tools, and the registry refuses to register them.

Read next: [`docs/product.md`](docs/product.md) (what we are building and what we are
not), [`docs/architecture.md`](docs/architecture.md), [`docs/law-engine.md`](docs/law-engine.md),
[`docs/runtime.md`](docs/runtime.md).

## Where things came from

* **Tura / Chotu** (`tura-learn/tura`): the agent runtime (kimi-agent-rs + Jev), the
  document grammars in `src/manu/doc_intel/` (CNR, case numbers, citations, statutes,
  dates), the Manu advocate workspace's design language and date helpers.
* **JudgeDesk** (`Ashish-dwi99/JudgeDesk`): the judge's screens and rules — cause list
  labels, Section 479 alerts, bail facts, "the judge decides, the system supports".
  See [`docs/judge-desk.md`](docs/judge-desk.md).
* **Mike** (`open-legal-products/mike`, AGPL-3.0): studied, not copied. See
  [`docs/mike-study.md`](docs/mike-study.md).
