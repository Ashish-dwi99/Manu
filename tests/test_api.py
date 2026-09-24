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


def test_day_has_labels_for_everyone_and_never_a_recommendation():
    body = client().get("/api/diary/day", params={"on": TODAY.isoformat()}).json()
    assert body["count"] == 3
    labels = {e["title"]: [label["code"] for label in e["labels"]] for e in body["entries"]}
    assert "URGENT" in labels["State v. Imran & Anr."]
    assert "WOMAN" in labels["State v. Ritu Sharma"]
    assert labels["State v. Deepak"] == ["DATA GAP"]


def test_case_detail_shows_s479_working_and_bail_facts():
    c = client()
    cases = c.get("/api/cases").json()["cases"]
    aamir = next(x for x in cases if x["cnr"] == "DLSE010001232024")
    detail = c.get(f"/api/cases/{aamir['id']}", params={"on": TODAY.isoformat()}).json()
    s = detail["criminal"]["accused"][0]["s479"]
    assert s["status"] == "approaching"
    assert any("12 months" in line for line in s["working"])
    assert detail["bail_facts"]["note"].startswith("Facts only")
    assert len(detail["bail_facts"]["factors"]) == 6


def test_an_order_can_be_read_in_full_so_a_direction_is_seen_in_place():
    c = client()
    cases = c.get("/api/cases").json()["cases"]
    aamir = next(x for x in cases if x["cnr"] == "DLSE010001232024")
    detail = c.get(f"/api/cases/{aamir['id']}").json()
    direction = next(o for o in detail["obligations"] if "29.09.2026" in o["what"])
    order = next(o for o in detail["orders"] if o["uri"] == direction["source"]["uri"])
    body = c.get(f"/api/cases/{aamir['id']}/orders/{order['on']}").json()
    assert direction["source"]["quote"] in body["text"]
    assert body["source"]["uri"] == direction["source"]["uri"]
    assert c.get(f"/api/cases/{aamir['id']}/orders/2001-01-01").status_code == 404


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
