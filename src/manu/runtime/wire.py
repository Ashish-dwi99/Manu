"""JSON-RPC client for `kimi-agent` (the Chotu runtime) over stdio, wire protocol 1.1.

One prompt, one agent process. The client:

* sends `initialize` with Manu's tools as `external_tools` — Kimi registers them next to
  its native tools and sends a `ToolCallRequest` back whenever the model calls one;
* sends `prompt`, then streams `event` messages (text, steps, tool calls) to a callback;
* answers `request` messages: `ToolCallRequest` through Manu's tool bridge, and
  `ApprovalRequest` (a native tool asking permission) through Manu's approval policy;
* on cancel, sends `cancel`, then terminates the process.

Adapted from Chotu's hub client (`agent_core/kimi_wire.py`), minus the hub's agent-slot
lane: Manu runs agents from background jobs, one at a time per case.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

WIRE_PROTOCOL_VERSION = "1.1"


class KimiWireError(RuntimeError):
    pass


class KimiWireTimeout(KimiWireError):
    pass


@dataclass
class WireEvent:
    type_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class WireResult:
    status: str
    text: str
    events: list[WireEvent] = field(default_factory=list)
    stderr: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[[WireEvent], dict[str, Any]]
ApprovalHandler = Callable[[WireEvent], str]


class KimiWireClient:
    def __init__(
        self,
        argv: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        timeout_seconds: float = 300,
        idle_timeout_seconds: float | None = 120,
        external_tools: list[dict[str, Any]] | None = None,
        tool_call_handler: ToolHandler | None = None,
        approval_handler: ApprovalHandler | None = None,
    ) -> None:
        self.argv = argv
        self.cwd = cwd
        self.env = env
        self.timeout_seconds = timeout_seconds
        self.idle_timeout_seconds = idle_timeout_seconds
        self.external_tools = external_tools or []
        self.tool_call_handler = tool_call_handler
        # Default is refusal: a native tool that asks permission gets it only from policy.
        self.approval_handler = approval_handler or (lambda _event: "reject")

    def run_prompt(
        self,
        prompt: str,
        *,
        on_event: Callable[[WireEvent], None] | None = None,
        cancel: Event | None = None,
    ) -> WireResult:
        process = subprocess.Popen(
            self.argv,
            cwd=str(self.cwd),
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        lines: queue.Queue[str | None] = queue.Queue()
        stderr: list[str] = []
        threading.Thread(target=_pump, args=(process.stdout, lines), daemon=True).start()
        threading.Thread(target=_collect, args=(process.stderr, stderr), daemon=True).start()
        deadline = time.monotonic() + self.timeout_seconds
        last_activity = [time.monotonic()]
        events: list[WireEvent] = []
        text: list[str] = []
        try:
            init: dict[str, Any] = {
                "protocol_version": WIRE_PROTOCOL_VERSION,
                "client": {"name": "manu", "version": "0.1"},
            }
            if self.external_tools:
                init["external_tools"] = self.external_tools
            init_id = self._send(process, "initialize", init)
            init_response = self._await(process, lines, init_id, deadline, last_activity)
            prompt_id = self._send(process, "prompt", {"user_input": prompt})
            raw: dict[str, Any] = {"initialize": init_response.get("result") or {}}
            while True:
                if cancel is not None and cancel.is_set():
                    self._cancel(process)
                    return WireResult(
                        "cancelled", "".join(text).strip(), events, "".join(stderr), {"status": "cancelled"}
                    )
                msg = self._read(process, lines, deadline, last_activity)
                method = msg.get("method")
                if method == "event":
                    event = _parse_event(msg.get("params"))
                    if event is None:
                        continue
                    if event.type_name == "TurnBegin" and text:
                        # The runtime restarts a turn after a bad generation and re-emits
                        # the reply from the top; the abandoned draft goes with it.
                        text.clear()
                    events.append(event)
                    if on_event:
                        on_event(event)
                    if event.type_name == "ContentPart" and event.payload.get("type") == "text":
                        text.append(str(event.payload.get("text", "")))
                    continue
                if method == "request":
                    event = self._answer(process, msg)
                    if event is not None:
                        events.append(event)
                        if on_event:
                            on_event(event)
                    continue
                if msg.get("id") == prompt_id:
                    if "error" in msg:
                        detail = msg["error"].get("message", "prompt failed")
                        if not "".join(text).strip():
                            raise KimiWireError(detail)
                        raw.update({"status": "incomplete", "error": detail})
                    else:
                        raw.update(msg.get("result") or {})
                    break
            return WireResult(str(raw.get("status", "")), "".join(text).strip(), events, "".join(stderr), raw)
        finally:
            _reap(process)

    # -- protocol -----------------------------------------------------------------------

    def _answer(self, process: subprocess.Popen[str], msg: dict[str, Any]) -> WireEvent | None:
        request_id = str(msg.get("id", ""))
        event = _parse_event(msg.get("params"))
        if event is None:
            self._reply_error(process, request_id, "Invalid wire request.")
            return None
        if event.type_name == "ApprovalRequest":
            response = self.approval_handler(event)
            self._reply(process, request_id, {"request_id": event.payload.get("id", request_id), "response": response})
            return event
        if event.type_name == "ToolCallRequest":
            tool_call_id = str(event.payload.get("id") or request_id)
            if self.tool_call_handler is None:
                self._reply_error(process, request_id, "No external tool handler.")
                return event
            try:
                value = self.tool_call_handler(event)
            except Exception as exc:  # noqa: BLE001 - a tool failure belongs inside the agent loop
                value = tool_error(f"{type(exc).__name__}: {exc}")
            self._reply(process, request_id, {"tool_call_id": tool_call_id, "return_value": value})
            return event
        self._reply_error(process, request_id, f"Unsupported wire request: {event.type_name}")
        return event

    def _send(self, process: subprocess.Popen[str], method: str, params: dict[str, Any]) -> str:
        request_id = f"{method}-{uuid4()}"
        _write(process, {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return request_id

    def _reply(self, process: subprocess.Popen[str], request_id: str, result: dict[str, Any]) -> None:
        _write(process, {"jsonrpc": "2.0", "id": request_id, "result": result})

    def _reply_error(self, process: subprocess.Popen[str], request_id: str, message: str) -> None:
        _write(process, {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": message}})

    def _await(self, process, lines, request_id, deadline, last_activity) -> dict[str, Any]:
        while True:
            msg = self._read(process, lines, deadline, last_activity)
            if msg.get("method") == "request":
                self._answer(process, msg)
                continue
            if msg.get("id") == request_id:
                if "error" in msg:
                    raise KimiWireError(msg["error"].get("message", "request failed"))
                return msg

    def _read(self, process, lines, deadline, last_activity) -> dict[str, Any]:
        while True:
            now = time.monotonic()
            if now >= deadline:
                raise KimiWireTimeout(f"agent run exceeded {self.timeout_seconds:g}s")
            if self.idle_timeout_seconds and now - last_activity[0] >= self.idle_timeout_seconds:
                raise KimiWireTimeout(f"agent silent for {self.idle_timeout_seconds:g}s")
            try:
                line = lines.get(timeout=0.2)
            except queue.Empty:
                if process.poll() is not None and lines.empty():
                    raise KimiWireError(f"agent exited with code {process.returncode}") from None
                continue
            if line is None:
                if process.poll() is not None:
                    raise KimiWireError(f"agent exited with code {process.returncode}")
                continue
            last_activity[0] = time.monotonic()
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                logger.debug("non-JSON line from agent: %s", line.rstrip())
                continue
            if isinstance(value, dict):
                return value

    @staticmethod
    def _cancel(process: subprocess.Popen[str]) -> None:
        try:
            _write(process, {"jsonrpc": "2.0", "id": f"cancel-{uuid4()}", "method": "cancel", "params": {}})
        except (OSError, ValueError):
            pass


def tool_result(output: Any, *, message: str = "Done.") -> dict[str, Any]:
    text = output if isinstance(output, str) else json.dumps(output, separators=(",", ":"), sort_keys=True, default=str)
    return {"is_error": False, "output": text, "message": message, "display": [{"type": "brief", "text": message}]}


def tool_error(message: str) -> dict[str, Any]:
    return {"is_error": True, "output": "", "message": message, "display": [{"type": "brief", "text": message}]}


def _parse_event(value: Any) -> WireEvent | None:
    if not isinstance(value, dict):
        return None
    type_name, payload = value.get("type"), value.get("payload")
    if not isinstance(type_name, str) or not isinstance(payload, dict):
        return None
    return WireEvent(type_name, payload)


def _write(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
    if process.stdin is None:
        raise KimiWireError("agent stdin closed")
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _pump(stream, out: queue.Queue[str | None]) -> None:
    try:
        if stream is not None:
            for line in stream:
                out.put(line)
    finally:
        out.put(None)


def _collect(stream, out: list[str]) -> None:
    if stream is not None:
        for line in stream:
            out.append(line)


def _reap(process: subprocess.Popen[str]) -> None:
    """Every path releases the process and its pipes, or a long-running server
    accumulates zombie agents."""
    try:
        if process.poll() is None:
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
    except Exception:  # noqa: BLE001
        pass
    for stream in (process.stdin, process.stdout, process.stderr):
        try:
            if stream is not None:
                stream.close()
        except Exception:  # noqa: BLE001
            pass
