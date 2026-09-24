# Do we need Excel?

Tura has two pieces: the **Sheets** surface in the dashboard
(`apps/dashboard/src/features/sheets`: Univer-based, from GenOffice, Apache-2.0, with AI
formatting guides) and the **xlsx sidecar** (`crates/xlsx-sidecar`: a Rust process that
opens, reads, recalculates and saves .xlsx over a JSON line protocol).

**Not for v1. Yes for phase 3, for two specific jobs.**

## Why not v1

The v1 product is a diary. Nothing in it needs a grid: the diary, the change feed and the
case page are lists and records. Bringing 4.6 MB of spreadsheet UI into the first release
would make the product harder to use and slower to ship. That runs against "one simple
product".

## The two jobs where it earns its place

1. **Tabular review** (Mike's best idea). Rows are documents (200 FIRs, 60 contracts, a
   bundle of witness statements), columns are questions, and each cell is an answer with a
   citation. This is how a firm does due diligence and how a Sessions court could look
   across its undertrials. In Manu:
   * published formats (CNR, case number, section, citation, dates) are answered by the
     `doc_intel` grammars, not a model;
   * closed-choice columns (yes/no, a fixed set of tags) go through Jev, which can abstain;
   * prose columns go through the Chotu runtime with the same "verbatim quote or refused"
     rule as the order reader;
   * the grid renders in Tura's Sheets surface, and exports through the xlsx sidecar.
2. **Firms live in Excel.** Chambers keep their diary, fee register and case list in
   spreadsheets. Import (a firm's case list → follow every CNR) and export (the diary, the
   due list) both go through the xlsx sidecar. Import can come earlier, in phase 2, as a
   small feature, because it is how a firm adopts Manu in an afternoon.

## What to port, when

| When | Port | From Tura |
| --- | --- | --- |
| Phase 2 | xlsx import/export of case lists and the due list | `crates/xlsx-sidecar` (as a sidecar binary, unchanged) |
| Phase 3 | Tabular review grid | `features/sheets` renderer + gateway, restyled to Manu tokens; drop the financial-formatting guides |
