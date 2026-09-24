import io
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from manu.api import create_app
from manu.case_state.store import CaseStore
from manu.connectors import ConnectorLadder
from manu.demo import FIXTURES, demo_research_ladder, seed
from manu.research import (
    IndianKanoonSource,
    LibrarySource,
    ResearchLadder,
    SourceUnavailable,
    check_citations,
    split_paragraphs,
)
from manu.runtime.tools import case_tools
from manu.runtime.wire import WireEvent

TODAY = date(2026, 9, 24)


def demo_library():
    return ResearchLadder([LibrarySource(FIXTURES / "judgments", name="demo_library", standing="demo")])


def test_paragraphs_follow_the_judgment_numbering():
    assert split_paragraphs("1. First.\n2. Second\ncontinues.\n3. Third.") == ["First.", "Second continues.", "Third."]
    assert split_paragraphs("One.\n\nTwo.") == ["One.", "Two."]


def test_search_by_words_and_by_citation_carries_standing():
    ladder = demo_library()
    hits, _ = ladder.search("parity co-accused")
    assert hits[0].title.startswith("Mohd. Arif") and hits[0].standing == "demo"
    by_citation, _ = ladder.search("(2025) 1 Demo 12")
    assert by_citation[0].doc_id == "demo-2025-1-12"


def test_citation_check_says_how_far_each_citation_got():
    library = LibrarySource(FIXTURES / "judgments", name="firm", standing="licensed")
    text = "Reliance is placed on (2025) 1 Demo 12 and on (2020) 5 SCC 1."
    result = check_citations(text, ResearchLadder([library]))
    statuses = {c["citation"]: c["status"] for c in result["citations"]}
    assert statuses == {"(2025) 1 Demo 12": "verified", "(2020) 5 SCC 1": "not_found"}
    demo = check_citations(text, demo_library())
    assert demo["citations"][0]["status"] == "demo"


def test_indian_kanoon_is_a_lead_and_says_when_it_is_not_configured():
    with pytest.raises(SourceUnavailable):
        IndianKanoonSource(token="").search("bail")

    def opener(request, timeout):
        assert request.headers["Authorization"] == "Token t"
        if "/search/" in request.full_url:
            body = {"docs": [{"tid": 42, "title": "<b>A</b> v. B", "docsource": "Delhi High Court", "publishdate": "2021-02-03"}]}
        else:
            body = {"title": "A v. B", "doc": "<p>1. First para.</p><p>2. Second para.</p>"}
        return io.BytesIO(json.dumps(body).encode())

    source = IndianKanoonSource(token="t", opener=opener)
    hit = source.search("bail")[0]
    assert (hit.title, hit.standing, hit.decided_on) == ("A v. B", "lead", date(2021, 2, 3))
    assert source.fetch("42").paragraphs == ["First para.", "Second para."]


def client():
    store = CaseStore()
    seed(store, today=TODAY)
    return store, TestClient(create_app(store, ConnectorLadder([]), demo_research_ladder()))


def test_relying_on_a_paragraph_stores_its_own_words_on_the_case():
    store, c = client()
    aamir = next(x["id"] for x in c.get("/api/cases").json()["cases"] if x["cnr"] == "DLSE010001232024")
    judgment = c.get("/api/research/judgments/demo_library/demo-2025-1-12").json()
    assert judgment["paragraphs"][0]["text"].startswith("FICTIONAL JUDGMENT")
    saved = c.post(f"/api/cases/{aamir}/authorities", json={"source": "demo_library", "doc_id": "demo-2025-1-12", "paragraph": 4}).json()
    assert saved["quote"] == judgment["paragraphs"][3]["text"] and saved["standing"] == "demo"
    assert c.get(f"/api/cases/{aamir}").json()["authorities"][0]["id"] == saved["id"]
    assert c.post(f"/api/cases/{aamir}/authorities", json={"source": "demo_library", "doc_id": "demo-2025-1-12", "paragraph": 99}).status_code == 400
    assert c.delete(f"/api/cases/{aamir}/authorities/{saved['id']}").json() == {"ok": True}
    offline = c.post(f"/api/cases/{aamir}/research", json={"question": "first-time offender section 479"}).json()
    assert offline["answer"] is None and offline["hits"]


def test_the_researcher_cannot_rely_on_a_paragraph_it_has_not_read():
    store, _ = client()
    aamir = next(x for x in store.all() if x.cnr == "DLSE010001232024")
    tools = case_tools(store, aamir.id, as_of=TODAY, research=demo_library())
    call = lambda name, args: tools.handle(WireEvent("ToolCallRequest", {"name": name, "arguments": json.dumps(args)}))  # noqa: E731
    args = {"source": "demo_library", "doc_id": "demo-2025-1-12", "paragraph": 4}
    assert call("manu_authority_save", args)["is_error"]
    assert not call("manu_judgment_read", {"source": "demo_library", "doc_id": "demo-2025-1-12"})["is_error"]
    assert not call("manu_authority_save", args)["is_error"]
    assert store.get(aamir.id).authorities[0].paragraph == 4
