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

One product, one record, one view. An advocate, a firm and a judge use the same case OS:
add a CNR and Manu gives you everything the record holds. Nobody switches modes.

| Screen | What it shows |
| --- | --- |
| **Today** | One box: paste a CNR to follow a case, or find one of yours. Below it, what is listed today (the diary and the cause list are the same list), and what needs you: liberty dates and directions due |
| **Board** | On today's list: item number and court hall per matter, and the court's live display board with how many items are ahead of you (demo court simulates one) |
| **Import** | Type an advocate's name in the same box; follow every case found in one go |
| **This week** | Hearings and directions for the next seven days, by day |
| **What changed** | New orders, moved dates, directions found, each with its source |
| **Case** | Next hearing, last order, what somebody has to do, and for criminal matters the s.479 BNSS and default-bail arithmetic with the working and the six bail facts (never a recommendation). Ask the case anything underneath |
| **Notes and deadlines** | Your own notes of each hearing, marked as yours. A limitation calculator (appeal, revision, review, SLP, written statement) with the working, saved to the to-do |
| **Drafts to send** | Morning cause list message and client updates (7 and 2 days before a hearing), edited, copied or opened in WhatsApp by you. Manu never sends |
| **Research** | Search judgments, check citations, read by paragraph, rely on a paragraph for the case. Indian Kanoon (`MANU_INDIANKANOON_TOKEN`) is a lead; a firm library (`MANU_JUDGMENTS_DIR`) is licensed; the demo library is fictional |
| **Drafting** | Adjournment and regular bail applications filled from the record, each paragraph sourced, asking for what only you know; .docx |
| **Source panel** | Every line on a case carries a numbered source. Clicking it opens the order or page at those words, highlighted, with whether the words are really there. Papers, list of dates (.docx) and timeline live in the same panel |

The interface follows the Chotu workspace (root): floating sheets on a hatched ground,
Geist for working text, Geist Mono for what you copy, Source Serif 4 for the court's own
words, light and dark.

## Quick start

```bash
uv sync
uv run manu serve --demo          # API + demo court on http://127.0.0.1:8790
cd apps/web && npm install && npm run dev   # UI on http://127.0.0.1:5180
```

Or `cd apps/web && npm run build` once, and `manu serve --demo` serves the built UI too.

The public website (home and About, in Tura's design) is `apps/site`:
`cd apps/site && npm install && npm run dev` serves it on http://127.0.0.1:5190.

The demo court's display board follows the clock (sits 10:30, rises 16:30 IST). To see it
mid-session at any hour: `MANU_DEMO_BOARD_AT=11:42 uv run manu serve --demo`. Try
importing by advocate name with "R. Mehta": two of the demo court's cases are not yet
followed.

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
 diary          watcher ── connectors ladder   liberty labels
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
