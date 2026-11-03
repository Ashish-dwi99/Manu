# Screen clarity pass

A focused follow-up to case progression, based on `case-progression` at `93329a4`.
No legal rules, generated legal document prose, model calls or court connectors changed.

## What changed

- Today: shorter title, search/import prompts, client-update prompt and import confirmation. Removed duplicated owner text from due work.
- Attention: fact, proposed action and controls first. Long proposed step, evidence and interpretation stay under Evidence. The short qualification remains visible, distinguishing a record gap from unfinished work and unknown cause. Accepted work is at the top.
- Case: attention and open work before the order excerpt. Done is still not resolved; reopen/review controls remain. Actions no longer depend on hover. Consistent missing-date wording.
- Week and Changes: concise headers/empty states. Mobile rows stack the category above the fact instead of squeezing long owner names into columns. Overdue work is explicitly included.
- All five source panels: shorter copy, clear empty papers state, persistent mobile close button. Source/quote verification and fictional-law labels remain.
- Research, judgment reader, citation checker and offline reader: short status labels, details expandable. Failure details remain available.
- Notes, authorities, deadline form, draft picker and bail facts: checked in the running app at both widths. Existing concise labels and substantive legal warnings were preserved where shortening would alter meaning.
- Client and cause-list drafts: shorter save/source labels, clear not-sent state. No messages sent.
- Adjournment and bail forms: shorter field labels/hints, visible required fields. Fixed mobile grid sizing that hid questions above the document preview. The preview remains the actual legal draft, not a summary.
- Shared loading/error: a useful retry control with diagnostic details folded away. Mutation errors now visible in several previously silent forms. Stable tab names for assistive tools even when counts change.

## Reproduce

From repo root:

```sh
uv sync
cd apps/web
npm ci
npm run build
# Google Chrome installed; alternatively install Playwright's Chrome channel first.
npm run test:ui
```

The test starts an isolated in-memory demo on port 8790 and stops it at exit. It refuses to run against an existing server. `MANU_SHOTS=/path` overrides the default `qa/screenshots`. All uploads and notes are explicitly fictional fixtures. No real case data or paid services are used. Requests simulating empty/loading/error states are browser-local mocks, not production API changes.

## Coverage actually exercised

Desktop 1440x1000 and phone 390x844:

- Today, find empty state, advocate results/no-results, import confirmation (desktop), cause-list draft.
- Attention, evidence disclosure, accept/edit/save/done; done-not-resolved on case. Pending work remains at the top. Completed-state case screenshot.
- This week and What changed, populated and empty.
- Criminal and civil case pages; Notes, Authorities, Deadline, Draft and Bail facts tools.
- Source, Papers, Research, Dates and Timeline panels; real order text; uploaded fictional text page.
- Judgment search/results and paragraph reader; citation-check result; offline case-reader matches.
- Client update, adjournment missing-input and ready states, bail missing-input form.
- Loading and error states at both widths; error retry recovers. Desktop dark attention.
- Note save and local fictional text upload at both widths. Viewport overflow checks run on every capture. No browser page errors in the final run.

`checks.json` records the exact captures and interaction markers. Selected screenshots in this folder are real running-app captures, not mockups.

## Tests

- Python: 128 pass. One existing Starlette/httpx deprecation warning.
- Ruff: clean.
- Frontend: 16 pass, including visible signal qualification and concise-label semantics.
- Production build: pass.

## Limits

Every existing screen/panel type was opened, but this is not exhaustive testing of every possible combination or failure response. No live court connectivity, paid reader, OCR, real private case, outbound WhatsApp, clipboard permission variations, all legal deadline rules or every file parser failure was exercised. Dark mode was checked on Attention, not every screen. Mobile is a Chrome viewport simulation, not an iOS/Android device test. Existing source/legal text stays intact even when long. Demo mode resets by design. This does not establish real-world case-duration benefit.

## Design-guidance pass (Impeccable)

Impeccable (github.com/pbakaus/impeccable 4.8.0) was read as review criteria only. No install script or binary ran and nothing was added to the app. Each screen was reviewed against it for contrast, hierarchy, labels, touch, focus, and states. Reproduce: `npm run test:ui` (95 captures) and `npm run test:audit` (qa/audit.mjs: dark sweep with computed contrast on every text node, keyboard tab stops, phone touch targets, dialog focus and Escape).

### Defects found and fixed
- Contrast: faint/secondary text and amber/accent text were below 4.5:1 (amber 4.2, accent 3.9, faint about 3.4); a dark-theme citation chip was 2.2. Computed contrast is now clean on every route, tool, panel and dialog in light and dark.
- Dialogs did not take focus when opened. They now do (Escape already closed them; verified in both themes).
- Phone touch targets: buttons, icons, tabs, summaries and links were 18-30px high. Now 40px, except the items listed below.
- Generated update lines showed raw ISO dates ("2026-11-21") in What changed and Record updates. Now "21 Nov 2026". Presentation only: source and order text is untouched ("08.11.2026" in a court direction stays as written). What changed no longer repeats its label inside the line.
- Research source status showed an operator setting name; it is trimmed from the lawyer view.
- To-do direction text was cut to one line with an ellipsis, hiding legal content; it now wraps up to three lines.
- Signal cards: thick coloured left bar replaced by a hairline and status dot. Tiny all-caps wide-tracked labels are sentence case. Type under 12px raised. Composer shows a focus ring.

### Reviewed and kept (with reason)
- Rail and case layout, evidence-on-demand disclosures, black primary action, status colours (red liberty/deadline, amber due or unconfirmed, blue category): they carry meaning and pass contrast.
- Dates panel keeps dd.mm.yyyy: it is a court-format list that exports to .docx.
- Draft previews stay on a paper-white page in dark theme: it is the legal document.
- Modals for drafts and applications: they hold work in progress and need protected focus.

### Not fixed or not covered
- Cause-list number pills on Today (22px high) and the inline citation chips are below 40px; chips have a larger invisible hit area, pills do not.
- Composer inputs use a container ring rather than an own outline, so the keyboard audit flags the two bare inputs; the ring is visible.
- Chrome viewport emulation only, not a device. Dark mode now swept on all routes, panels, tools and both dialogs, but not every empty/error state. No screen reader pass. No live backend or court data.
