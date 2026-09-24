"""Section 479 BNSS: when an undertrial must be released.

Section 479(1), Bharatiya Nagarik Suraksha Sanhita, 2023:

* an undertrial who has been detained for up to **one-half** of the maximum period of
  imprisonment for the offence shall be released on bail by the court;
* a **first-time offender** (never convicted of any offence) shall be released on bond
  after **one-third**;
* the section does not apply to offences punishable with **death or imprisonment for
  life**;
* no undertrial may be detained beyond the maximum period itself.

Section 479(2): where investigation, inquiry or trial "in more than one offence or in
multiple cases" is pending, the person shall not be released on bail under this section.
The Explanation excludes detention caused by the accused's own delay. Section 479(3)
puts the duty to apply on the jail superintendent.

The Supreme Court directed in August 2024 (*In Re: Inhuman Conditions in 1382 Prisons*,
W.P.(C) 406/2013) that the first-time-offender proviso applies to undertrials in cases
registered before 1 July 2024 as well. For those cases the maximum sentence is the one
under the IPC, which governs the offence — see `offences.penal_code_for`.

This module computes; it never decides. Section 479(2) and delay attributable to the
accused are questions for the judge, so they are surfaced as flags, not used to hide an
alert. A missing input is reported as a gap and the computation shows its working.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from manu.law.offences import Offence

ALERT_WINDOW_DAYS = 7
"""JudgeDesk PRD: raise the alert this many days before a threshold is crossed."""

Status = Literal[
    "not_applicable",
    "insufficient_data",
    "not_yet",
    "approaching",
    "crossed",
    "maximum_exceeded",
]


@dataclass(frozen=True, slots=True)
class CustodyPeriod:
    start: date
    end: date | None = None
    """None while the person is still in custody."""

    def days(self, as_of: date) -> int:
        """Days detained, counting both the day of remand and the last day."""
        last = min(self.end or as_of, as_of)
        if last < self.start:
            return 0
        return (last - self.start).days + 1


@dataclass(frozen=True, slots=True)
class Threshold:
    ratio_label: Literal["one-third", "one-half", "maximum"]
    months: int
    days: int
    crossing_date: date
    days_remaining: int


@dataclass(slots=True)
class S479Result:
    status: Status
    as_of: date
    days_detained: int = 0
    excluded_delay_days: int = 0
    max_offence: Offence | None = None
    applicable: Threshold | None = None
    """The threshold that drives the alert: one-third for a first-time offender, and
    also one-third when that status is unknown — the earliest date on which release may
    become mandatory is the one a court cannot afford to miss."""
    other_thresholds: list[Threshold] = field(default_factory=list)
    percent_of_applicable: float | None = None
    flags: list[str] = field(default_factory=list)
    """Things the judge must decide: 479(2), delay, aggravating facts, unreviewed rows."""
    gaps: list[str] = field(default_factory=list)
    working: list[str] = field(default_factory=list)

    @property
    def alert(self) -> bool:
        return self.status in {"approaching", "crossed", "maximum_exceeded"}


def _add_months(start: date, months: int) -> date:
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    # Clamp to the month's last day: 31 Jan + 1 month is 28/29 Feb, not 3 Mar.
    for day in (start.day, 30, 29, 28):
        try:
            return date(year, month, day)
        except ValueError:
            continue
    raise ValueError("unreachable")


def assess(
    *,
    offences: list[Offence],
    custody: list[CustodyPeriod],
    as_of: date,
    first_offender: bool | None,
    other_pending_cases: int | None = None,
    excluded_delay_days: int = 0,
    alert_window_days: int = ALERT_WINDOW_DAYS,
) -> S479Result:
    """Where an undertrial stands against Section 479 on `as_of`."""
    result = S479Result(status="insufficient_data", as_of=as_of, excluded_delay_days=excluded_delay_days)

    if not offences:
        result.gaps.append("No charged offence could be matched to the offence table.")
        return result
    if any(o.punishment.max_is_life_or_death for o in offences):
        capital = next(o for o in offences if o.punishment.max_is_life_or_death)
        result.status = "not_applicable"
        result.max_offence = capital
        result.working.append(
            f"{capital.key} ({capital.title}) is punishable with death or life imprisonment: s.479 does not apply."
        )
        return result
    if not custody:
        result.gaps.append("No custody start date (remand) on record.")
        return result

    max_offence = max(offences, key=lambda o: o.punishment.max_years or 0)
    max_years = max_offence.punishment.max_years or 0
    result.max_offence = max_offence
    max_months = round(max_years * 12)

    gross = sum(period.days(as_of) for period in custody)
    net = max(0, gross - max(0, excluded_delay_days))
    result.days_detained = net

    anchor = min(period.start for period in custody)
    thresholds: dict[str, Threshold] = {}
    for label, months in (("one-third", max_months // 3), ("one-half", max_months // 2), ("maximum", max_months)):
        # A threshold is a period of time ("one-half of the maximum period"), so it is
        # measured in calendar months from the first remand and converted to days once.
        # Custody that was broken is then compared day for day against that length.
        span = (_add_months(anchor, months) - anchor).days
        remaining = span - net
        thresholds[label] = Threshold(label, months, span, as_of + timedelta(days=max(remaining, 0)), remaining)  # type: ignore[arg-type]

    result.working.append(f"Maximum sentence: {max_years:g} years under {max_offence.key} ({max_offence.title}).")
    result.working.append(
        f"Detained {gross} days from {anchor.isoformat()} to {as_of.isoformat()}"
        + (f", less {excluded_delay_days} days of delay attributed to the accused" if excluded_delay_days else "")
        + f" = {net} days."
    )

    if first_offender is True:
        applicable = thresholds["one-third"]
        result.other_thresholds = [thresholds["one-half"]]
    elif first_offender is False:
        applicable = thresholds["one-half"]
    else:
        applicable = thresholds["one-third"]
        result.other_thresholds = [thresholds["one-half"]]
        result.gaps.append(
            "First-time offender status is not verified (antecedent report). "
            f"One-third falls on {thresholds['one-third'].crossing_date.isoformat()}, "
            f"one-half on {thresholds['one-half'].crossing_date.isoformat()}."
        )
    result.applicable = applicable
    result.percent_of_applicable = round(100 * net / applicable.days, 1) if applicable.days else None
    result.working.append(
        f"{applicable.ratio_label.capitalize()} of {max_months} months = {applicable.months} months = {applicable.days} days."
    )

    maximum = thresholds["maximum"]
    if maximum.days_remaining <= 0:
        result.status = "maximum_exceeded"
        result.working.append("Detention has reached the maximum period of imprisonment for the offence.")
    elif applicable.days_remaining <= 0:
        result.status = "crossed"
        result.working.append(f"Threshold crossed {-applicable.days_remaining} days ago.")
    elif applicable.days_remaining <= alert_window_days:
        result.status = "approaching"
        result.working.append(
            f"Threshold will be crossed in {applicable.days_remaining} days, on {applicable.crossing_date.isoformat()}."
        )
    else:
        result.status = "not_yet"
        result.working.append(
            f"{applicable.days_remaining} days to the threshold, on {applicable.crossing_date.isoformat()}."
        )

    if other_pending_cases is None:
        result.gaps.append("Other pending cases against the accused are not known (s.479(2)).")
    elif other_pending_cases > 0:
        result.flags.append(
            f"s.479(2): {other_pending_cases} other case(s) pending against the accused — "
            "release on bail under this section is barred by statute. Verify."
        )
    if len(offences) > 1:
        result.flags.append(
            "s.479(2) refers to investigation, inquiry or trial “in more than one offence”. "
            "Whether multiple sections in one FIR attract it is for the court to decide."
        )
    if excluded_delay_days:
        result.flags.append(
            f"{excluded_delay_days} days excluded as delay caused by the accused (Explanation to s.479). Confirm the order recording it."
        )
    for offence in offences:
        if offence.punishment.aggravated_note:
            result.flags.append(
                f"{offence.key}: {offence.punishment.aggravated_note} The computation uses the ordinary maximum."
            )
        if not offence.reviewed:
            result.flags.append(f"{offence.key}: punishment row not yet reviewed by an advocate.")
    return result
