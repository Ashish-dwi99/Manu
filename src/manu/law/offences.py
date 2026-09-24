"""Offence → punishment, for the two penal codes an Indian criminal court works under today.

The code that governs an offence is fixed by the date it was committed, not the date of
the hearing. The Bharatiya Nyaya Sanhita, 2023 commenced on 1 July 2024; an offence
committed before that is charged, tried and punished under the Indian Penal Code, 1860
(BNS s.358, savings), and Article 20(1) forbids a heavier penalty than the law in force
when the act was done.

This matters to every number downstream. A Section 479 BNSS threshold is a fraction of
the *maximum* sentence, and the maxima moved between codes: criminal breach of trust
was 3 years under IPC s.406 and is 5 under BNS s.316(2); extortion was 3 under IPC s.384
and is 7 under BNS s.308(2). Reading the wrong code misstates when an undertrial must be
released.

The section numbers also moved, which is how records go wrong: "Sec. 379 BNS" is not
theft (theft is BNS s.303), it is IPC s.379 written with the wrong code. `resolve_charge`
catches exactly that.

**Every row here is `reviewed=False` until an advocate has checked it against the Bare
Act and recorded their name.** The table is small on purpose. A missing offence is shown
as a gap; an invented one would be worse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

PenalCode = Literal["IPC", "BNS"]

BNS_COMMENCEMENT = date(2024, 7, 1)


def penal_code_for(offence_date: date) -> PenalCode:
    """The penal code that governs an offence committed on `offence_date`."""
    return "BNS" if offence_date >= BNS_COMMENCEMENT else "IPC"


@dataclass(frozen=True, slots=True)
class Punishment:
    """The statutory ceiling (and floor, where one exists) for one offence."""

    max_years: float | None
    """Longest fixed term. None only when the ceiling is life or death."""
    min_years: float | None = None
    life: bool = False
    death: bool = False
    aggravated_note: str = ""
    """A factual condition that raises the ceiling, e.g. robbery on a highway at night.
    The calculator cannot see facts, so it surfaces this rather than assuming either way."""

    @property
    def max_is_life_or_death(self) -> bool:
        return self.life or self.death


@dataclass(frozen=True, slots=True)
class Offence:
    code: PenalCode
    section: str
    title: str
    punishment: Punishment
    counterpart: str
    """The same offence in the other code, e.g. "BNS 303(2)" for IPC 379."""
    reviewed: bool = False
    reviewed_by: str = ""

    @property
    def key(self) -> str:
        return f"{self.code} {self.section}"


def _p(max_years: float | None, **kwargs) -> Punishment:
    return Punishment(max_years=max_years, **kwargs)


_ROWS: tuple[Offence, ...] = (
    # Property
    Offence("IPC", "379", "Theft", _p(3), "BNS 303(2)"),
    Offence(
        "BNS", "303(2)", "Theft", _p(3, aggravated_note="Second or subsequent conviction: RI 1 to 5 years."), "IPC 379"
    ),
    Offence("IPC", "411", "Dishonestly receiving stolen property", _p(3), "BNS 317(2)"),
    Offence("BNS", "317(2)", "Dishonestly receiving stolen property", _p(3), "IPC 411"),
    Offence("IPC", "406", "Criminal breach of trust", _p(3), "BNS 316(2)"),
    Offence("BNS", "316(2)", "Criminal breach of trust", _p(5), "IPC 406"),
    Offence("IPC", "420", "Cheating and dishonestly inducing delivery of property", _p(7), "BNS 318(4)"),
    Offence("BNS", "318(4)", "Cheating and dishonestly inducing delivery of property", _p(7), "IPC 420"),
    Offence("IPC", "384", "Extortion", _p(3), "BNS 308(2)"),
    Offence("BNS", "308(2)", "Extortion", _p(7), "IPC 384"),
    Offence(
        "IPC",
        "392",
        "Robbery",
        _p(10, aggravated_note="On a highway between sunset and sunrise: up to 14 years."),
        "BNS 309(4)",
    ),
    Offence(
        "BNS",
        "309(4)",
        "Robbery",
        _p(10, aggravated_note="On a highway between sunset and sunrise: up to 14 years."),
        "IPC 392",
    ),
    # Body
    Offence("IPC", "323", "Voluntarily causing hurt", _p(1), "BNS 115(2)"),
    Offence("BNS", "115(2)", "Voluntarily causing hurt", _p(1), "IPC 323"),
    Offence(
        "IPC",
        "307",
        "Attempt to murder",
        _p(10, aggravated_note="If hurt is caused: imprisonment for life."),
        "BNS 109(1)",
    ),
    Offence(
        "BNS",
        "109(1)",
        "Attempt to murder",
        _p(10, aggravated_note="If hurt is caused: imprisonment for life."),
        "IPC 307",
    ),
    Offence("IPC", "302", "Murder", _p(None, life=True, death=True), "BNS 103(1)"),
    Offence("BNS", "103(1)", "Murder", _p(None, life=True, death=True), "IPC 302"),
    Offence("IPC", "363", "Kidnapping", _p(7), "BNS 137(2)"),
    Offence("BNS", "137(2)", "Kidnapping", _p(7), "IPC 363"),
    Offence("IPC", "376(1)", "Rape", _p(None, min_years=10, life=True), "BNS 64(1)"),
    Offence("BNS", "64(1)", "Rape", _p(None, min_years=10, life=True), "IPC 376(1)"),
    # Home
    Offence("IPC", "498A", "Cruelty by husband or relatives", _p(3), "BNS 85"),
    Offence("BNS", "85", "Cruelty by husband or relatives", _p(3), "IPC 498A"),
    Offence("IPC", "304B", "Dowry death", _p(None, min_years=7, life=True), "BNS 80(2)"),
    Offence("BNS", "80(2)", "Dowry death", _p(None, min_years=7, life=True), "IPC 304B"),
    # Intimidation
    Offence(
        "IPC",
        "506",
        "Criminal intimidation",
        _p(2, aggravated_note="Threat to cause death or grievous hurt, etc.: up to 7 years."),
        "BNS 351(2)",
    ),
    Offence("BNS", "351(2)", "Criminal intimidation", _p(2), "IPC 506"),
    Offence("BNS", "351(3)", "Criminal intimidation (threat to cause death or grievous hurt, etc.)", _p(7), "IPC 506"),
)

OFFENCES: dict[str, Offence] = {row.key: row for row in _ROWS}


def lookup(code: PenalCode, section: str) -> Offence | None:
    return OFFENCES.get(f"{code} {_normalise_section(section)}")


def _normalise_section(section: str) -> str:
    return re.sub(r"[\s-]", "", str(section or "")).upper()


# "Sec. 379 BNS", "u/s 303(2) BNS", "S. 420 IPC", "section 498-A IPC", "IPC 379"
_CHARGE = re.compile(
    r"(?:(?P<code_first>IPC|BNS)\s*)?"
    r"(?:sec(?:tion)?s?\.?|s\.|u/s)?\s*"
    r"(?P<section>\d{1,3}(?:\s*-?\s*[A-Z](?![A-Z]))?(?:\s*\(\s*\d+\s*\))?)"
    r"\s*(?:of\s+(?:the\s+)?)?(?P<code_after>IPC|BNS)?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ResolvedCharge:
    raw: str
    offence: Offence | None
    """Exact match under the code that governs the offence date. Only this feeds a
    calculation."""
    governing_code: PenalCode | None
    suggested: Offence | None = None
    """What the record most likely meant when it does not match exactly. Shown to a
    person, never used to compute."""
    warnings: tuple[str, ...] = ()


def resolve_charge(raw: str, offence_date: date | None) -> ResolvedCharge:
    """Read one charge as written in a record and check it against the offence date.

    Never silently corrects. When the record is wrong — "Sec. 379 BNS" on a 2024 FIR —
    `offence` stays None, `suggested` names the likely offence (BNS 303(2), theft) and a
    warning says why, so the person reading it decides.
    """
    match = _CHARGE.search(raw or "")
    if not match:
        return ResolvedCharge(raw, None, None, warnings=(f"Could not read a section from “{raw}”.",))
    section = _normalise_section(match.group("section"))
    written = (match.group("code_first") or match.group("code_after") or "").upper() or None
    governing: PenalCode | None = penal_code_for(offence_date) if offence_date else None
    warnings: list[str] = []
    if offence_date is None:
        warnings.append("Offence date unknown: cannot tell whether IPC or BNS governs.")

    code = written or governing
    if code is None:
        return ResolvedCharge(raw, None, None, warnings=tuple(warnings + ["No penal code on the charge."]))

    as_written = lookup(code, section)  # type: ignore[arg-type]
    offence: Offence | None = None
    suggested: Offence | None = None

    if as_written is not None:
        if governing is None or as_written.code == governing:
            offence = as_written
        else:
            suggested = OFFENCES.get(as_written.counterpart)
            warnings.append(
                f"Charge is written under {as_written.code} but an offence on "
                f"{offence_date.isoformat()} is governed by {governing}"  # type: ignore[union-attr]
                + (f"; {as_written.key} corresponds to {suggested.key}." if suggested else ".")
            )
    else:
        other: PenalCode = "IPC" if code == "BNS" else "BNS"
        other_row = lookup(other, section)
        if other_row is not None:
            suggested = other_row if governing == other else OFFENCES.get(other_row.counterpart)
            warnings.append(
                f"{code} {section} is not {other_row.title.lower()}: that is {other_row.key}"
                f" (= {other_row.counterpart}). The record may have the wrong code."
            )
        else:
            warnings.append(f"{code} {section} is not in the offence table yet.")

    for row in (offence, suggested):
        if row is not None and not row.reviewed:
            warnings.append(f"{row.key} punishment row has not been reviewed by an advocate.")
    return ResolvedCharge(raw, offence, governing, suggested, tuple(warnings))
