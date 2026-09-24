"""What Manu found in a folder, in one line an advocate can check at a glance.

Pointing at a folder and being told "indexed 7 files" is a progress bar. Pointing at a folder
and being told "Criminal Appeal No. 442 of 2026 — next hearing 12 Aug 2026, under s.374(2)
CrPC" is the moment the product earns its place: the advocate did not type any of that, and
they can verify all of it in a second.

Deliberately only the identifiers the deterministic layer is sure about. Anything requiring
judgement belongs to the model layer, and putting a guess in this line would teach an advocate
not to trust it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from manu.doc_intel import grammars


@dataclass
class FolderFindings:
    """Identifiers seen across a case folder, with how often each appeared."""

    case_numbers: Counter[str] = field(default_factory=Counter)
    cnrs: Counter[str] = field(default_factory=Counter)
    provisions: Counter[str] = field(default_factory=Counter)
    citations: Counter[str] = field(default_factory=Counter)
    dates: set[str] = field(default_factory=set)
    files_read: int = 0
    files_with_text: int = 0
    scanned_files: int = 0

    def observe(self, text: str, *, was_scanned: bool = False) -> None:
        self.files_read += 1
        if was_scanned:
            self.scanned_files += 1
        body = text or ""
        if not body.strip():
            return
        self.files_with_text += 1
        for match in grammars.find_case_numbers(body):
            self.case_numbers[match.value] += 1
        for match in grammars.find_cnr(body):
            self.cnrs[match.value] += 1
        for match in grammars.find_statutes(body):
            self.provisions[match.value] += 1
        for match in grammars.find_citations(body):
            self.citations[match.value] += 1
        self.dates.update(match.value for match in grammars.find_dates(body))

    @property
    def lead_case_number(self) -> str:
        """The case the folder is mostly about.

        Most frequent wins, because a folder for an appeal mentions the appeal in the memo, in
        every order and on every index page, while the trial number below it appears once or
        twice. A tie breaks on the later year: an appeal is filed after the case it appeals.
        """
        if not self.case_numbers:
            return ""
        return max(
            self.case_numbers.items(),
            key=lambda item: (item[1], _year_of(item[0])),
        )[0]

    @property
    def next_hearing(self) -> str:
        """The latest date in the folder, as a candidate only.

        A hearing already listed is the last date anyone wrote down, so the maximum is the right
        guess — but it is a guess: the maximum could equally be a limitation date or a deadline
        in a prayer. Presented as "next date" rather than asserted as the diary entry, and the
        model layer is what will decide the role properly.
        """
        return max(self.dates) if self.dates else ""

    @property
    def instituting_provision(self) -> str:
        """The provision the filing is *under*, which is procedural, not the offence.

        Frequency is the wrong signal here and picking it was wrong: in this folder s.138 NI Act
        is cited more often than anything else, because the notice and the memo both recite the
        offence — but the appeal is instituted under s.374(2) CrPC, and that is what belongs
        after the word "under" in a cause title and in a draft.

        So procedure outranks substance. Within procedure, frequency decides.
        """
        if not self.provisions:
            return ""
        return max(
            self.provisions.items(),
            key=lambda item: (_is_procedural(item[0]), item[1]),
        )[0]

    def headline(self) -> str:
        """One line, or nothing. Never a line that says nothing."""
        parts: list[str] = []
        if self.lead_case_number:
            parts.append(self.lead_case_number)
        if self.next_hearing:
            parts.append(f"next date {_human_date(self.next_hearing)}")
        provision = self.instituting_provision
        if provision:
            parts.append(f"under {_short_provision(provision)}")
        if not parts:
            return ""
        return " · ".join(parts)

    def as_dict(self) -> dict[str, Any]:
        return {
            "files_read": self.files_read,
            "files_with_text": self.files_with_text,
            "scanned_files": self.scanned_files,
            "lead_case_number": self.lead_case_number,
            "case_numbers": [value for value, _ in self.case_numbers.most_common(8)],
            "cnr": next(iter(self.cnrs), ""),
            "provisions": [value for value, _ in self.provisions.most_common(6)],
            "citations": [value for value, _ in self.citations.most_common(8)],
            "next_hearing_candidate": self.next_hearing,
            "date_count": len(self.dates),
            "headline": self.headline(),
        }


# Statutes that institute a proceeding, as against those that create the offence or the right
# being litigated. A cause title reads "under section 374(2) of the Code of Criminal
# Procedure"; it never reads "under section 420 IPC".
_PROCEDURAL_STATUTES = (
    "Code of Criminal Procedure",
    "Code of Civil Procedure",
    "Constitution of India",
    "Arbitration and Conciliation",
    "Companies Act",
    "Insolvency and Bankruptcy",
)


def _is_procedural(provision: str) -> bool:
    return any(name.lower() in provision.lower() for name in _PROCEDURAL_STATUTES)


def _year_of(case_number: str) -> int:
    tail = case_number.rsplit(" ", 1)[-1]
    return int(tail) if tail.isdigit() else 0


_MONTH_NAMES = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _human_date(iso: str) -> str:
    """`12 Aug 2026`, because no advocate reads 2026-08-12 as a hearing date."""
    try:
        year, month, day = (int(part) for part in iso.split("-"))
        return f"{day} {_MONTH_NAMES[month - 1]} {year}"
    except Exception:  # noqa: BLE001
        return iso


def _short_provision(provision: str) -> str:
    """`s.374(2) CrPC` rather than the full statute title, which does not fit one line."""
    text = provision.replace("Section ", "s.")
    for long, short in (
        ("of the Code of Criminal Procedure", "CrPC"),
        ("of the Code of Civil Procedure", "CPC"),
        ("of the Indian Penal Code", "IPC"),
        ("of the Negotiable Instruments Act", "NI Act"),
        ("of the Constitution of India", "Constitution"),
    ):
        if long in text:
            head = text.split(long)[0].strip()
            return f"{head} {short}"
    # Drop a trailing year; it adds length without helping anyone scan the line.
    return text.split(",")[0].strip()
