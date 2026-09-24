# Running agents on the Chotu runtime

Manu does not have its own agent loop. Its agents run on **kimi-agent-rs**, the Chotu
runtime (Apache-2.0, a Rust port of Moonshot's kimi-cli, extended in Tura with the Jev
director, completion gates and Dhee-aware compaction). Manu talks to it over the wire
protocol (JSON-RPC over stdio).

## Build the runtime

From a Tura checkout:

```bash
cd subsystems/sankhya/third_party/kimi-agent-rs
cargo build -p kimi-agent --release
export MANU_KIMI_AGENT_BIN=$PWD/target/release/kimi-agent
```

## Configure

| Variable | Meaning | Default |
| --- | --- | --- |
| `MANU_KIMI_AGENT_BIN` | path to `kimi-agent` | `kimi-agent` on PATH |
| `OPENROUTER_API_KEY` | model key (BYOK) | — required |
| `MANU_MODEL` | model id | `openai/gpt-oss-120b` |
| `MANU_MODEL_BASE_URL` | OpenAI-compatible base URL | `https://openrouter.ai/api/v1` |
| `CHOTU_DECISIONS_ENABLED` | `0` turns off Jev routing | on when the provider is OpenRouter |

Every other `*_API_KEY` is removed from the agent's environment.

## What one agent run is

```text
manu.runtime.agent.read_order(store, case_id, order_on)
  → case_tools(store, case_id)            5 tools, scoped to this case
  → kimi-agent --config … --agent-file agents/order-reader/agent.yaml
      initialize {external_tools: Manu's tools}
      prompt "Read the order dated …"
        model → ToolCall manu_case_read       → Manu answers over the wire
        model → ToolCall manu_order_text      → …
        model → ToolCall manu_obligations_propose
                  (quotes checked verbatim against the order; misses refused)
        completion gate satisfied → TurnEnd
  → AgentRun(result, receipts)            one receipt per tool call
```

## Tools

| Tool | Tier | Does |
| --- | --- | --- |
| `manu_case_read` | auto_read | The case record, with Section 479 / default-bail working |
| `manu_order_text` | auto_read | Full text of one order |
| `manu_bail_facts` | auto_read | The six bail facts with sources and gaps |
| `manu_obligations_propose` | auto_action | Adds `lead` obligations. Quote must be verbatim. A person confirms |
| `manu_brief_save` | auto_action | Saves a hearing brief as a `brief_prepared` event |

`confirm_write` tools ask a person through an `Approver` before running. `high_risk` tools
are not exposed at all, and `FORBIDDEN_ACTIONS` (filing, portal mutation, payment,
contacting clients or the other side, final opinions without review) cannot be registered.
Native approval requests from the runtime are refused by default.

## Verified

`tests/test_runtime.py` drives the wire protocol end to end against a scripted stand-in
process. The same flow was also run against a real `kimi-agent` release build (both
agent specs load, all five tools register, and a three-step turn against a local
OpenAI-compatible server completed through the completion gate).
