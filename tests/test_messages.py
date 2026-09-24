from datetime import date

from manu.case_state.store import CaseStore
from manu.demo import seed
from manu.messages import cause_list, client_update, due_updates

TODAY = date(2026, 9, 24)


def store():
    s = CaseStore()
    seed(s, today=TODAY)
    return s


def test_morning_cause_list_is_in_item_order_with_purpose_last_order_and_dues():
    draft = cause_list(store(), TODAY)
    text = draft["text"]
    assert draft["count"] == 3
    assert text.startswith("*Cause list · Thu, 24 Sep 2026*")
    assert text.index("Item 14") < text.index("Item 22") < text.index("Item 31")
    assert "Court Room 312" in text
    assert "For: Bail application" in text
    assert "Due: IO" in text and "(today)" in text
    assert draft["sources"]


def test_client_update_uses_only_the_record():
    s = store()
    imran = next(c for c in s.all() if c.cnr == "DLSE010007892026")
    en = client_update(imran, TODAY)
    assert "is listed on Thursday, 24 September 2026 before ASJ-03, Saket" in en["text"]
    assert "item 14 in Court Room 312" in en["text"]
    assert en["gaps"] and en["text"].startswith("Hello,")


def test_client_updates_fall_due_seven_and_two_days_before_a_hearing():
    s = store()
    due = due_updates(s, TODAY)
    # Aamir Khan is listed in seven days; no followed case is two days out.
    assert [d["title"] for d in due] == ["State v. Aamir Khan"]
    assert due[0]["days_to_hearing"] == 7
