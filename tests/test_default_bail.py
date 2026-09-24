from datetime import date, timedelta

from manu.law import default_bail
from manu.law.offences import OFFENCES

AS_OF = date(2026, 9, 24)


def test_sixty_days_counts_remand_as_day_one():
    remand = date(2026, 8, 1)
    r = default_bail.assess(
        offences=[OFFENCES["BNS 303(2)"]], first_remand=remand, as_of=AS_OF, chargesheet_filed_on=None, in_custody=True
    )
    assert r.period_days == 60
    assert r.accrual_date == remand + timedelta(days=60)


def test_life_offence_is_ninety_days():
    r = default_bail.assess(
        offences=[OFFENCES["BNS 103(1)"]],
        first_remand=AS_OF - timedelta(days=10),
        as_of=AS_OF,
        chargesheet_filed_on=None,
        in_custody=True,
    )
    assert r.period_days == 90
    assert r.status == "not_yet"


def test_ten_year_ceiling_is_flagged_with_both_dates():
    remand = AS_OF - timedelta(days=58)
    r = default_bail.assess(
        offences=[OFFENCES["BNS 309(4)"]], first_remand=remand, as_of=AS_OF, chargesheet_filed_on=None, in_custody=True
    )
    assert r.period_days == 90
    assert r.alternative_accrual_date == remand + timedelta(days=60)
    assert r.status == "approaching"
    assert any("Rakesh Kumar Paul" in f for f in r.flags)


def test_chargesheet_in_time_extinguishes():
    remand = date(2026, 6, 1)
    r = default_bail.assess(
        offences=[OFFENCES["BNS 303(2)"]],
        first_remand=remand,
        as_of=AS_OF,
        chargesheet_filed_on=date(2026, 7, 1),
        in_custody=True,
    )
    assert r.status == "chargesheet_filed"


def test_accrued():
    r = default_bail.assess(
        offences=[OFFENCES["BNS 303(2)"]],
        first_remand=AS_OF - timedelta(days=70),
        as_of=AS_OF,
        chargesheet_filed_on=None,
        in_custody=True,
    )
    assert r.status == "accrued" and r.alert


def test_special_statute_goes_to_review():
    r = default_bail.assess(
        offences=[OFFENCES["BNS 303(2)"]],
        first_remand=AS_OF,
        as_of=AS_OF,
        chargesheet_filed_on=None,
        in_custody=True,
        special_statute=True,
    )
    assert r.status == "needs_review"


def test_not_in_custody():
    r = default_bail.assess(offences=[], first_remand=None, as_of=AS_OF, chargesheet_filed_on=None, in_custody=False)
    assert r.status == "not_applicable"
