"""Limitation: the last day to file, worked out the way the Limitation Act, 1963 counts.

An advocate asks one question after every adverse order: *by when must I file?* The
answer is arithmetic over a fixed table, and getting it wrong is not recoverable without
a condonation application. So it is code, with the working shown, and never a model.

How a period is counted here:

* **s.12(1)** — the day from which the period is reckoned is excluded. An order of
  1 January with 30 days gives 31 January.
* **s.12(2)** — for an appeal, revision or review, the time requisite for obtaining a
  certified copy of the decree, sentence or order is excluded. Manu excludes the days
  *from the date of application to the date the copy was ready*, not counting the day
  of application. Courts have also excluded that day; Manu takes the shorter count, so
  the date it shows is never later than the true last day. A copy applied for after the
  period has already run excludes nothing.
* **s.4** — when the last day falls on a day the court is closed, the filing may be
  made on the day it reopens. Manu knows Sundays; it does not know a court's holiday
  list, so it always says so and never moves a date for a holiday it cannot see.
* **s.5** — delay in an appeal or application may be condoned on sufficient cause. That
  is for the court; Manu only says when the period has run.

**Every rule is `reviewed=False` until an advocate has checked it against the Bare Act
and recorded their name**, the same discipline as the offence table. The table is small
on purpose: a missing rule is a gap the advocate sees, an invented one is a missed
deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

Group = Literal["civil", "criminal", "supreme_court", "pleadings"]
Status = Literal["running", "due_soon", "last_day", "extension_only", "expired"]

DUE_SOON_DAYS = 7

_OLD_CODE = (
    "The Schedule still names the old Code of Criminal Procedure; read it with the "
    "corresponding BNSS provision (appeals: BNSS ss.415, 419)."
)


@dataclass(frozen=True, slots=True)
class Rule:
    key: str
    title: str
    """What is being filed, as an advocate would say it."""
    group: Group
    provision: str
    days: int
    reckoned_from: str
    """The event the period runs from, in the provision's words."""
    copy_exclusion: bool = True
    """Whether s.12(2) excludes the time for obtaining a certified copy."""
    condonable: bool = True
    """Whether s.5 (or an equivalent power) lets the court condone delay."""
    outer_days: int | None = None
    """A longer outer limit the court may extend to, e.g. 90 days for a written statement."""
    notes: tuple[str, ...] = ()
    reviewed: bool = False
    reviewed_by: str = ""


RULES: dict[str, Rule] = {
    rule.key: rule
    for rule in (
        # Civil
        Rule(
            "civil_appeal_hc",
            "Appeal to the High Court from a decree or order",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 116(a)",
            90,
            "the date of the decree or order",
        ),
        Rule(
            "civil_appeal_other",
            "Appeal to a court other than the High Court from a decree or order",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 116(b)",
            30,
            "the date of the decree or order",
        ),
        Rule(
            "commercial_appeal",
            "Appeal under the Commercial Courts Act",
            "civil",
            "Commercial Courts Act, 2015, s.13(1A)",
            60,
            "the date of the judgment or order",
            notes=("Sections 4 to 24 of the Limitation Act apply to this special period through s.29(2).",),
        ),
        Rule(
            "review",
            "Review of a judgment (court other than the Supreme Court)",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 124",
            30,
            "the date of the decree or order",
        ),
        Rule(
            "revision",
            "Revision (civil or criminal)",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 131",
            90,
            "the date of the decree, order or sentence sought to be revised",
            notes=(_OLD_CODE,),
        ),
        Rule(
            "restore_default",
            "Restore a suit dismissed for default (O.IX r.9 CPC)",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 122",
            30,
            "the date of dismissal",
            copy_exclusion=False,
        ),
        Rule(
            "set_aside_ex_parte",
            "Set aside an ex parte decree (O.IX r.13 CPC)",
            "civil",
            "Limitation Act, 1963, Schedule, Art. 123",
            30,
            "the date of the decree",
            copy_exclusion=False,
            notes=(
                "Where summons was not duly served, time runs from when the applicant knew of the decree. "
                "Manu counts from the decree; if knowledge came later, enter that date instead.",
            ),
        ),
        # Criminal
        Rule(
            "crl_appeal_conviction_hc",
            "Appeal against conviction to the High Court (sentence other than death)",
            "criminal",
            "Limitation Act, 1963, Schedule, Art. 115(b)(ii)",
            60,
            "the date of the sentence or order",
            notes=(_OLD_CODE,),
        ),
        Rule(
            "crl_appeal_conviction_other",
            "Appeal against conviction to a court other than the High Court",
            "criminal",
            "Limitation Act, 1963, Schedule, Art. 115(c)",
            30,
            "the date of the sentence or order",
            notes=(_OLD_CODE,),
        ),
        Rule(
            "crl_appeal_death",
            "Appeal from a sentence of death",
            "criminal",
            "Limitation Act, 1963, Schedule, Art. 115(a), (b)(i)",
            30,
            "the date of the sentence",
            notes=(_OLD_CODE,),
        ),
        Rule(
            "crl_appeal_acquittal_state",
            "Appeal by the State against acquittal",
            "criminal",
            "Limitation Act, 1963, Schedule, Art. 114(a)",
            90,
            "the date of the order appealed from",
            notes=(_OLD_CODE,),
        ),
        # Supreme Court
        Rule(
            "slp",
            "Special leave petition to the Supreme Court",
            "supreme_court",
            "Supreme Court Rules, 2013, O.XXI r.1 (civil) and O.XXII r.2 (criminal)",
            90,
            "the date of the judgment or order sought to be appealed",
            notes=(
                "Where a certificate of fitness was refused, the period is 60 days from the order refusing it. "
                "Choose that order as the start and check the rule.",
            ),
        ),
        # Pleadings
        Rule(
            "written_statement",
            "Written statement (civil suit)",
            "pleadings",
            "CPC, O.VIII r.1",
            30,
            "the date of service of summons",
            copy_exclusion=False,
            condonable=False,
            outer_days=90,
            notes=("The court may allow up to 90 days from service, for reasons recorded in writing.",),
        ),
        Rule(
            "written_statement_commercial",
            "Written statement (commercial suit)",
            "pleadings",
            "CPC, O.VIII r.1 proviso, as amended by the Commercial Courts Act, 2015",
            30,
            "the date of service of summons",
            copy_exclusion=False,
            condonable=False,
            outer_days=120,
            notes=(
                "The court may allow up to 120 days, on costs; after 120 days the right to file is forfeited "
                "and the court cannot take the written statement on record.",
            ),
        ),
    )
}


@dataclass(slots=True)
class LimitationResult:
    rule: Rule
    start: date
    as_of: date
    last_day: date
    """The last day on the statute's count, after s.12 exclusions."""
    file_by: date
    """`last_day`, moved past a Sunday under s.4. Holidays are not known."""
    outer_day: date | None = None
    excluded_days: int = 0
    days_left: int = 0
    status: Status = "running"
    working: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


def _d(value: date) -> str:
    return value.isoformat()


def compute(
    rule_key: str,
    start: date,
    *,
    as_of: date,
    copy_applied: date | None = None,
    copy_ready: date | None = None,
) -> LimitationResult:
    """The last day to file under `rule_key`, counted from `start`.

    `copy_applied` and `copy_ready` are the dates a certified copy was applied for and
    made ready. They are facts a person enters; Manu never guesses them.
    """
    rule = RULES.get(rule_key)
    if rule is None:
        raise KeyError(f"unknown limitation rule {rule_key!r}")

    working = [
        f"{rule.provision}: {rule.days} days from {rule.reckoned_from}.",
        f"Reckoned from {_d(start)}; that day is excluded (s.12(1)).",
    ]
    flags: list[str] = []
    gaps: list[str] = []
    raw_last = start + timedelta(days=rule.days)

    excluded = 0
    if rule.copy_exclusion:
        if copy_applied and copy_ready:
            if copy_ready < copy_applied or copy_applied < start:
                gaps.append("The copy dates are out of order; check them. Nothing was excluded.")
            elif copy_applied > raw_last:
                flags.append(
                    f"The copy was applied for on {_d(copy_applied)}, after the period ran out on {_d(raw_last)}; "
                    "s.12(2) excludes nothing for it."
                )
            else:
                excluded = (copy_ready - copy_applied).days
                working.append(
                    f"Certified copy applied {_d(copy_applied)}, ready {_d(copy_ready)}: "
                    f"{excluded} days excluded (s.12(2)), counted short so the date is never late."
                )
        elif copy_applied and not copy_ready:
            gaps.append("The copy is not ready yet. The date grows by one day for each day it stays pending.")
        elif copy_ready and not copy_applied:
            gaps.append("Enter the date the copy was applied for; without it no time is excluded.")
        else:
            working.append("No certified-copy dates entered, so no time is excluded under s.12(2).")
    else:
        working.append("No certified-copy exclusion applies to this period.")

    last_day = raw_last + timedelta(days=excluded)
    working.append(f"Last day: {_d(last_day)}.")

    file_by = last_day
    if last_day.weekday() == 6:
        file_by = last_day + timedelta(days=1)
        working.append(
            f"{_d(last_day)} is a Sunday. If the court is closed, s.4 allows filing on the day it reopens: "
            f"{_d(file_by)} if open."
        )
    flags.append("Manu does not know this court's holiday list. If the last day is a holiday, s.4 applies.")

    outer_day = None
    if rule.outer_days:
        outer_day = start + timedelta(days=rule.outer_days)
        working.append(f"Outer limit, if the court extends time: {_d(outer_day)} ({rule.outer_days} days).")

    flags.extend(rule.notes)
    if not rule.reviewed:
        flags.append(f"This rule ({rule.provision}) has not yet been reviewed by an advocate against the Bare Act.")

    days_left = (file_by - as_of).days
    if days_left < 0 and outer_day and as_of <= outer_day:
        status: Status = "extension_only"
        days_left = (outer_day - as_of).days
        flags.append(f"The first period has run. Only the court can allow filing now, and not after {_d(outer_day)}.")
    elif days_left < 0:
        status = "expired"
        if rule.condonable:
            flags.append("The period has run. Delay may be condoned under s.5 on sufficient cause; that is for the court.")
    elif days_left == 0:
        status = "last_day"
    elif days_left <= DUE_SOON_DAYS:
        status = "due_soon"
    else:
        status = "running"

    return LimitationResult(
        rule=rule,
        start=start,
        as_of=as_of,
        last_day=last_day,
        file_by=file_by,
        outer_day=outer_day,
        excluded_days=excluded,
        days_left=days_left,
        status=status,
        working=working,
        flags=flags,
        gaps=gaps,
    )
