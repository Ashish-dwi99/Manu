"""Identifiers the courts publish a format for, matched exactly.

These are grammars, not guesses. A CNR is sixteen characters with a fixed shape; a citation
is `(2020) 5 SCC 1`. Reading them deterministically is both more accurate than asking a
model and checkable afterwards, which is what an advocate needs from a case file.

This is not the regex-router pattern Manu bans. That rule is about intent — never
pattern-match what a person meant into a hardcoded workflow. Nothing here touches intent;
it reads published document formats. Anything requiring judgement (what a document *is*,
what an order *held*, which date is the *next hearing*) is left to the layers above.

Word boundaries everywhere, because without them "IA" matches inside "trial" and "SC"
inside "SCC" — the same trap paperless-ngx guards with `\\b` in every non-fuzzy mode.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- CNR ----------------------------------------------------------------------------
#
# Two letters of state, two of district, two of establishment, six digits of sequence, four
# of year: DLST010012342024. The middle four are alphanumeric in practice, the last ten
# always digits, which is what makes this safe to match without catching ordinary words.
CNR = re.compile(r"\b([A-Z]{2}[A-Z0-9]{4}\d{6}(?:19|20)\d{2})\b")

# --- Case numbers -------------------------------------------------------------------
#
# Indian case numbers are a court-type token, a number, and a year, joined by "of", "/" or
# "-": "CRL.A. 442 of 2026", "W.P.(C) 1234/2025", "O.S. No. 55 of 2020". The token list is
# explicit rather than a wildcard so that ordinary prose containing a number and a year
# cannot masquerade as a case number.
_CASE_TYPE_TOKENS = (
    # Spelled out, which is how the cause title of the filing itself almost always reads —
    # "CRIMINAL APPEAL NO. 442 OF 2026". Missing these meant reading a matter's own number
    # off nothing and picking up only the court below, which is the wrong case.
    "CRIMINAL\\s+APPEAL",
    "CRIMINAL\\s+REVISION",
    "CRIMINAL\\s+MISC(?:ELLANEOUS)?",
    "CIVIL\\s+APPEAL",
    "CIVIL\\s+REVISION",
    "CIVIL\\s+SUIT",
    "ORIGINAL\\s+SUIT",
    "WRIT\\s+PETITION",
    "SPECIAL\\s+LEAVE\\s+PETITION",
    "FIRST\\s+APPEAL",
    "SECOND\\s+APPEAL",
    "REGULAR\\s+FIRST\\s+APPEAL",
    "EXECUTION\\s+PETITION",
    "COMPANY\\s+PETITION",
    "ARBITRATION\\s+PETITION",
    "MOTOR\\s+ACCIDENT\\s+CLAIM",
    "INTERLOCUTORY\\s+APPLICATION",
    "BAIL\\s+APPLICATION",
    # Criminal
    "CRL\\.?\\s?A",
    "CRL\\.?\\s?REV",
    "CRL\\.?\\s?M\\.?C",
    "CRL\\.?\\s?O\\.?P",
    "CRL\\.?\\s?MP",
    "SESSIONS\\s+TRIAL",
    "S\\.?T",
    "BAIL\\s+APPLN",
    "ANTICIPATORY\\s+BAIL",
    # Civil
    "O\\.?\\s?S",
    "C\\.?\\s?S",
    "R\\.?\\s?F\\.?\\s?A",
    "R\\.?\\s?S\\.?\\s?A",
    "C\\.?\\s?R\\.?\\s?P",
    "M\\.?\\s?A",
    "E\\.?\\s?P",
    "C\\.?\\s?M\\.?\\s?A",
    # Constitutional / writ
    "W\\.?\\s?P\\.?\\s?\\(?C\\)?",
    "W\\.?\\s?P\\.?\\s?\\(?CRL\\)?",
    "W\\.?\\s?P",
    "S\\.?L\\.?P",
    "C\\.?\\s?A",
    "P\\.?I\\.?L",
    # Applications and misc
    "I\\.?\\s?A",
    "O\\.?\\s?A",
    "M\\.?\\s?C",
    "ARB\\.?\\s?P",
    "COMP\\.?\\s?A",
)
CASE_NUMBER = re.compile(
    r"\b(" + "|".join(_CASE_TYPE_TOKENS) + r")\.?\s*"
    r"(?:NO\.?|NOS\.?)?\s*"
    r"(\d{1,6})\s*"
    r"(?:OF|/|-)\s*"
    r"((?:19|20)\d{2})\b",
    re.IGNORECASE,
)

# --- Reported citations -------------------------------------------------------------
#
# Two shapes cover most of what is cited in practice:
#   neutral//reporter with a bracketed year — (2020) 5 SCC 1
#   reporter with a leading year          — AIR 2019 SC 1234, 2021 SCC OnLine Del 456
_REPORTERS = (
    "SCC\\s+OnLine",
    "SCC",
    "AIR",
    "SCR",
    "JT",
    "ALL\\s?ER",
    "Cri\\.?\\s?L\\.?J",
    "CriLJ",
    "ITR",
    "GST",
    "CTC",
    "MLJ",
    "BomCR",
    "DLT",
    "MPLJ",
    "RLW",
    "PLR",
)
CITATION_BRACKETED_YEAR = re.compile(
    r"\((?:19|20)\d{2}\)\s*\d{1,3}\s*(?:" + "|".join(_REPORTERS) + r")(?:\s+\w{2,10})?\s*\d{1,5}",
    re.IGNORECASE,
)
CITATION_LEADING_YEAR = re.compile(
    r"\b(?:" + "|".join(_REPORTERS) + r")\s+(?:19|20)\d{2}\s+[A-Z][A-Za-z]{1,9}\s*\d{1,5}\b"
    r"|\b(?:19|20)\d{2}\s+(?:" + "|".join(_REPORTERS) + r")\s+[A-Z][A-Za-z]{1,9}\s*\d{1,5}\b",
    re.IGNORECASE,
)

# --- Statutory references -----------------------------------------------------------
#
# "Section 374(2) of the Code of Criminal Procedure, 1973", "Order XXXIX Rules 1 and 2 CPC",
# "u/s 138 of the Negotiable Instruments Act". The provision is what tells us how a filing is
# framed, which is why the draft section needs it: a criminal appeal is under s.374(2), and a
# draft that cites the wrong provision is unusable however well written.
SECTION_REF = re.compile(
    r"\b(?:under\s+)?(?:section|sections|sec\.?|s\.|u/s|u/ss)\s*"
    r"(\d{1,4}[A-Z]?(?:\s*\(\s*\d+\s*\))?(?:\s*\(\s*[a-z]\s*\))?)"
    r"(?:\s*(?:and|,|&)\s*\d{1,4}[A-Z]?(?:\s*\(\s*\d+\s*\))?)*"
    # Two shapes, and the second is the one that matters most in criminal practice:
    #   trailing  — "Indian Penal Code", "Negotiable Instruments Act"
    #   leading   — "Code of Criminal Procedure", "Constitution of India"
    # A pattern requiring the type word at the end silently dropped the statute from every
    # CrPC and CPC reference, which is exactly what a criminal appeal is framed under.
    r"(?:\s+of\s+the\s+((?:Code|Constitution)\s+of\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,3}"
    r"|[A-Za-z][A-Za-z' \-]{3,70}?(?:Act|Code|Rules|Constitution))"
    r"(?:\s*,?\s*((?:18|19|20)\d{2}))?)?",
    re.IGNORECASE,
)
ORDER_RULE_REF = re.compile(
    r"\bOrder\s+([IVXLC]{1,7}|\d{1,3})\s*(?:,)?\s*Rules?\s*"
    r"(\d{1,3}(?:\s*(?:and|,|&|to)\s*\d{1,3})*)"
    r"(?:\s+of\s+the\s+(C\.?P\.?C\.?|Code of Civil Procedure))?",
    re.IGNORECASE,
)

# --- Dates ---------------------------------------------------------------------------
#
# Candidates only. Which of them is the order date and which the next hearing is a reading
# question, answered a layer up — the same separation paperless draws between finding a date
# and deciding it is the document date.
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
    "|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
DATE_TEXTUAL = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + _MONTHS + r")\.?,?\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
DATE_MONTH_FIRST = re.compile(
    r"\b(" + _MONTHS + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
# Numeric dates are read day-first. India writes dd/mm/yyyy, and a US-style reading turns
# 12/08/2026 into December when the order means August — a wrong hearing date in a diary.
DATE_NUMERIC = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-]((?:19|20)\d{2})\b")

_MONTH_NUMBERS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True, slots=True)
class Match:
    """A grammar hit and where it was, so the caller can cite it."""

    value: str
    start: int
    end: int


def _collapse(text: str) -> str:
    return " ".join(str(text or "").split())


# One case, one string. A folder spells the same appeal as "CRIMINAL APPEAL NO. 442 OF
# 2026" in the memo and "Crl.A. 442/2026" in the order; left alone the case file lists two
# cases. Everything collapses to the abbreviated form, which is what cause lists and orders
# use.
_CASE_TYPE_CANONICAL = {
    "CRIMINALAPPEAL": "CRL.A.",
    "CRIMINALREVISION": "CRL.REV.",
    "CRIMINALMISC": "CRL.M.C.",
    "CRIMINALMISCELLANEOUS": "CRL.M.C.",
    "CIVILAPPEAL": "C.A.",
    "CIVILREVISION": "C.R.P.",
    "CIVILSUIT": "C.S.",
    "ORIGINALSUIT": "O.S.",
    "WRITPETITION": "W.P.",
    "SPECIALLEAVEPETITION": "S.L.P.",
    "FIRSTAPPEAL": "F.A.",
    "SECONDAPPEAL": "S.A.",
    "REGULARFIRSTAPPEAL": "R.F.A.",
    "EXECUTIONPETITION": "E.P.",
    "COMPANYPETITION": "COMP.P.",
    "ARBITRATIONPETITION": "ARB.P.",
    "MOTORACCIDENTCLAIM": "M.A.C.",
    "INTERLOCUTORYAPPLICATION": "I.A.",
    "BAILAPPLICATION": "BAIL APPLN.",
    "SESSIONSTRIAL": "S.T.",
}


def _normalise_case_type(raw: str) -> str:
    """`Crl. A.`, `CRL.A.` and `CRIMINAL APPEAL` must all become one string.

    Spaces beside a period are noise — abbreviations the typist spaced out. Spaces between
    whole words are not, which is why stripping every space turned "SESSIONS TRIAL" into
    "SESSIONSTRIAL". After that, spelled-out types fold into their abbreviation.
    """
    collapsed = re.sub(r"\s*\.\s*", ".", _collapse(raw).upper())
    canonical = _CASE_TYPE_CANONICAL.get(collapsed.replace(" ", "").replace(".", ""))
    if canonical:
        return canonical
    # Abbreviations arrive with a trailing period inconsistently; give them one.
    return collapsed if collapsed.endswith(".") else f"{collapsed}."


def find_cnr(text: str) -> list[Match]:
    return [Match(m.group(1), m.start(1), m.end(1)) for m in CNR.finditer(text or "")]


def find_case_numbers(text: str) -> list[Match]:
    """Normalised to `TYPE No. N of YYYY` so the same case reads identically everywhere.

    A folder will spell one case three ways — "CRL.A. 442/2026", "Crl. A. No.442 of 2026",
    "CRIMINAL APPEAL NO. 442 OF 2026". Without normalising, the case file shows three cases.
    """
    found: list[Match] = []
    for match in CASE_NUMBER.finditer(text or ""):
        kind = _normalise_case_type(match.group(1))
        value = f"{kind} No. {match.group(2)} of {match.group(3)}"
        found.append(Match(value, match.start(), match.end()))
    return found


def find_citations(text: str) -> list[Match]:
    found: list[Match] = []
    seen: set[tuple[int, int]] = set()
    for pattern in (CITATION_BRACKETED_YEAR, CITATION_LEADING_YEAR):
        for match in pattern.finditer(text or ""):
            key = (match.start(), match.end())
            if key in seen:
                continue
            seen.add(key)
            found.append(Match(_collapse(match.group(0)), match.start(), match.end()))
    return sorted(found, key=lambda item: item.start)


def find_statutes(text: str) -> list[Match]:
    """Section and Order/Rule references, normalised for display."""
    found: list[Match] = []
    for match in SECTION_REF.finditer(text or ""):
        provision = _collapse(match.group(1)).replace(" ", "")
        statute = _statute_title(match.group(2) or "")
        year = _collapse(match.group(3) or "")
        value = f"Section {provision}"
        if statute:
            value += f" of the {statute}"
            if year:
                value += f", {year}"
        found.append(Match(value, match.start(), match.end()))
    for match in ORDER_RULE_REF.finditer(text or ""):
        rules = _collapse(match.group(2))
        value = f"Order {_collapse(match.group(1)).upper()} Rule {rules}"
        if match.group(3):
            value += " CPC"
        found.append(Match(value, match.start(), match.end()))
    return sorted(found, key=lambda item: item.start)


# Words that stay lowercase inside a statute name, and acronyms that stay upper. A filing
# typed in capitals and one in mixed case must name the same statute the same way, or the
# case file lists the Code of Criminal Procedure twice.
_STATUTE_LOWER = {"of", "the", "and", "for", "in", "on", "to"}
_STATUTE_UPPER = {"CPC", "CRPC", "IPC", "NI", "GST", "IT", "MV", "POCSO", "UAPA", "NDPS", "SARFAESI"}


def _statute_title(raw: str) -> str:
    collapsed = _collapse(raw)
    if not collapsed:
        return ""
    words = []
    for index, word in enumerate(collapsed.split(" ")):
        bare = word.strip(".,")
        if bare.upper() in _STATUTE_UPPER:
            words.append(word.upper())
        elif index and bare.lower() in _STATUTE_LOWER:
            words.append(word.lower())
        else:
            words.append(word[:1].upper() + word[1:].lower() if word.isupper() else word)
    return " ".join(words)


def find_dates(text: str) -> list[Match]:
    """Every plausible date, as ISO, with the span it was written in.

    Bounds reject the implausible rather than trusting the parse: a scan that OCRs a page
    number into "1/1/1900" should not become a hearing date. Courts in the record run from
    the mid twentieth century, and a filing dated far in the future is a misread.
    """
    body = text or ""
    found: list[Match] = []
    seen: set[tuple[int, int]] = set()

    def add(day: int, month: int, year: int, start: int, end: int) -> None:
        if not (1 <= month <= 12 and 1 <= day <= 31):
            return
        if not (1947 <= year <= 2100):
            return
        key = (start, end)
        if key in seen:
            return
        seen.add(key)
        found.append(Match(f"{year:04d}-{month:02d}-{day:02d}", start, end))

    for match in DATE_TEXTUAL.finditer(body):
        month = _MONTH_NUMBERS.get(match.group(2).lower().rstrip("."))
        if month:
            add(int(match.group(1)), month, int(match.group(3)), match.start(), match.end())
    for match in DATE_MONTH_FIRST.finditer(body):
        month = _MONTH_NUMBERS.get(match.group(1).lower().rstrip("."))
        if month:
            add(int(match.group(2)), month, int(match.group(3)), match.start(), match.end())
    for match in DATE_NUMERIC.finditer(body):
        first, second = int(match.group(1)), int(match.group(2))
        # Day-first, except where that is impossible and the other reading works — "13/2"
        # can only be the 13th of February whichever convention the typist used.
        if first > 12 and second <= 12:
            day, month = first, second
        elif second > 12 and first <= 12:
            day, month = second, first
        else:
            day, month = first, second
        add(day, month, int(match.group(3)), match.start(), match.end())

    return sorted(found, key=lambda item: item.start)
