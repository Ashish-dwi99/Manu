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


def demo_client():
    from manu.connectors import DemoConnector
    from manu.demo import FIXTURES

    store = CaseStore()
    seed(store, today=TODAY)
    return TestClient(create_app(store, ConnectorLadder([DemoConnector(FIXTURES / "day1", today=TODAY)])))


def case_id(c, cnr):
    return next(x["id"] for x in c.get("/api/cases").json()["cases"] if x["cnr"] == cnr)


def test_a_note_is_a_human_fact_on_the_case_and_its_timeline():
    c = client()
    aamir = case_id(c, "DLSE010001232024")
    note = c.post(f"/api/cases/{aamir}/notes", json={"text": "APP sought time; IO absent.", "on": "2026-09-24"}).json()
    assert note["source"] == {"kind": "human", "connector": "human", "verification": "human_confirmed"}
    detail = c.get(f"/api/cases/{aamir}").json()
    assert detail["notes"][0]["text"] == "APP sought time; IO absent."
    assert detail["last_note"]["id"] == note["id"]
    assert any(item["kind"] == "note" for item in detail["timeline"])
    assert c.delete(f"/api/cases/{aamir}/notes/{note['id']}").json() == {"ok": True}
    assert c.get(f"/api/cases/{aamir}").json()["notes"] == []


def test_today_is_in_cause_list_order_with_item_and_hall():
    body = demo_client().get("/api/diary/day", params={"on": TODAY.isoformat()}).json()
    assert [e["listing"]["item"] for e in body["entries"]] == ["14", "22", "31"]
    assert body["entries"][0]["listing"]["court_hall"].startswith("Court Room 312")


def test_boards_say_where_the_court_is_and_how_many_items_are_ahead():
    body = demo_client().get("/api/boards", params={"on": TODAY.isoformat()}).json()
    board = body["boards"][0]
    assert board["connector"] == "demo"
    assert [y["item"] for y in board["yours"]] == ["14", "22", "31"]
    assert board["state"] in {"in_session", "not_started", "risen"}
    unavailable = client().get("/api/boards", params={"on": TODAY.isoformat()}).json()["boards"][0]
    assert unavailable["state"] == "unknown" and unavailable["unavailable"]


def test_simulated_board_advances_through_the_day():
    from datetime import UTC, datetime

    from manu.connectors.sources import _simulated_board

    spec = {"sits": "10:30", "lunch_from": "13:30", "lunch_to": "14:00", "rises": "16:30", "minutes_per_item": 8, "items": 40}
    at = lambda hh, mm: datetime(2026, 9, 24, hh, mm, tzinfo=UTC)  # noqa: E731 - UTC; IST is +5:30
    assert _simulated_board("X", "", spec, at(4, 0)).state == "not_started"
    assert _simulated_board("X", "", spec, at(5, 30)).current_item == "4"  # 11:00 IST: 30 min at 8 min an item
    assert _simulated_board("X", "", spec, at(11, 30)).state == "risen"  # 17:00 IST


def test_import_by_advocate_name_finds_cases_and_follows_the_chosen_ones():
    c = demo_client()
    found = c.get("/api/import/advocate", params={"name": "r mehta"}).json()
    by_cnr = {h["cnr"]: h for h in found["hits"]}
    assert by_cnr["DLSE010001232024"]["following"] is True
    assert by_cnr["DLSE010006782025"]["following"] is False
    assert "DLSE030009912024" in by_cnr
    result = c.post("/api/cases/import", json={"cnrs": ["DLSE010006782025", "DLSE030009912024", "nonsense"]}).json()
    assert len(result["followed"]) == 2 and "nonsense" in result["failed"]
    assert c.get("/api/import/advocate", params={"name": "r mehta"}).json()["hits"][-1]["following"] is True
    assert client().get("/api/import/advocate", params={"name": "r mehta"}).json()["hits"] == []


def test_a_limitation_deadline_lands_in_the_diary_with_its_working():
    c = client()
    aamir = case_id(c, "DLSE010001232024")
    request = {"rule": "crl_appeal_conviction_hc", "start": "2026-09-23", "on": TODAY.isoformat()}
    computed = c.post("/api/law/limitation", json=request).json()
    assert computed["file_by"] == "2026-11-23" and computed["status"] == "running"
    saved = c.post(f"/api/cases/{aamir}/deadlines", json=request).json()["obligation"]
    assert saved["due"] == "2026-11-23" and saved["source"]["kind"] == "human"
    assert "s.12(1)" in saved["source"]["quote"].splitlines()[1]
    assert c.post("/api/law/limitation", json={**request, "rule": "nope"}).status_code == 400
    assert len(c.get("/api/law/limitation").json()["rules"]) >= 10
