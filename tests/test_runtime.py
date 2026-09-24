import json
import sys
from datetime import date
from pathlib import Path

import pytest

from manu.case_state.store import CaseStore
from manu.demo import seed
from manu.runtime import agent as agent_module
from manu.runtime.tools import FORBIDDEN_ACTIONS, Tier, ToolRegistry, ToolSpec, case_tools
from manu.runtime.wire import KimiWireClient

FAKE = Path(__file__).parent / "fakes" / "fake_kimi.py"
TODAY = date(2026, 9, 24)


def seeded():
    store = CaseStore()
    seed(store, today=TODAY)
    case = next(c for c in store.all() if c.cnr == "DLSE010001232024")
    return store, case


def fake_client(script, tools, monkeypatch):
    monkeypatch.setenv("FAKE_KIMI_SCRIPT", json.dumps(script))
    return KimiWireClient(
        [sys.executable, str(FAKE)],
        cwd=Path.cwd(),
        timeout_seconds=20,
        external_tools=tools.external_tools(),
        tool_call_handler=tools.handle,
    )


def test_order_reader_round_trip_accepts_only_verbatim_quotes(monkeypatch):
    store, case = seeded()
    last = case.last_order
    quote = "the SHO concerned shall remain present in person"
    assert quote in last.text
    tools = case_tools(store, case.id, as_of=TODAY)
    before = len(store.get(case.id).obligations)
    script = [
        {"kind": "tool", "name": "manu_case_read"},
        {"kind": "tool", "name": "manu_order_text", "arguments": {"on": last.on.isoformat()}},
        {
            "kind": "tool",
            "name": "manu_obligations_propose",
            "arguments": {
                "order_on": last.on.isoformat(),
                "obligations": [
                    {"who": "SHO", "what": "Appear in person if the reply is not filed.", "quote": quote},
                    {"who": "Accused", "what": "Invented direction", "quote": "the accused shall pay Rs. 1 crore"},
                ],
            },
        },
        {"kind": "text", "text": "Adjourned; IO to reply; SHO to appear if not."},
    ]
    result = fake_client(script, tools, monkeypatch).run_prompt("Read the order.")
    assert result.status == "finished"
    assert result.text == "Adjourned; IO to reply; SHO to appear if not."
    assert [r["tool"] for r in tools.receipts] == ["manu_case_read", "manu_order_text", "manu_obligations_propose"]
    assert not any(r["is_error"] for r in tools.receipts)
    stored = store.get(case.id)
    assert len(stored.obligations) == before + 1
    added = stored.obligations[-1]
    assert added.source.quote == quote and added.source.verification == "lead"
    assert last.text[added.source.span_start : added.source.span_end] == quote


def test_native_approval_requests_are_refused_by_default(monkeypatch):
    store, case = seeded()
    tools = case_tools(store, case.id, as_of=TODAY)
    result = fake_client([{"kind": "approval"}], tools, monkeypatch).run_prompt("x")
    assert "[approval:reject]" in result.text


def test_unknown_tool_is_an_error_inside_the_loop(monkeypatch):
    store, case = seeded()
    tools = case_tools(store, case.id, as_of=TODAY)
    fake_client([{"kind": "tool", "name": "file_in_court"}], tools, monkeypatch).run_prompt("x")
    assert tools.receipts[-1]["is_error"]


def test_forbidden_actions_cannot_be_registered():
    registry = ToolRegistry()
    for name in FORBIDDEN_ACTIONS:
        with pytest.raises(ValueError):
            registry.register(ToolSpec(name, "", {}, Tier.AUTO_READ, lambda a: a))
    with pytest.raises(ValueError):
        registry.register(ToolSpec("x", "", {}, Tier.HIGH_RISK, lambda a: a))


def test_confirm_write_needs_a_person():
    from manu.runtime.wire import WireEvent

    calls = []
    registry = ToolRegistry(approver=lambda name, args: False)
    registry.register(ToolSpec("change_record", "", {}, Tier.CONFIRM_WRITE, lambda a: calls.append(a) or "ok"))
    value = registry.handle(WireEvent("ToolCallRequest", {"name": "change_record", "arguments": "{}"}))
    assert value["is_error"] and calls == []


def test_agent_specs_exist_and_gate_on_their_output():
    for name, gate in (("order-reader", "manu_obligations_propose"), ("hearing-brief", "manu_brief_save")):
        spec = (agent_module.AGENTS_DIR / name / "agent.yaml").read_text()
        assert gate in spec
        assert (agent_module.AGENTS_DIR / name / "system.md").is_file()


def test_run_agent_requires_a_key_and_binary(monkeypatch):
    store, case = seeded()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(agent_module.RuntimeUnavailable):
        agent_module.read_order(store, case.id, case.last_order.on)


def test_run_agent_builds_the_kimi_command(monkeypatch, tmp_path):
    store, case = seeded()
    binary = tmp_path / "kimi-agent"
    binary.write_text("")
    monkeypatch.setenv("MANU_KIMI_AGENT_BIN", str(binary))
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-leak")
    seen = {}

    class Recorder:
        def __init__(self, argv, **kwargs):
            seen["argv"], seen["kwargs"] = argv, kwargs

        def run_prompt(self, prompt, **_):
            from manu.runtime.wire import WireResult

            seen["prompt"] = prompt
            return WireResult("finished", "ok")

    run = agent_module.read_order(store, case.id, case.last_order.on, client_factory=Recorder)
    assert run.result.status == "finished"
    argv = seen["argv"]
    assert argv[0] == str(binary) and "--agent-file" in argv
    assert argv[argv.index("--agent-file") + 1].endswith("order-reader/agent.yaml")
    env = seen["kwargs"]["env"]
    assert env["KIMI_API_KEY"] == "sk-test" and "ANTHROPIC_API_KEY" not in env and "OPENROUTER_API_KEY" not in env
    names = {t["name"] for t in seen["kwargs"]["external_tools"]}
    assert {"manu_case_read", "manu_order_text", "manu_obligations_propose"} <= names


def test_case_assistant_reads_documents_through_the_wire(monkeypatch):
    from manu.documents import DocumentStore

    store, case = seeded()
    documents = DocumentStore(store)
    tools = case_tools(store, case.id, as_of=TODAY, documents=documents)
    fir = next(d for d in documents.for_case(case.id) if d.name.startswith("FIR"))
    script = [
        {"kind": "tool", "name": "manu_documents_search", "arguments": {"query": "recovered"}},
        {"kind": "tool", "name": "manu_document_page", "arguments": {"document_id": fir.id, "page": 2}},
        {"kind": "text", "text": "11 cartons were recovered [FIR, p. 2]."},
    ]
    result = fake_client(script, tools, monkeypatch).run_prompt("What was recovered?")
    assert result.text == "11 cartons were recovered [FIR, p. 2]."
    assert [r["is_error"] for r in tools.receipts] == [False, False]
    assert (agent_module.AGENTS_DIR / "case-assistant" / "agent.yaml").is_file()
