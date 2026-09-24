from datetime import date

from manu.case_state.store import CaseStore
from manu.citations import locate, verify_answer
from manu.demo import seed
from manu.documents import DocumentStore


def test_locate_tolerates_whitespace_case_and_punctuation():
    source = "That the applicant is a first-time offender and has no previous\ninvolvement in any criminal case."
    assert locate(source, "first-time offender and has no previous involvement")
    assert locate(source, "FIRST-TIME OFFENDER  and has no previous")
    assert locate(source, "first time offender and has no previous involvement")
    assert not locate(source, "the applicant has two previous convictions")


def test_answer_quotes_are_checked_against_papers_and_orders():
    store = CaseStore()
    seed(store, today=date(2026, 9, 24))
    case = store.by_cnr("DLSE010001232024")
    answer = (
        'The FIR records that "11 cartons were recovered from a rented room" [FIR, p. 2]. '
        'The court directed that "the SHO concerned shall remain present in person" [Order dt. 23.09.2026]. '
        'It also said "the accused is a habitual offender with ten cases".'
    )
    results = verify_answer(DocumentStore(store), case.id, answer)
    assert [(r["verified"], r["source"], r["page"]) for r in results] == [
        (True, "FIR-512-2025.txt", 2),
        (True, "Order dated 23.09.2026", None),
        (False, None, None),
    ]
