"""Identifiers the courts publish a format for must be read exactly.

These are the facts a case file is built on and a draft's cause title is copied from. A
missed case number means the matter shows the number of the court below; a misread date
means a wrong entry in an advocate's diary.

See docs/manu-document-intelligence.md for why this layer is deterministic while
classification and reading are not.
"""

from __future__ import annotations

from manu.doc_intel import grammars


def _values(matches) -> set[str]:
    return {match.value for match in matches}


def test_a_matters_own_case_number_is_found_however_the_cause_title_spells_it() -> None:
    """The cause title of a filing spells the type out; orders abbreviate it.

    Only matching the abbreviation meant reading nothing from the appeal memo's own heading
    and picking up only the trial court number underneath — the wrong case entirely.
    """
    for spelling in (
        "CRIMINAL APPEAL NO. 442 OF 2026",
        "Criminal Appeal No. 442 of 2026",
        "CRL.A. 442/2026",
        "Crl. A. No.442 of 2026",
        "CRL.A. No. 442 of 2026",
    ):
        assert _values(grammars.find_case_numbers(spelling)) == {"CRL.A. No. 442 of 2026"}, spelling


def test_different_cases_do_not_collapse_into_one() -> None:
    # An appeal, the trial below it, and an application inside it are three numbers that
    # must stay three. Over-normalising would merge a matter with its own history.
    assert _values(grammars.find_case_numbers("SESSIONS TRIAL NO. 118 OF 2025")) == {"S.T. No. 118 of 2025"}
    assert _values(grammars.find_case_numbers("I.A. No. 3117 of 2026")) == {"I.A. No. 3117 of 2026"}
    assert _values(grammars.find_case_numbers("W.P.(C) 1234/2025")) == {"W.P.(C). No. 1234 of 2025"}


def test_prose_containing_a_number_and_a_year_is_not_a_case_number() -> None:
    # The type token list is explicit precisely so that ordinary sentences cannot pass. A
    # phantom case number in the header is worse than a blank one.
    assert grammars.find_case_numbers("The sum of 450000 in 2024 was never paid.") == []
    assert grammars.find_case_numbers("Paragraph 12 of 2019 is denied.") == []


def test_a_cnr_is_sixteen_characters_in_the_published_shape() -> None:
    assert _values(grammars.find_cnr("CNR: DLST010012342024")) == {"DLST010012342024"}
    # Wrong length, or letters where the sequence belongs, is not a CNR.
    assert grammars.find_cnr("DLST01001234202") == []
    assert grammars.find_cnr("DLSTABCDEF342024") == []


def test_dates_are_read_day_first_because_india_writes_them_that_way() -> None:
    """12/08/2026 in an Indian order is August, not December.

    A month-first reading puts a hearing four months late in the diary, which is the kind of
    error that loses a matter rather than merely annoying someone.
    """
    assert _values(grammars.find_dates("List on 12/08/2026.")) == {"2026-08-12"}
    # Unambiguous when one number cannot be a month, whichever convention was used.
    assert _values(grammars.find_dates("dated 25/03/2026")) == {"2026-03-25"}
    # Both spelled forms agree.
    assert _values(grammars.find_dates("List on 12 August 2026")) == {"2026-08-12"}
    assert _values(grammars.find_dates("August 12, 2026")) == {"2026-08-12"}


def test_implausible_dates_are_rejected_rather_than_trusted() -> None:
    # OCR turns page furniture into digits. A 1900 date is a misread, not a filing.
    assert grammars.find_dates("1/1/1900") == []
    assert grammars.find_dates("31/13/2026") == []


def test_the_provision_a_filing_is_under_is_extracted_with_its_statute() -> None:
    """The draft section needs this: a criminal appeal is under s.374(2) CrPC.

    A draft citing the wrong provision is unusable however well written, so the provision is
    read from the filing rather than inferred from the document type.
    """
    found = _values(
        grammars.find_statutes("MEMORANDUM OF APPEAL UNDER SECTION 374(2) OF THE CODE OF CRIMINAL PROCEDURE, 1973")
    )
    assert any(item.startswith("Section 374(2) of the Code of Criminal Procedure") for item in found)

    found = _values(grammars.find_statutes("under Section 138 of the Negotiable Instruments Act, 1881"))
    assert "Section 138 of the Negotiable Instruments Act, 1881" in found

    # Order and Rule references are how civil interlocutory relief is framed.
    assert "Order XXXIX Rule 1 and 2 CPC" in _values(
        grammars.find_statutes("under Order XXXIX Rules 1 and 2 of the Code of Civil Procedure")
    )


def test_reported_citations_are_recognised_in_both_common_shapes() -> None:
    assert _values(grammars.find_citations("relied on (2020) 5 SCC 1 and AIR 2019 SC 1234")) >= {
        "(2020) 5 SCC 1",
        "AIR 2019 SC 1234",
    }


def test_every_match_carries_a_span_that_points_at_what_was_read() -> None:
    """Without an exact span there is no citation, and without a citation the case file is a
    summary rather than work product."""
    text = "ORDER dated 08 April 2026 in CRIMINAL APPEAL NO. 442 OF 2026"
    for match in grammars.find_dates(text) + grammars.find_case_numbers(text):
        assert 0 <= match.start < match.end <= len(text)
        # The span must actually contain what it claims, allowing for normalisation.
        assert text[match.start : match.end].strip()
