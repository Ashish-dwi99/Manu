# Architecture

## Layers

| Layer | Package | Rule |
| --- | --- | --- |
| Web | `apps/web` | Shows the record. Never computes law. |
| API | `manu.api` | Thin: each handler calls one function. |
| Views | `manu.diary`, `manu.judge` | Read the case state; the judge lens adds labels and bail facts. |
| Watcher | `manu.watcher` | Fetch → diff → events → read new orders → snapshot. Deterministic. |
| Connectors | `manu.connectors` | A ladder, most official first. |
| Orders | `manu.orders` | Deterministic reader: next date, directions, exact spans. |
| Law | `manu.law` | Statute arithmetic. Standard library only; no model, no runtime (tested). |
| Case state | `manu.case_state` | The truth. SQLite: case documents, append-only events, raw snapshots. |
| Runtime | `manu.runtime` | The bridge to the Chotu runtime: wire client, tools, agent specs. |
| Grammars | `manu.doc_intel` | CNR, case numbers, citations, statutes, dates. Ported from Tura. |

## The record

```text
Case
 ├── parties, accused (custody spans, first-offender, other cases), charges
 ├── hearings                       each with a SourceRef
 ├── orders   (text + URI + sha256) each with a SourceRef
 ├── obligations (who, what, due)   each with a SourceRef → order span + quote
 └── events   (append-only)         tracked, new_order, hearing_date_changed, …
```

`SourceRef.verification` is one of `verified` (from the court), `human_confirmed`,
`lead` (read by Manu, awaiting a person), `unverified`. The UI always says which.

## Connector ladder

```text
1 official API          eCourts Open API (institutional), High Court services
2 official public data  published cause lists and orders
3 browser               the public portal, driven by a Chotu page-tool agent
4 human                 a clerk or junior uploads / confirms
```

Each connector returns a record, says the case is not covered (`None`), or says it is
unavailable right now. The ladder records every attempt, so the diary can show how it
knows what it shows. v1 ships the fixture/folder connector and the two official slots,
which report themselves unavailable until configured. They do not pretend.

## The watcher

1. Fetch through the ladder. A failure becomes a `fetch_failed` event, not an exception.
2. The first sync of a case is summarised in one `tracked` event. Only later syncs
   produce change events, so following a case doesn't flood the feed.
3. Diff: status, stage, next date/purpose, new orders (identity = date + content digest),
   hearings, disposal.
4. Read each new order (`manu.orders`) → next date, purpose, obligations with spans.
5. Save the raw snapshot with its SHA-256.

## Agents (Chotu runtime)

See `runtime.md`. Two agents in v1:

* `order-reader` — refines the directions in one order; completion-gated on
  `manu_obligations_propose`; quotes must be verbatim.
* `hearing-brief` — writes the brief for the next date from the case record;
  completion-gated on `manu_brief_save`; statutory numbers only from tools.

## Memory (Dhee)

Case state is the canonical record. Dhee (optional extra `manu[dhee]`) is the context
compiler around it: one namespace per case, recall across a firm's matters, and the
compiled packet the runtime's Jev director reads per turn. Memory is reference context. It
is never a source or a citation (the same rule as Mike's scoped memory).
