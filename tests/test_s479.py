from datetime import date, timedelta

from manu.law import s479
from manu.law.offences import OFFENCES

THEFT = OFFENCES["BNS 303(2)"]
MURDER = OFFENCES["BNS 103(1)"]
CHEATING_IPC = OFFENCES["IPC 420"]
AS_OF = date(2026, 9, 24)


def custody(days_ago: int) -> list[s479.CustodyPeriod]:
    return [s479.CustodyPeriod(AS_OF - timedelta(days=days_ago))]


def test_life_or_death_is_outside_the_section():
    r = s479.assess(offences=[THEFT, MURDER], custody=custody(900), as_of=AS_OF, first_offender=True)
    assert r.status == "not_applicable"
    assert not r.alert


def test_first_offender_one_third_approaching():
    # 3 years max -> one-third = 12 months; 361 days served (remand day counted).
    r = s479.assess(offences=[THEFT], custody=custody(360), as_of=AS_OF, first_offender=True, other_pending_cases=0)
    assert r.applicable.ratio_label == "one-third"
    assert r.days_detained == 361
    assert r.status == "approaching"
    assert r.alert


def test_repeat_offender_uses_one_half():
    r = s479.assess(offences=[THEFT], custody=custody(360), as_of=AS_OF, first_offender=False, other_pending_cases=0)
    assert r.applicable.ratio_label == "one-half"
    assert r.status == "not_yet"


def test_unknown_first_offender_alerts_on_the_earlier_date_and_says_so():
    r = s479.assess(offences=[THEFT], custody=custody(400), as_of=AS_OF, first_offender=None)
    assert r.applicable.ratio_label == "one-third"
    assert r.status == "crossed"
    assert any("not verified" in g for g in r.gaps)
    assert any("s.479(2)" in g for g in r.gaps)


def test_ipc_offence_uses_ipc_maximum():
    # IPC 420: 7 years -> one-half = 42 months.
    r = s479.assess(
        offences=[CHEATING_IPC], custody=custody(100), as_of=AS_OF, first_offender=False, other_pending_cases=0
    )
    assert r.applicable.months == 42


def test_other_pending_cases_flag_the_bar_without_hiding_the_alert():
    r = s479.assess(offences=[THEFT], custody=custody(400), as_of=AS_OF, first_offender=True, other_pending_cases=2)
    assert r.status == "crossed"
    assert any("barred by statute" in f for f in r.flags)


def test_delay_by_accused_is_excluded_and_disclosed():
    r = s479.assess(
        offences=[THEFT],
        custody=custody(370),
        as_of=AS_OF,
        first_offender=True,
        other_pending_cases=0,
        excluded_delay_days=30,
    )
    assert r.days_detained == 341
    assert r.status == "not_yet"
    assert any("Explanation to s.479" in f for f in r.flags)


def test_broken_custody_is_summed():
    periods = [
        s479.CustodyPeriod(date(2025, 1, 1), date(2025, 1, 31)),
        s479.CustodyPeriod(date(2025, 6, 1), None),
    ]
    r = s479.assess(
        offences=[THEFT], custody=periods, as_of=date(2025, 6, 30), first_offender=True, other_pending_cases=0
    )
    assert r.days_detained == 31 + 30


def test_maximum_period_exceeded():
    r = s479.assess(
        offences=[OFFENCES["BNS 115(2)"]],
        custody=custody(400),
        as_of=AS_OF,
        first_offender=False,
        other_pending_cases=0,
    )
    assert r.status == "maximum_exceeded"


def test_missing_custody_is_a_gap():
    r = s479.assess(offences=[THEFT], custody=[], as_of=AS_OF, first_offender=True)
    assert r.status == "insufficient_data"
    assert r.gaps


def test_month_arithmetic_clamps_to_month_end():
    assert s479._add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert s479._add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert s479._add_months(date(2024, 11, 15), 3) == date(2025, 2, 15)
