# The law engine

Everything in `src/manu/law` is fixed-rule arithmetic over statute. It never calls a
model, gives the same answer every time, and returns its working line by line so the
person acting on it can check it.

## Which code governs

`offences.penal_code_for(offence_date)`: BNS for offences on or after 1 July 2024, IPC
before (BNS s.358 savings; Art. 20(1)). Maxima moved between codes. For example, criminal
breach of trust was 3 years under IPC s.406 and is 5 years under BNS s.316(2). So the
code must be right before any threshold is computed.

`offences.resolve_charge(text, offence_date)` reads a charge as written and returns:

* `offence`: an exact match under the governing code. Only this is used in calculations.
* `suggested`: what the record probably meant, e.g. "Sec. 379 BNS" on a 2024 FIR →
  BNS 303(2) (theft; 379 is the IPC number). This is shown to a person and never used in a
  calculation.
* `warnings`: every mismatch, in words.

**The offence table is small and every row is `reviewed=False`.** Before any pilot, an
advocate checks each row against the Bare Act and records their name in `reviewed_by`.
The UI shows unreviewed rows.

## Section 479 BNSS (`s479.assess`)

* Offences punishable with death or life imprisonment → not applicable.
* Threshold: one-third of the maximum for a first-time offender, one-half otherwise,
  measured in calendar months from first remand. When first-offender status is unknown,
  it alerts on one-third, the earlier date, and reports the gap.
* Detention: sum of custody spans, remand day included, less delay attributed to the
  accused (Explanation). The deduction is disclosed as a flag.
* s.479(2) (multiple cases / more than one offence) is **flagged for the court**. It never
  hides an alert. Whether several sections in one FIR attract it is a question of law.
* Alert window: 7 days before the threshold (JudgeDesk PRD). Also flags
  `maximum_exceeded`.
* Applies to pre-July-2024 cases too (SC, Aug 2024, *In Re: Inhuman Conditions in 1382
  Prisons*), with the IPC maximum.

## Default bail (`default_bail.assess`)

* BNSS s.187(3) / CrPC s.167(2): 90 days for offences punishable with death, life, or ten
  years or more; 60 days otherwise.
* Remand day is day 1 (*ED v. Kapil Wadhawan*, 2023). The right accrues the day after
  the period ends.
* A ceiling of exactly ten years with a lower minimum (robbery, attempt to murder
  without hurt) is flagged with both dates. The courts have read this differently
  (*Rakesh Kumar Paul*, 2017).
* A chargesheet filed before accrual extinguishes the right. A chargesheet filed after
  accrual is flagged: the outcome depends on whether the right was claimed first.
* Special statutes (NDPS s.36A, UAPA s.43D…) → `needs_review`.

## Corrections to the JudgeDesk demo data

* "Sec. 379 BNS" / "Sec. 411 BNS" are IPC numbers. Theft is BNS 303(2); receiving
  stolen property is BNS 317(2).
* The PRD's 479 example shows an alert 183 days before the threshold, but its own rule is
  7 days. Manu follows the rule and shows the percentage served.
