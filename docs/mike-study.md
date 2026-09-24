# What Manu takes from Mike

[Mike](https://github.com/open-legal-products/mike) (MikeOSS) is an open-source legal AI
platform: Next.js frontend, Express backend, Supabase Postgres/Auth, R2 storage, a Word
add-in, and US case law through CourtListener.

**Mike is AGPL-3.0. Manu studies it and copies none of its code.** Nothing from Mike is
vendored, translated or transcribed here. This is the same rule Manu already follows for
paperless-ngx (see `document-intelligence.md`): techniques and product decisions are
not what copyright protects, source code is. When in doubt, don't open the file — read
the docs.

## What Mike is, in one table

| Mike feature | What it does | Manu decision |
| --- | --- | --- |
| Projects + library | Matter folders, subfolders, document library, versions | **Adopt.** Manu's matter vault + case folder already does this; add document versions with SHA-256 per version. |
| Chat over documents | Assistant with `list_documents`, `read_document`, `find_in_document`, `fetch_documents` tools | **Already have.** `legal_case_read`, `legal_file_search`, `legal_source_read` on the Chotu runtime. |
| Tabular review | Grid: rows = documents, columns = questions; each cell is extracted by a model with a typed format (date, yes/no, tag, money…) and a mandatory inline citation `[[document‖page‖quote]]` | **Adopt — highest value.** This is how a firm reviews 200 FIRs, 60 contracts or a bundle of witness statements. Manu version: `review` over matter files, cell = value + `SourceRef` (path, page, span). Rendered with the Sheets surface ported from Tura (see `sheets-and-excel.md`). |
| Typed column formats | Per-format output contract appended to the column prompt | **Adopt, but stronger.** Where a format is a published grammar (CNR, case number, citation, section) the deterministic `doc_intel` layer answers; the model only fills prose columns. Closed-choice columns (`yes_no`, `tag`) go through Jev, which returns a probability per option and may abstain. |
| Workflows | Reusable assistant + tabular recipes, shareable, synced from a catalogue repo | **Adopt.** Manu workflows are Kimi agent specs + prompts (`src/manu/runtime/agents/`). v1 ships *Order reader* and *Hearing brief*; firms will add their own. |
| Citation verification | Verifies cited US cases against CourtListener | **Adopt the idea, Indian sources.** `legal_citation_verify` checks against official sources (sci.gov.in, High Court sites, India Code); Indian Kanoon / Vakeel360 are *leads* until confirmed. |
| Scoped memory | Private `memory.md` + per-project memory; a curator model writes after the chat goes quiet; memory is fenced as untrusted data | **Already have, differently.** Dhee is the memory layer. The adopted rule: memory is *reference context, never a source or a citation*. Case State is the record; Dhee compiles context over it. |
| Word add-in | Task pane that chats with and edits the open .docx with tracked changes | **Later.** Indian chambers draft in Word. Phase 3, after the hearing-brief workflow is proven. |
| Tamper-evident exports | Manifest of SHA-256 hashes per document version + accept/reject trail; optional Ed25519 signature over a canonical digest | **Adopt.** Courts and firms need to prove what a filing looked like when it was reviewed. `manu.exports` (planned) follows the same shape. |
| Orgs, grants, audit | Organizations, members, per-project access grants, audit log export | **Adopt for firms.** Firm → team → matter access, and an audit trail of every agent action (the Chotu runtime already emits a receipt per tool call). |
| Model agnostic, Ollama | Anthropic/Gemini/OpenAI/local | **Already have.** OpenRouter BYOK or Sankhya through the Chotu runtime. |
| Backend layering test | `architecture.test.ts` walks imports and fails on layer violations | **Adopt.** `tests/test_architecture.py` enforces that `manu.law` (deterministic law) never imports the runtime or any model client. |

## Where Manu is deliberately different

1. **One agent runtime, not an engine per surface.** Mike's chat, tabular, and Word chat
   are separate engines. Manu runs every agent turn through `kimi-agent-rs` (the Chotu
   runtime), with the same approvals, cancellation, and completion gate for all of them.
2. **Deterministic law is code.** Section 479 thresholds, default-bail periods and
   offence→punishment lookups are never answered by a model. See `law-engine.md`.
3. **Judges are a first-class user.** Mike serves lawyers. Manu has a Judge surface
   (from JudgeDesk): cause list, case detail, 479 alerts, bail card. The judge surface
   never recommends an outcome.
4. **Courts are live data.** Mike reasons over documents you upload. Manu also watches
   the court (eCourts / NJDG / High Court portals) and turns changes into events and
   obligations, each tied to the order it came from.
