from datetime import date

from fastapi.testclient import TestClient

from manu.api import create_app
from manu.case_state.store import CaseStore
from manu.connectors import ConnectorLadder
from manu.demo import seed

TODAY = date(2026, 9, 24)


def client():
    store = CaseStore()
    seed(store, today=TODAY)
    return TestClient(create_app(store, ConnectorLadder([])))


def test_judge_day_has_labels_and_never_a_recommendation():
    body = client().get("/api/diary/day", params={"on": TODAY.isoformat(), "lens": "judge"}).json()
    assert body["count"] == 3
    labels = {e["title"]: [label["code"] for label in e["labels"]] for e in body["entries"]}
    assert "URGENT" in labels["State v. Imran & Anr."]
    assert "WOMAN" in labels["State v. Ritu Sharma"]
    assert labels["State v. Deepak"] == ["DATA GAP"]


def test_case_detail_shows_s479_working_and_bail_facts():
    c = client()
    cases = c.get("/api/cases").json()["cases"]
    aamir = next(x for x in cases if x["cnr"] == "DLSE010001232024")
    detail = c.get(f"/api/cases/{aamir['id']}", params={"on": TODAY.isoformat(), "lens": "judge"}).json()
    s = detail["criminal"]["accused"][0]["s479"]
    assert s["status"] == "approaching"
    assert any("12 months" in line for line in s["working"])
    assert detail["bail_facts"]["note"].startswith("Facts only")
    assert len(detail["bail_facts"]["factors"]) == 6


def test_confirming_an_obligation_upgrades_its_source():
    c = client()
    cases = c.get("/api/cases").json()["cases"]
    aamir = next(x for x in cases if x["cnr"] == "DLSE010001232024")
    detail = c.get(f"/api/cases/{aamir['id']}").json()
    obligation = detail["obligations"][0]
    confirmed = c.post(f"/api/cases/{aamir['id']}/obligations/{obligation['id']}", json={"status": "confirmed"}).json()
    assert confirmed["source"]["verification"] == "human_confirmed"


def test_track_rejects_non_cnr():
    assert client().post("/api/cases", json={"cnr": "not-a-cnr-at-all-x"}).status_code == 400


def test_changes_feed():
    events = client().get("/api/diary/changes").json()["events"]
    assert any(e["kind"] == "hearing_date_changed" for e in events)
