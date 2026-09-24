# JudgeDesk in Manu

JudgeDesk (`Ashish-dwi99/JudgeDesk`) is a PRD and a Next.js prototype of a decision-support
dashboard for Sessions judges (pilot: South District, Saket). In Manu it is not a separate
product, and not a separate mode either: a judge uses the same case OS as an advocate. The
cause list is the day's list; liberty labels and the arithmetic are on every case for everyone.

## What carried over

| JudgeDesk | Manu |
| --- | --- |
| Cause list with smart labels | Today's list, for every user: 479 ALERT, BAIL, URGENT, WOMAN, JUVENILE, plus DATA GAP |
| Custody column | Days in custody on each row |
| Case detail: header, timeline, last order, action panel | Case page: header + labels, next hearing, last order with the text, directions with sources, timeline, history |
| Section 479 alert with computation | Section 479 block with the working, flags and gaps (`law/s479.py`) |
| BailScore (six factors) | **Bail facts**, the same six factors, each with its source or "Data unavailable". Renamed: it is not a score |
| "Judge decides, system supports" | Enforced: no recommendation anywhere; law is fixed-rule code; statutory questions are flagged, not decided |
| "Show gaps clearly" | Every factor carries its gaps; unmatched charges get a DATA GAP label |
| Similar cases (post-MVP) | Not built. It needs a court's own decided-bail data and a privacy review first |

## What changed and why

* **Default bail** (BNSS s.187(3)) was added to the URGENT label. The PRD names it and
  it is the most time-critical liberty date after s.479.
* **Offence data is checked, not trusted.** The prototype's demo cases use IPC section
  numbers labelled BNS. Manu resolves each charge against the offence date and says when a
  record is wrong (`law/offences.py`).
* **Data sources.** CIS/e-Courts come through the connector ladder. ePrisons and CCTNS
  (via ICJS) need institutional access; until then custody and antecedents come from the
  record and missing data is shown as a gap.
