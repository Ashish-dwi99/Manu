from datetime import date

from manu.case_state.models import SourceRef
from manu.orders import read_order, sentences

ORDER = """Present: Ld. APP for the State. Accused produced from JC. Sh. R. Mehta, Ld. counsel for the accused.
The IO is directed to file a reply along with the previous involvement report of the accused within two weeks. Let the TCR be summoned. Ld. counsel for the accused shall furnish a copy of the application to the Ld. APP before the next date.
Put up on 14.10.2024 for arguments on the bail application."""


def read():
    return read_order(ORDER, order_on=date(2024, 9, 24), source=SourceRef(kind="order", uri="order.pdf"))


def test_sentences_do_not_split_on_court_abbreviations():
    texts = [s.text for s in sentences(ORDER)]
    assert (
        "Ld. counsel for the accused shall furnish a copy of the application to the Ld. APP before the next date."
        in texts
    )


def test_next_date_and_purpose():
    r = read()
    assert r.next_date == date(2024, 10, 14)
    assert r.next_purpose == "arguments on the bail application"


def test_obligations_carry_who_when_and_the_exact_words():
    r = read()
    by_who = {o.who: o for o in r.obligations}
    io = by_who["IO"]
    assert io.due == date(2024, 10, 8)
    assert ORDER[io.source.span_start : io.source.span_end].strip() == io.what
    assert io.source.verification == "lead"
    assert by_who["Ld. counsel for the accused"].due == date(2024, 10, 14)
    assert by_who["Court office (process)"].what == "Let the TCR be summoned."


def test_explicit_due_date_wins():
    text = "The IO is directed to file the reply on or before 29.09.2026, failing which the SHO shall remain present."
    r = read_order(text, order_on=date(2026, 9, 23), source=SourceRef(kind="order"))
    assert r.obligations[0].due == date(2026, 9, 29)


def test_order_with_no_directions_has_no_obligations():
    r = read_order(
        "Present: none. Put up on 01.12.2026 for evidence.", order_on=date(2026, 9, 1), source=SourceRef(kind="order")
    )
    assert r.obligations == []
    assert r.next_date == date(2026, 12, 1)
