"""The judge's view of a case: labels, liberty thresholds, and the facts a bail hearing needs.

From the JudgeDesk PRD, and held to its first rule: **the judge decides, the system
supports.** Nothing here recommends grant or rejection or scores an accused. It lays out
the statutory arithmetic and the facts, says where each came from, and says plainly what
is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from manu.case_state.models import Accused, Case
from manu.law import default_bail, s479
from manu.law.offences import Offence, ResolvedCharge, resolve_charge

LabelCode = Literal["479 ALERT", "BAIL", "URGENT", "WOMAN", "JUVENILE", "DATA GAP"]
Tone = Literal["red", "blue", "amber", "purple", "green", "gray"]

_TONES: dict[str, Tone] = {
    "479 ALERT": "red",
    "BAIL": "blue",
    "URGENT": "amber",
    "WOMAN": "purple",
    "JUVENILE": "green",
    "DATA GAP": "gray",
}


@dataclass(frozen=True, slots=True)
class Label:
    code: LabelCode
    reason: str

    @property
    def tone(self) -> Tone:
        return _TONES[self.code]

    def as_dict(self) -> dict:
        return {"code": self.code, "tone": self.tone, "reason": self.reason}


@dataclass(slots=True)
class AccusedAssessment:
    accused: Accused
    s479: s479.S479Result
    default_bail: default_bail.DefaultBailResult


@dataclass(slots=True)
class CriminalAssessment:
    charges: list[ResolvedCharge]
    offences: list[Offence]
    accused: list[AccusedAssessment] = field(default_factory=list)


def assess_case(case: Case, as_of: date) -> CriminalAssessment | None:
    if case.case_type != "criminal":
        return None
    charges = [resolve_charge(c.text, c.offence_date) for c in case.charges]
    offences = [c.offence for c in charges if c.offence is not None]
    result = CriminalAssessment(charges=charges, offences=offences)
    for person in case.accused:
        spans = [s479.CustodyPeriod(s.start, s.end) for s in person.custody]
        first_remand = min((s.start for s in person.custody), default=None)
        result.accused.append(
            AccusedAssessment(
                accused=person,
                s479=s479.assess(
                    offences=offences,
                    custody=spans,
                    as_of=as_of,
                    first_offender=person.first_offender,
                    other_pending_cases=person.other_pending_cases,
                    excluded_delay_days=person.delay_attributable_days,
                ),
                default_bail=default_bail.assess(
                    offences=offences,
                    first_remand=first_remand,
                    as_of=as_of,
                    chargesheet_filed_on=case.chargesheet_filed_on,
                    in_custody=person.in_custody,
                    special_statute=case.special_statute,
                ),
            )
        )
    return result


def labels(case: Case, as_of: date, assessment: CriminalAssessment | None = None) -> list[Label]:
    assessment = assessment if assessment is not None else assess_case(case, as_of)
    out: list[Label] = []
    if assessment:
        for item in assessment.accused:
            name = item.accused.name
            if item.accused.in_custody and item.s479.alert:
                out.append(
                    Label("479 ALERT", f"{name}: {item.s479.working[-1] if item.s479.working else item.s479.status}")
                )
            if item.default_bail.alert and item.default_bail.accrual_date:
                out.append(
                    Label(
                        "URGENT",
                        f"{name}: default bail {item.default_bail.status} ({item.default_bail.accrual_date.isoformat()}).",
                    )
                )
            if item.accused.in_custody and item.accused.gender == "female":
                out.append(Label("WOMAN", f"{name} is in custody."))
            if item.accused.juvenile:
                out.append(Label("JUVENILE", f"{name} is recorded as a juvenile."))
        unmatched = [c for c in assessment.charges if c.offence is None]
        if unmatched:
            out.append(Label("DATA GAP", "; ".join(w for c in unmatched for w in c.warnings[:1])))
    if "bail" in (case.next_purpose or "").lower():
        out.append(Label("BAIL", f"Listed for {case.next_purpose}."))
    seen: set[tuple[str, str]] = set()
    unique = []
    for label in out:
        if (label.code, label.reason) not in seen:
            seen.add((label.code, label.reason))
            unique.append(label)
    return unique


UNAVAILABLE = "Data unavailable"


def bail_facts(case: Case, as_of: date) -> dict:
    """The six factors the PRD's bail view lays out, with a source or a gap for each.

    Called "bail facts", not a score: courts weigh these (Sanjay Chandra v. CBI, 2012);
    Manu only gathers them.
    """
    assessment = assess_case(case, as_of)
    if assessment is None:
        return {"applicable": False}
    accused = assessment.accused[0] if assessment.accused else None
    offences = assessment.offences
    max_offence = max(
        offences, key=lambda o: (o.punishment.max_is_life_or_death, o.punishment.max_years or 0), default=None
    )

    def factor(title: str, source: str, items: list[tuple[str, str]], gaps: list[str] | None = None) -> dict:
        return {
            "title": title,
            "source": source,
            "items": [{"label": k, "value": v} for k, v in items],
            "gaps": gaps or [],
        }

    offence_items = [
        (
            c.raw,
            (
                c.offence.title
                if c.offence
                else f"not matched{' (likely ' + c.suggested.key + ')' if c.suggested else ''}"
            ),
        )
        for c in assessment.charges
    ]
    if max_offence:
        p = max_offence.punishment
        ceiling = "death or life imprisonment" if p.max_is_life_or_death else f"{p.max_years:g} years"
        offence_items.append(("Maximum punishment", f"{ceiling} ({max_offence.key})"))
    offence = factor(
        "Offence profile",
        "Charges on record, offence table",
        offence_items,
        [w for c in assessment.charges for w in c.warnings if "not been reviewed" not in w],
    )

    if accused:
        r = accused.s479
        custody_items = [("Days in custody", str(r.days_detained) if r.days_detained else UNAVAILABLE)]
        if r.applicable:
            custody_items.append(
                (
                    f"s.479 {r.applicable.ratio_label} threshold",
                    f"{r.applicable.crossing_date.isoformat()} ({r.percent_of_applicable}% served)",
                )
            )
        custody_items.append(("s.479 status", r.status.replace("_", " ")))
        db = accused.default_bail
        if db.accrual_date:
            custody_items.append(
                (
                    "Default bail (s.187(3) BNSS)",
                    f"{db.status.replace('_', ' ')} — accrues {db.accrual_date.isoformat()}",
                )
            )
        custody = factor(
            "Custody status", "Case record (remand dates)", custody_items, r.gaps + r.flags + db.gaps + db.flags
        )
        antecedent_items = [
            ("First-time offender", {True: "Yes", False: "No", None: UNAVAILABLE}[accused.accused.first_offender]),
            (
                "Other pending cases",
                UNAVAILABLE
                if accused.accused.other_pending_cases is None
                else str(accused.accused.other_pending_cases),
            ),
        ]
        antecedents = factor(
            "Criminal antecedents",
            "CCTNS via ICJS (not connected)",
            antecedent_items,
            ["Antecedent report not on record."] if accused.accused.first_offender is None else [],
        )
    else:
        custody = factor("Custody status", "Case record", [("Accused", UNAVAILABLE)], ["No accused on record."])
        antecedents = factor("Criminal antecedents", "CCTNS via ICJS (not connected)", [], ["No accused on record."])

    roots = factor(
        "Roots & stability",
        "Bail application, surety documents",
        [],
        ["Read from the bail application once it is uploaded."],
    )
    status = factor(
        "Case status",
        "Court record",
        [
            ("Stage", case.stage.replace("_", " ")),
            (
                "Chargesheet",
                case.chargesheet_filed_on.isoformat() if case.chargesheet_filed_on else "Not filed / not on record",
            ),
        ],
    )
    reply = next((o for o in case.obligations if "reply" in o.what.lower()), None)
    prosecution = factor(
        "Prosecution position",
        "Orders on record",
        [
            (
                "Reply",
                f"directed{' by ' + reply.due.isoformat() if reply and reply.due else ''}" if reply else UNAVAILABLE,
            )
        ],
        [] if reply else ["No reply on record."],
    )
    return {
        "applicable": True,
        "as_of": as_of.isoformat(),
        "note": "Facts only. Manu does not recommend grant or rejection.",
        "factors": [offence, custody, antecedents, roots, status, prosecution],
    }
