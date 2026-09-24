"""Default ("statutory") bail: the right that accrues when police do not file in time.

Section 187(3) BNSS (earlier s.167(2) CrPC, same periods): if the investigation is not
completed and the final report (chargesheet) is not filed within

* **90 days**, where the investigation relates to an offence punishable with death,
  imprisonment for life, or imprisonment for a term of ten years or more, or
* **60 days**, for any other offence,

the accused is entitled to be released on bail if prepared to furnish it. The right is
indefeasible once it accrues and is claimed, and is lost if the chargesheet is filed
before it is claimed.

The day of remand counts as day one (*Enforcement Directorate v. Kapil Wadhawan*, 2023).
So on a 60-day period the right accrues on the 61st day.

Offences whose ceiling is exactly ten years but whose minimum is lower (robbery,
attempt to murder without hurt) are where the courts have read the words differently
(*Rakesh Kumar Paul v. State of Assam*, 2017, under the CrPC's "not less than ten years").
This module does not pick a side: it reports both dates and flags the question.

Special statutes (NDPS s.36A, UAPA s.43D, and others) extend these periods and are
outside this calculator; a case flagged `special_statute` is always sent for review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from manu.law.offences import Offence

ALERT_WINDOW_DAYS = 7

Status = Literal[
    "not_applicable",
    "insufficient_data",
    "not_yet",
    "approaching",
    "accrued",
    "chargesheet_filed",
    "needs_review",
]


@dataclass(slots=True)
class DefaultBailResult:
    status: Status
    as_of: date
    period_days: int | None = None
    accrual_date: date | None = None
    alternative_accrual_date: date | None = None
    days_remaining: int | None = None
    flags: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    working: list[str] = field(default_factory=list)

    @property
    def alert(self) -> bool:
        return self.status in {"approaching", "accrued"}


def _period(offence: Offence) -> tuple[int, bool]:
    """(days, ambiguous) for one offence."""
    p = offence.punishment
    if p.life or p.death:
        return 90, False
    if (p.min_years or 0) >= 10:
        return 90, False
    if (p.max_years or 0) >= 10:
        return 90, True
    return 60, False


def assess(
    *,
    offences: list[Offence],
    first_remand: date | None,
    as_of: date,
    chargesheet_filed_on: date | None,
    in_custody: bool,
    special_statute: bool = False,
    alert_window_days: int = ALERT_WINDOW_DAYS,
) -> DefaultBailResult:
    result = DefaultBailResult(status="insufficient_data", as_of=as_of)
    if not in_custody:
        result.status = "not_applicable"
        result.working.append("Accused is not in custody.")
        return result
    if special_statute:
        result.status = "needs_review"
        result.flags.append("A special statute may extend the investigation period (e.g. NDPS s.36A, UAPA s.43D).")
        return result
    if first_remand is None:
        result.gaps.append("First remand date is not on record.")
        return result
    if not offences:
        result.gaps.append("No charged offence could be matched to the offence table.")
        return result

    periods = [_period(o) for o in offences]
    period = max(days for days, _ in periods)
    ambiguous = period == 90 and all(amb for days, amb in periods if days == 90)
    result.period_days = period
    # Remand day is day 1, so the period ends on remand + (period - 1); the right
    # accrues the next day.
    result.accrual_date = first_remand + timedelta(days=period)
    result.working.append(
        f"First remand {first_remand.isoformat()} (day 1). {period}-day period ends "
        f"{(first_remand + timedelta(days=period - 1)).isoformat()}; right accrues {result.accrual_date.isoformat()}."
    )
    if ambiguous:
        result.alternative_accrual_date = first_remand + timedelta(days=60)
        result.flags.append(
            "Maximum sentence is exactly ten years with a lower minimum: whether 60 or 90 days applies "
            f"is a question of law (Rakesh Kumar Paul, 2017). 60-day accrual would be {result.alternative_accrual_date.isoformat()}."
        )

    if chargesheet_filed_on is not None:
        if chargesheet_filed_on < result.accrual_date:
            result.status = "chargesheet_filed"
            result.working.append(f"Chargesheet filed {chargesheet_filed_on.isoformat()}, before the right accrued.")
            return result
        result.flags.append(
            f"Chargesheet filed {chargesheet_filed_on.isoformat()}, after the right accrued on "
            f"{result.accrual_date.isoformat()}. Whether it was claimed before filing decides whether it survives."
        )

    earliest = min(d for d in (result.accrual_date, result.alternative_accrual_date) if d)
    remaining = (earliest - as_of).days
    result.days_remaining = remaining
    if remaining <= 0:
        result.status = "accrued" if chargesheet_filed_on is None else "needs_review"
    elif remaining <= alert_window_days:
        result.status = "approaching"
    else:
        result.status = "not_yet"
    return result
