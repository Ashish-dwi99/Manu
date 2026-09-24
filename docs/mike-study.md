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

## What an Indian lawyer needs from Mike, ranked

Measured against one question: *does this remove work an advocate or a firm does every
week?* Mike serves transactional lawyers first (contracts, redlines). Indian litigation
chambers live in orders, filings and hearing dates, so the ranking differs from Mike's
own emphasis.

| # | Mike gives | Why an Indian lawyer needs it | Manu |
| --- | --- | --- | --- |
| 1 | **Matter documents** — upload, extract text, find in document with page citations | Every case is a bundle: petition, reply, orders, FIR, chargesheet. Finding "where did the IO say that" is daily work | **Built now**: case documents with page-level text, search that answers with file + page + quote |
| 2 | **Workflows / quick actions** — one-click recipes | Chambers repeat the same outputs: list of dates, synopsis, hearing brief, adjournment application | **Built now**: *List of dates* (instant, from the record, exported as .docx) and *Hearing brief* (agent). More recipes follow the same shape |
| 3 | **Generate .docx** | Everything filed or sent is a Word file | **Built now** for the list of dates; drafts follow |
| 4 | **Chat over a matter, with citations** | "What did the court say about the reply?" asked of one case, answered with the page | **Built now**: *Ask this case* on the Chotu runtime, scoped to the case's record and documents. Needs a model key; says so when absent |
| 5 | Citation verification (CourtListener) | Wrong citations embarrass counsel in court | Next: Indian sources (SCI, High Courts, India Code); Indian Kanoon as a lead only |
| 6 | Tabular review | Due diligence, and reviewing many FIRs/statements side by side | Phase 3, in Tura's Sheets (see `sheets-and-excel.md`) |
| 7 | Word add-in | Drafting happens in Word | Phase 3 |
| 8 | Orgs, sharing, audit | Firms: juniors, seniors, clerks on the same matter | Phase 2 |
| 9 | Tamper-evident export | Proving what a document looked like when reviewed | Phase 2, same manifest shape |
| 10 | Scoped memory | Firm preferences, a senior's drafting style | Dhee, later; never a source |

Not needed: US case law, US-centric workflow catalogue, Mike's per-surface chat engines
(Manu has one runtime).

## In depth: what Mike gives per matter, and how it researches

### Per matter ("project")

| Mike | What it is | Manu today |
| --- | --- | --- |
| Documents, folders, versions | Upload, extract text with `[Page N]` markers, keep every version with a SHA-256 | **Papers** tab: page-level text, dedupe by hash. Versions: phase 2 |
| Project chats | Assistant scoped to the matter's documents; tools `list_documents`, `read_document`, `fetch_documents`, `find_in_document` | **Ask this case** on the Chotu runtime with `manu_documents_list/search`, `manu_document_page`, plus the court record and orders |
| Verbatim citations | Every claim carries `[N]` and a `<CITATIONS>` block of short quotes with page; the server then **locates each quote** in the source (exact → whitespace/case → punctuation-tolerant) and marks misses unverified | **Built**: `manu.citations` checks every quotation in an answer against the case's papers and orders, same three tiers; the UI shows found / not found beside the answer |
| Tabular reviews | Documents × questions grid, typed cells, each cited | Phase 3 (Sheets) |
| Workflows + templates | Recipes; templates are immutable, filled as copies | **List of dates** (deterministic) and **Hearing brief** (agent). Indian drafting templates next |
| Generate / edit | `generate_docx`, `generate_excel`, `generate_ppt`, `edit_document` (tracked-change substitutions), `ask_inputs` to pause for missing facts | .docx for the list of dates. Drafting with `edit_document`-style substitutions and an `ask_inputs`-style pause: next |
| Project memory | `memory.md` curated after a chat goes quiet | Dhee, later |

### Research (CourtListener, US only)

Mike's research loop is strict, and the strictness is the valuable part:

1. **Verify** reporter citations (never case names) → cluster IDs.
2. **Fetch** the matched cases (metadata only).
3. **Find in case**: 1–3-word searches, at most three per turn, returning passages.
4. **Read** only the opinion needed if snippets are not enough.
5. **Cite only text it read this turn**, with a link and an `[N]` marker whose quote is
   verbatim opinion text. On a rate limit, stop and answer from what it already has.

### Do we need the same? Yes — the discipline, not the source

An Indian advocate needs research every week: the Supreme Court or High Court judgment
behind a bail argument, whether a precedent still stands, the text of a provision as on
the date of the offence. Mike's CourtListener tools are useless here, but its loop is
exactly right. Manu's version:

| Step | Indian source | Status |
| --- | --- | --- |
| Verify a citation | Parse with `doc_intel` grammars (`(2020) 5 SCC 1`, `AIR 2019 SC 1234`, `2021 SCC OnLine Del 456`, neutral citations `2023 INSC 123`), then resolve | **Built**: `manu.research.check_citations` — verified / lead / demo / not found |
| Find judgments | Indian Kanoon API (paid token) as the search index; eCourts judgments portal and SCI for official copies | **Built**: `IndianKanoonSource` (lead) and `LibrarySource` (licensed); official sources next |
| Read + find in judgment | Paragraph-numbered text; cite by paragraph, not page | **Built**: judgments split by their own paragraph numbers; "rely on ¶n" stores the paragraph on the case |
| Statutes | India Code, **as on the offence date** (IPC before 1 July 2024, BNS after) | Offence table built; full text next |
| Cite only what was read | Same rule; Indian Kanoon results are *leads* until read from an official or licensed copy | Enforced by the same quote check |

What we deliberately do not copy: Mike's research is a chat feature. In Manu it is
attached to a case. A judgment the advocate relies on is saved to the case's papers,
with its citation verified, so the hearing brief and the list of authorities can cite
it later.
