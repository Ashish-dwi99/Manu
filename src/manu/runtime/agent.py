"""Run a Manu agent on the Chotu runtime (`kimi-agent`).

The runtime owns the loop: model calls, the Jev director's routing, retries,
compaction, cancellation, and the completion gate. Manu supplies the agent spec (a
YAML + system prompt in `agents/`), the tools for one case, and the model settings.

Configuration (environment):

* `MANU_KIMI_AGENT_BIN` — path to the `kimi-agent` binary, built from Chotu's
  `subsystems/sankhya/third_party/kimi-agent-rs` (`cargo build -p kimi-agent --release`).
  Falls back to `kimi-agent` on PATH.
* `OPENROUTER_API_KEY` — the model key (OpenRouter BYOK, as in Chotu).
* `MANU_MODEL` — model id (default `openai/gpt-oss-120b`, Chotu's agent default).
* `MANU_MODEL_BASE_URL` — default `https://openrouter.ai/api/v1`.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from threading import Event

from manu.case_state.store import CaseStore
from manu.runtime.tools import Approver, ToolRegistry, case_tools
from manu.runtime.wire import KimiWireClient, WireEvent, WireResult

AGENTS_DIR = Path(__file__).resolve().parent / "agents"
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class RuntimeUnavailable(RuntimeError):
    pass


@dataclass
class AgentRun:
    result: WireResult
    receipts: list[dict]


def kimi_binary() -> str:
    configured = os.getenv("MANU_KIMI_AGENT_BIN", "").strip()
    if configured:
        if not Path(configured).is_file():
            raise RuntimeUnavailable(f"MANU_KIMI_AGENT_BIN={configured} does not exist")
        return configured
    found = shutil.which("kimi-agent")
    if not found:
        raise RuntimeUnavailable("kimi-agent not found: build it from Chotu and set MANU_KIMI_AGENT_BIN")
    return found


def inline_config(*, model: str, base_url: str, max_steps: int = 24) -> str:
    return json.dumps(
        {
            "default_model": "manu_main",
            "default_thinking": False,
            "providers": {"openrouter": {"type": "kimi", "base_url": base_url, "api_key": "", "prompt_cache": True}},
            "models": {"manu_main": {"provider": "openrouter", "model": model, "max_context_size": 262144}},
            "loop_control": {
                "max_steps_per_turn": max_steps,
                "max_retries_per_step": 2,
                "max_ralph_iterations": 0,
                "reserved_context_size": 50000,
            },
        },
        separators=(",", ":"),
    )


def agent_env(work_dir: Path, *, api_key: str, model: str, base_url: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not (k.endswith("_API_KEY") or "_API_KEY_" in k)}
    env.update(
        {
            "KIMI_HOME": str(work_dir / "kimi"),
            "KIMI_SHARE_DIR": str(work_dir / "kimi"),
            "KIMI_BASE_URL": base_url,
            "KIMI_API_KEY": api_key,
            "KIMI_MODEL_NAME": model,
            "CHOTU_AGENT_RUNTIME_PROFILE": "manu",
            "CHOTU_WORKSPACE_SCOPED_FILE_TOOLS": "1",
        }
    )
    return env


def run_agent(
    agent: str,
    prompt: str,
    tools: ToolRegistry,
    *,
    on_event: Callable[[WireEvent], None] | None = None,
    cancel: Event | None = None,
    timeout_seconds: float = 300,
    client_factory: Callable[..., KimiWireClient] = KimiWireClient,
) -> AgentRun:
    agent_file = AGENTS_DIR / agent / "agent.yaml"
    if not agent_file.is_file():
        raise RuntimeUnavailable(f"unknown agent {agent!r}")
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeUnavailable("OPENROUTER_API_KEY is not set")
    model = os.getenv("MANU_MODEL", DEFAULT_MODEL)
    base_url = os.getenv("MANU_MODEL_BASE_URL", DEFAULT_BASE_URL)
    with tempfile.TemporaryDirectory(prefix="manu-agent-") as tmp:
        work_dir = Path(tmp)
        client = client_factory(
            [
                kimi_binary(),
                "--config",
                inline_config(model=model, base_url=base_url),
                "--agent-file",
                str(agent_file),
                "--work-dir",
                str(work_dir),
            ],
            cwd=work_dir,
            env=agent_env(work_dir, api_key=api_key, model=model, base_url=base_url),
            timeout_seconds=timeout_seconds,
            external_tools=tools.external_tools(),
            tool_call_handler=tools.handle,
        )
        result = client.run_prompt(prompt, on_event=on_event, cancel=cancel)
    return AgentRun(result=result, receipts=list(tools.receipts))


def read_order(
    store: CaseStore, case_id: str, order_on: date, *, approver: Approver | None = None, **kwargs
) -> AgentRun:
    tools = case_tools(store, case_id, approver=approver)
    prompt = f"Read the order dated {order_on.isoformat()} in this case and record every direction it gives."
    return run_agent("order-reader", prompt, tools, **kwargs)


def prepare_hearing_brief(store: CaseStore, case_id: str, *, approver: Approver | None = None, **kwargs) -> AgentRun:
    tools = case_tools(store, case_id, approver=approver)
    return run_agent("hearing-brief", "Prepare the hearing brief for this case's next date.", tools, **kwargs)
