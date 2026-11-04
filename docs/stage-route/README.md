# Stage and route on the case page

The case page now opens with where the record places the matter: its stage and, for a
criminal case, the prosecution route — each echoed exactly as the court record states
it, with the fetch it came from. There is deliberately no flow rail: a stage word from
the record does not establish which stages a case has traversed or what comes next, so
the page shows the words and nothing more. Where the record is silent the gap is shown
("Stage not on record" / "Route not on record"), never filled by a guess. Underneath
sit the sourced pending steps: the listing and every open direction with its citation,
capped at five with the rest under To do.

Captures from the running demo (fictional cases, this branch's build):

- `case-criminal-desktop.png` / `case-criminal-phone.png` — State v. Aamir Khan:
  stage Evidence, police case, listing and two sourced directions.
- `case-gap-desktop.png` / `case-gap-phone.png` — State v. Imran & Anr.: the record
  states the stage (Investigation) but no route; the gap shows instead of a guess.
- `case-civil-desktop.png` — civil matter: recorded stage, no criminal route line.
- `case-dark.png` — the same section in the dark theme.

Also exercised with local fixture variants (not committed): a complaint-route case, a
record with no stage at all, a case reserved for judgment, and a disposed case (no
implied completion; pending steps show "No pending step on record"). Citation pills in
the pending list open the source panel at the quoted words, as elsewhere.

Data path: `CourtRecord.route` (connector-supplied, empty when unstated) →
`Case.route` + `Case.stage_source`/`route_source` in the watcher → `standing` in the
case API → the Stage section. Demo fixtures carry `"route": "police"`; the bail
application fixture deliberately does not, so the gap state is part of the demo.

Verified: 131 pytest, 18 frontend tests, ruff clean, `qa/screens.mjs` (adds
`19b-case-stage-gap`) and `qa/audit.mjs` with no new findings, no horizontal overflow
at 1440px or 390px.
