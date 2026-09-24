from datetime import date

import pytest

from manu.law.limitation import RULES, compute


def test_the_day_of_the_order_is_excluded():
    result = compute("civil_appeal_other", date(2026, 1, 1), as_of=date(2026, 1, 5))
    assert result.last_day == date(2026, 1, 31)
    assert result.status == "running"
    assert any("s.12(1)" in line for line in result.working)


def test_certified_copy_time_is_excluded_and_counted_short():
    result = compute(
        "civil_appeal_hc",
        date(2026, 9, 1),
        as_of=date(2026, 9, 2),
        copy_applied=date(2026, 9, 3),
        copy_ready=date(2026, 9, 13),
    )
    assert result.excluded_days == 10
    assert result.last_day == date(2026, 11, 30) + (date(2026, 9, 13) - date(2026, 9, 3))


def test_a_copy_applied_after_the_period_ran_excludes_nothing():
    result = compute(
        "civil_appeal_other",
        date(2026, 1, 1),
        as_of=date(2026, 3, 1),
        copy_applied=date(2026, 2, 5),
        copy_ready=date(2026, 2, 10),
    )
    assert result.excluded_days == 0
    assert result.status == "expired"
    assert any("s.5" in flag for flag in result.flags)


def test_pending_copy_is_a_gap_not_a_guess():
    result = compute("review", date(2026, 1, 1), as_of=date(2026, 1, 2), copy_applied=date(2026, 1, 3))
    assert result.excluded_days == 0
    assert result.gaps


def test_sunday_moves_under_section_4_and_holidays_are_flagged():
    # 30 days from Fri 2 Oct 2026 is Sun 1 Nov 2026.
    result = compute("civil_appeal_other", date(2026, 10, 2), as_of=date(2026, 10, 3))
    assert result.last_day == date(2026, 11, 1)
    assert result.file_by == date(2026, 11, 2)
    assert any("holiday" in flag for flag in result.flags)


def test_written_statement_has_an_outer_limit_only_the_court_can_reach():
    result = compute("written_statement", date(2026, 1, 1), as_of=date(2026, 2, 15))
    assert result.last_day == date(2026, 1, 31)
    assert result.outer_day == date(2026, 4, 1)
    assert result.status == "extension_only"
    assert result.days_left == (date(2026, 4, 1) - date(2026, 2, 15)).days
    commercial = compute("written_statement_commercial", date(2026, 1, 1), as_of=date(2026, 6, 1))
    assert commercial.status == "expired"
    assert not any("s.5" in flag for flag in commercial.flags)


def test_every_rule_names_its_provision_and_is_unreviewed_until_an_advocate_signs():
    for rule in RULES.values():
        assert rule.provision and rule.days > 0
        assert not rule.reviewed
    result = compute("slp", date(2026, 1, 1), as_of=date(2026, 1, 1))
    assert any("not yet been reviewed" in flag for flag in result.flags)


def test_unknown_rule_is_refused():
    with pytest.raises(KeyError):
        compute("appeal_to_the_moon", date(2026, 1, 1), as_of=date(2026, 1, 1))
