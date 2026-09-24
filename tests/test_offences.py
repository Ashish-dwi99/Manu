from datetime import date

from manu.law.offences import OFFENCES, penal_code_for, resolve_charge


def test_code_is_fixed_by_offence_date():
    assert penal_code_for(date(2024, 6, 30)) == "IPC"
    assert penal_code_for(date(2024, 7, 1)) == "BNS"


def test_every_row_has_a_counterpart_that_exists_or_is_new_in_bns():
    for row in OFFENCES.values():
        assert row.counterpart in OFFENCES, row.key


def test_maxima_that_changed_between_codes():
    assert OFFENCES["IPC 406"].punishment.max_years == 3
    assert OFFENCES["BNS 316(2)"].punishment.max_years == 5
    assert OFFENCES["IPC 384"].punishment.max_years == 3
    assert OFFENCES["BNS 308(2)"].punishment.max_years == 7


def test_wrong_code_label_is_caught_and_never_computed():
    # JudgeDesk's demo record: theft on a July 2024 FIR written as "Sec. 379 BNS".
    charge = resolve_charge("Sec. 379 BNS", date(2024, 7, 2))
    assert charge.offence is None
    assert charge.suggested is not None and charge.suggested.key == "BNS 303(2)"
    assert any("wrong code" in w for w in charge.warnings)


def test_ipc_charge_on_a_bns_era_offence_suggests_the_counterpart():
    charge = resolve_charge("u/s 406 IPC", date(2024, 9, 1))
    assert charge.offence is None
    assert charge.suggested.key == "BNS 316(2)"


def test_exact_matches_and_formats():
    assert resolve_charge("Sec. 379 IPC", date(2023, 1, 1)).offence.key == "IPC 379"
    assert resolve_charge("section 498-A IPC", date(2020, 1, 1)).offence.key == "IPC 498A"
    assert resolve_charge("u/s 303(2) BNS", date(2025, 1, 1)).offence.key == "BNS 303(2)"
    assert resolve_charge("S. 376 (1) IPC", date(2022, 1, 1)).offence.key == "IPC 376(1)"


def test_unknown_section_is_a_gap_not_a_guess():
    charge = resolve_charge("Sec. 999 BNS", date(2025, 1, 1))
    assert charge.offence is None and charge.suggested is None
    assert "not in the offence table" in charge.warnings[0]


def test_unreviewed_rows_are_disclosed():
    charge = resolve_charge("Sec. 379 IPC", date(2023, 1, 1))
    assert any("not been reviewed" in w for w in charge.warnings)
