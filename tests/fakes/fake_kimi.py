"""A stand-in for `kimi-agent` that speaks wire protocol 1.1 and follows a script.

It proves Manu's side of the protocol without a model: initialize with external tools,
prompt, tool-call requests answered by Manu, streamed text, and the prompt's result.
The script is read from the FAKE_KIMI_SCRIPT environment variable (JSON list of steps).
"""

import json
import os
import sys


def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def receive():
    line = sys.stdin.readline()
    if not line:
        sys.exit(0)
    return json.loads(line)


init = receive()
assert init["method"] == "initialize"
tools = [t["name"] for t in init["params"].get("external_tools", [])]
send({"jsonrpc": "2.0", "id": init["id"], "result": {"protocol_version": "1.1", "external_tools": {"accepted": tools}}})
prompt = receive()
assert prompt["method"] == "prompt"
send(
    {
        "jsonrpc": "2.0",
        "method": "event",
        "params": {"type": "TurnBegin", "payload": {"user_input": prompt["params"]["user_input"]}},
    }
)
for n, step in enumerate(json.loads(os.environ["FAKE_KIMI_SCRIPT"])):
    if step["kind"] == "tool":
        request_id = f"req-{n}"
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "request",
                "params": {
                    "type": "ToolCallRequest",
                    "payload": {
                        "id": f"call-{n}",
                        "name": step["name"],
                        "arguments": json.dumps(step.get("arguments", {})),
                    },
                },
            }
        )
        reply = receive()
        assert reply["id"] == request_id, reply
        send(
            {
                "jsonrpc": "2.0",
                "method": "event",
                "params": {
                    "type": "ToolResult",
                    "payload": {"tool_call_id": f"call-{n}", "return_value": reply["result"]["return_value"]},
                },
            }
        )
    elif step["kind"] == "approval":
        request_id = f"req-{n}"
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "request",
                "params": {
                    "type": "ApprovalRequest",
                    "payload": {
                        "id": f"ap-{n}",
                        "tool_call_id": "x",
                        "sender": "Shell",
                        "action": "run",
                        "description": "rm -rf /",
                    },
                },
            }
        )
        reply = receive()
        send(
            {
                "jsonrpc": "2.0",
                "method": "event",
                "params": {
                    "type": "ContentPart",
                    "payload": {"type": "text", "text": f"[approval:{reply['result']['response']}]"},
                },
            }
        )
    elif step["kind"] == "text":
        send(
            {
                "jsonrpc": "2.0",
                "method": "event",
                "params": {"type": "ContentPart", "payload": {"type": "text", "text": step["text"]}},
            }
        )
send({"jsonrpc": "2.0", "id": prompt["id"], "result": {"status": "finished"}})
