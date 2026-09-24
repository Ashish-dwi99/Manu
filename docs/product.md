# Manu: one simple product

## The promise

> *"I already have a case. Never make me track it by hand again."*

An Indian advocate lives by their diary: which cases are listed tomorrow, in which
court, for what, and what was ordered last time. Today that means refreshing eCourts,
downloading PDFs, and asking juniors. A judge's morning is the same problem from the
bench: a cause list of case numbers and memory. A firm's version is fifty associates' diaries
that nobody can see at once.

Manu does one thing for all of them: **it keeps the diary true, and tells you what changed
and what you have to do, with the source.**

## Who it is for, in order

1. **Litigating advocates and their chambers** (district courts and High Courts). The
   largest group and the most daily pain. Free for one advocate's own cases.
2. **Law firms and in-house litigation teams.** The same diary across the team, plus
   who owes what by when.
3. **Judges** (JudgeDesk). The same diary seen from the bench: the cause list with liberty
   labels, and the statutory arithmetic that is easy to miss. Pilot with a Sessions
   division.
4. **Litigants** (later). The same record, explained in plain language on WhatsApp.

## What v1 does

1. **Follow a case** by CNR. Manu reads the court record and every order on it.
2. **Watch** every morning. Next date moved, new order, status or stage changed, disposed
   — each an event with its source.
3. **Read the order.** A fixed-rule pass finds the next date and every direction (who,
   what, by when) with the exact words. The order-reader agent refines them on the Chotu
   runtime, quoting the order word for word. A person confirms, completes or dismisses each one.
4. **The diary**: today's list, what changed, what's due in the next 14 days, one page per
   case.
5. **Liberty, for everyone**: 479 ALERT / URGENT / BAIL / WOMAN / JUVENILE / DATA GAP labels, Section
   479 and default-bail status with the working, and the six bail facts, each with a source
   or a gap, on the same case page an advocate and a judge both use. Never a recommendation.
6. **The day in court**: each listed matter shows its cause-list item and court hall;
   the court's display board, where a connector reads it, says where the court is and how
   many items are ahead. Your own notes of what happened sit beside the court's record,
   marked as yours.
7. **Import your practice**: search by advocate name and follow every case at once.
8. **Limitation**: the last day for an appeal, revision, review, SLP or written statement,
   by fixed rules with the working (see `law-engine.md`), saved to the to-do list.
9. **Every line cites its words**: a numbered source on each fact opens the order or page
   at the quoted words, highlighted, and says whether they were found.

## What v1 deliberately does not do

* No chatbot as the product. Chat may come as a way to ask about a case, not as the
  proposition.
* No filing, submission, payment or contact with anyone. Manu prepares; people act.
* No scraping as a foundation. Connectors go official API → official public data →
  browser agent → a person. See `architecture.md`.
* No scores for accused persons, no bail predictions, no judge analytics.

## Next, in order

| Phase | What | Built from |
| --- | --- | --- |
| 1 | Real connectors: eCourts Open API (institutional onboarding), High Court case status and orders, and a portal browser agent on the Chotu page tool for the gaps | Chotu page tool |
| 1 | Order PDFs: text + OCR with page numbers, so every quote carries a page | Tura `doc_text` / `legal_agent/ocr.py` |
| 1 | Hearing brief: one click on the case page runs the `hearing-brief` agent | `runtime/agents/hearing-brief` |
| 1 | Indian legal research attached to a case: verify citation → find judgment → read → cite only what was read (see `mike-study.md`) | Tura `legal_agent` research tools, `doc_intel` grammars, Mike's loop (ideas) |
| 1 | Drafting from templates (adjournment application, bail application, written submissions), with a pause for missing facts | Tura `legal_agent/drafting.py`, Mike's `ask_inputs` idea |
| 2 | Firm diary: teams, matter access, audit trail, assignment of directions | Mike's orgs/grants/audit (ideas only) |
| 2 | Morning digest on WhatsApp / email | Tura messaging |
| 2 | Case folder: link a folder, index filings, cite them | Tura `legal_agent` store + `doc_intel` |
| 3 | Tabular review in Sheets (see `sheets-and-excel.md`) | Tura Sheets (GenOffice, Apache-2.0) + Mike's idea |
| 3 | Drafting with Word | Tura `legal_agent/drafting.py`, Mike's add-in idea |
| 3 | Dhee as context compiler per case | Dhee |
