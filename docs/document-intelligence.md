# Manu document intelligence

> Carried over from Tura (`docs/manu-document-intelligence.md`). Module paths below refer to
> Tura; in this repository the grammars live in `src/manu/doc_intel/`.

What turns a folder of filings into a case file an advocate can rely on: classify each
document, pull its attributes out, and carry a citation with every fact so nothing in the
case file is unsourced.

This is the lifeline of the product. The draft section is downstream of it — a plaint
cannot have a correct cause title until we know the court, the case number and how each
party is described, and those come from here.

## Studied, not copied

paperless-ngx solves the general form of this problem well, and it is AGPL-3.0. We cannot
take its code. Techniques and architecture are not what copyright protects, so what
follows is a record of which of their design decisions we adopted, which we inverted, and
why — written from reading their `classifier.py`, `matching.py` and `consumer.py`. No
paperless code is vendored, translated or transcribed anywhere in Manu.

### Adopted

- **Rules and a model, not one or the other.** They pair deterministic matching modes
  (literal, word-boundary all/any, regex, fuzzy) with a learned classifier. A single
  approach fails: pure rules miss everything unanticipated, pure inference cannot be
  explained to the person who has to sign the filing.
- **Word boundaries, never substrings.** Their non-fuzzy modes all match on `\b`. Without
  it, "IA" hits "trial", "SC" hits "SCC".
- **Fuzzy matching for scanned text.** They use `partial_ratio` at 90 on
  punctuation-stripped text. OCR of an Indian court scan produces exactly the noise this
  absorbs — `ORDER` as `0RDER`, `Hon'ble` as `Honble`.
- **Version the extractor, digest the inputs, skip the unchanged.** They avoid retraining
  by comparing a stored timestamp and an HMAC of the training set against the current
  ones. We apply the same idea to re-indexing: a file whose content hash and extractor
  version are unchanged is not re-read. This is what makes "re-index the folder" cheap
  enough to run on every open.
- **An ordered pipeline of small stages** with explicit contracts, rather than one
  function that does everything.

### Inverted, with reasons

- **Failure is per document, not per intake.** They abort the whole consume on any stage
  failure, because a document row without its file is worse than no row. Our unit is a
  case folder of two hundred files, and one unreadable scan must not stop the other
  hundred and ninety-nine from becoming citable. Each document carries its own failure.
- **Rules outrank the model; the model may abstain.** Their `MATCH_AUTO` lets the
  classifier decide. We reverse the precedence: a document that says
  "MEMORANDUM OF APPEAL UNDER SECTION 374(2) OF THE CODE OF CRIMINAL PROCEDURE" is an
  appeal memo as a matter of fact, and no inference should be able to overrule that. Below
  a confidence floor the model returns nothing rather than a guess, because an advocate
  can work with "unclassified" and cannot work with "written statement" when it is a
  counter-affidavit.
- **Every attribute carries a citation.** They store attributes bare. We store
  `(relative_path, start, end, page)` with each one, so the case file has no fact an
  advocate cannot click through to the line that says it. This is the difference between
  a summary and a work product.

## Where deterministic extraction is right, and where it is not

Manu's standing rule is no regex routers — intent must never be pattern-matched into a
hardcoded workflow. That rule is about *intent*, and it stands.

Document *formats* are a different thing. A CNR is a specified 16-character identifier:
two letters of state, two of district, two of establishment, six digits of sequence, four
of year — `DLST010012342024`. A citation is `(2020) 5 SCC 1`. These are grammars published
by the courts, not guesses about what someone meant. For them a deterministic extractor is
both more accurate than a model and auditable, which is what an advocate needs.

So the split is:

| Layer | Method | Why |
| --- | --- | --- |
| Identifiers — CNR, case number, citations, statute references | deterministic grammar | published formats; exactness matters and is checkable |
| Dates and their roles — filed, heard, ordered, next listed | deterministic candidates, model assigns the role | finding "12 August 2026" is mechanical; knowing it is the *next hearing* is reading |
| Document kind | rules first, model for the remainder | a title line is proof; prose needs judgement |
| Parties and how each is described | model, over an extracted cause-title region | "Ramesh Sharma … APPELLANT" is prose with a shape, not a format |
| Holdings, relief, admissions | model only | reading |

## Pipeline

Per file, in order, each stage recording its own failure without stopping the rest:

1. **Fingerprint** — sha256 of bytes. Unchanged hash plus unchanged extractor version means
   skip; this is what makes re-indexing on demand affordable. It also collapses the
   duplicates every case folder carries (`order copy 2.pdf`).
2. **Text with page spans** — existing extraction, OCR when there is no text layer, page
   spans preserved so a char offset can become a page number.
3. **Region split** — cause title, body, prayer, verification. Most attributes live in a
   known region, and searching the right region beats searching the file.
4. **Identifiers** — deterministic grammars over the whole text.
5. **Kind** — rules over title lines and statute references; model for what is left.
6. **Attributes** — per kind, because what matters differs: an order has a date and what it
   held; a deposition has a witness and whether they were declared hostile.
7. **Cite** — resolve every extracted value to a char span and page in its file.

## Case file assembly

The case file stops reading from what was typed at import. Each field takes the
highest-confidence cited extraction across the folder, and shows its source. Where two
documents disagree — a hearing date in an old order and a newer one — the later document
wins and the conflict is kept, because an advocate needs to know the diary changed.

## Draft section

A draft is only as good as the attributes under it. With extraction in place a draft can
be assembled from facts rather than prompts: the cause title from the extracted court,
case number and party descriptions; the statutory framing from the provision the matter is
actually under; the facts paragraph-wise with a citation on each; the annexure index from
the documents that exist. Until then the draft section produces a checklist and a brief,
which is not something an advocate can file.
