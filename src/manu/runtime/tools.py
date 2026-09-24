"""Manu's tools for the Chotu runtime, and the rules they run under.

Each tool has a permission tier (the same four Chotu uses):

* `auto_read`     — reads the diary. Runs without asking.
* `auto_action`   — writes something reversible that a person reviews anyway (a
                    proposed obligation is a `lead` until confirmed). Runs without asking.
* `confirm_write` — changes the record in a way a person should approve first.
* `high_risk`     — never exposed to a model in v1.

And some actions do not exist at all. Manu never files, pays, submits to a court portal,
or contacts a party. Those are not tools with a "deny" switch; they are absent, and
`FORBIDDEN_ACTIONS` is checked so no future tool can be registered under those names.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from manu import diary, judge
from manu.case_state.models import CaseEvent, Obligation
from manu.case_state.store import CaseStore, new_id
from manu.runtime.wire import WireEvent, tool_error, tool_result


class Tier(StrEnum):
    AUTO_READ = "auto_read"
    AUTO_ACTION = "auto_action"
    CONFIRM_WRITE = "confirm_write"
    HIGH_RISK = "high_risk"


FORBIDDEN_ACTIONS = frozenset(
    {
        "external_filing",
        "court_portal_mutation",
        "payment",
        "client_contact",
        "opposing_party_contact",
        "final_legal_opinion_without_advocate_review",
    }
)

Approver = Callable[[str, dict[str, Any]], bool]
"""(tool name, arguments) → approved? Wired to the UI's approval card."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    tier: Tier
    handler: Callable[[dict[str, Any]], Any]


class ToolRegistry:
    def __init__(self, approver: Approver | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._approver = approver or (lambda _name, _args: False)
        self.receipts: list[dict[str, Any]] = []

    def register(self, spec: ToolSpec) -> None:
        if spec.name in FORBIDDEN_ACTIONS or any(action in spec.name for action in FORBIDDEN_ACTIONS):
            raise ValueError(f"{spec.name} is a forbidden action")
        if spec.tier == Tier.HIGH_RISK:
            raise ValueError(f"{spec.name}: high-risk tools are not exposed to agents in v1")
        self._tools[spec.name] = spec

    def names(self) -> list[str]:
        return sorted(self._tools)

    def external_tools(self) -> list[dict[str, Any]]:
        """The `external_tools` block for Kimi's `initialize`."""
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters} for t in self._tools.values()
        ]

    def handle(self, event: WireEvent) -> dict[str, Any]:
        """Answer one `ToolCallRequest`. Every call leaves a receipt."""
        name = str(event.payload.get("name") or "")
        spec = self._tools.get(name)
        if spec is None:
            return self._receipt(name, {}, tool_error(f"Unknown tool {name!r}."))
        try:
            raw = event.payload.get("arguments") or "{}"
            args = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except (TypeError, ValueError):
            return self._receipt(name, {}, tool_error("Arguments were not valid JSON."))
        if spec.tier == Tier.CONFIRM_WRITE and not self._approver(name, args):
            return self._receipt(name, args, tool_error("A person declined this action."))
        try:
            output = spec.handler(args)
        except (KeyError, ValueError) as exc:
            return self._receipt(name, args, tool_error(str(exc)))
        return self._receipt(
            name, args, output if isinstance(output, dict) and "is_error" in output else tool_result(output)
        )

    def _receipt(self, name: str, args: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
        self.receipts.append(
            {"tool": name, "arguments": args, "is_error": value["is_error"], "message": value["message"]}
        )
        return value


def _obj(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def case_tools(
    store: CaseStore, case_id: str, *, as_of: date | None = None, approver: Approver | None = None
) -> ToolRegistry:
    """The tools an agent gets for one case. Scoped: it cannot see or touch other cases."""
    registry = ToolRegistry(approver)
    today = as_of or date.today()

    def load():
        case = store.get(case_id)
        if case is None:
            raise KeyError("case not found")
        return case

    def case_read(_args: dict[str, Any]) -> Any:
        return diary.case_detail(store, case_id, today, lens="advocate")

    def order_text(args: dict[str, Any]) -> Any:
        on = date.fromisoformat(str(args["on"]))
        for order in load().orders:
            if order.on == on:
                return {"on": order.on.isoformat(), "title": order.title, "uri": order.source.uri, "text": order.text}
        raise KeyError(f"no order dated {on.isoformat()}")

    def propose_obligations(args: dict[str, Any]) -> Any:
        """Obligations the agent read, anchored to the order's own words.

        A proposal whose quote is not found verbatim in the order is refused: an agent
        may interpret an order, it may not invent one.
        """
        case = load()
        on = date.fromisoformat(str(args["order_on"]))
        order = next((o for o in case.orders if o.on == on), None)
        if order is None:
            raise KeyError(f"no order dated {on.isoformat()}")
        accepted, refused = [], []
        for item in args.get("obligations") or []:
            quote = str(item.get("quote") or "").strip()
            start = order.text.find(quote) if quote else -1
            if start < 0:
                refused.append({"what": item.get("what"), "reason": "quote not found verbatim in the order"})
                continue
            due = date.fromisoformat(item["due"]) if item.get("due") else None
            obligation = Obligation(
                id=new_id("obl"),
                who=str(item.get("who") or "Unspecified")[:160],
                what=str(item.get("what") or quote)[:1000],
                due=due,
                source=order.source.model_copy(
                    update={
                        "span_start": start,
                        "span_end": start + len(quote),
                        "quote": quote[:400],
                        "verification": "lead",
                    }
                ),
            )
            duplicate = any(
                o.source.quote == obligation.source.quote and o.source.uri == order.source.uri for o in case.obligations
            )
            if duplicate:
                refused.append({"what": obligation.what, "reason": "already in the diary"})
                continue
            case.obligations.append(obligation)
            accepted.append(obligation.id)
        store.put(case)
        return {"accepted": accepted, "refused": refused}

    def liberty(_args: dict[str, Any]) -> Any:
        return judge.bail_facts(load(), today)

    def save_brief(args: dict[str, Any]) -> Any:
        load()
        brief = str(args["markdown"]).strip()
        if not brief:
            raise ValueError("empty brief")
        event = CaseEvent(
            id=new_id("evt"),
            case_id=case_id,
            kind="brief_prepared",
            summary="Hearing brief prepared.",
            after=brief[:20000],
        )
        store.append([event])
        return {"saved": event.id, "chars": len(brief)}

    registry.register(
        ToolSpec(
            "manu_case_read",
            "Read this case from the diary: parties, stage, next date, last order, open obligations, orders list, timeline, "
            "and for criminal cases the Section 479 and default-bail working. Call this first.",
            _obj({}, []),
            Tier.AUTO_READ,
            case_read,
        )
    )
    registry.register(
        ToolSpec(
            "manu_order_text",
            "Read the full text of one order in this case by its date (YYYY-MM-DD).",
            _obj({"on": {"type": "string", "description": "Order date, YYYY-MM-DD"}}, ["on"]),
            Tier.AUTO_READ,
            order_text,
        )
    )
    registry.register(
        ToolSpec(
            "manu_obligations_propose",
            "Propose obligations an order imposes. Each needs who, what, optional due (YYYY-MM-DD) and `quote`: the exact words "
            "from the order, copied verbatim. Proposals without a verbatim quote are refused. A person confirms each one.",
            _obj(
                {
                    "order_on": {"type": "string"},
                    "obligations": {
                        "type": "array",
                        "items": _obj(
                            {
                                "who": {"type": "string"},
                                "what": {"type": "string"},
                                "due": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                            ["who", "what", "quote"],
                        ),
                    },
                },
                ["order_on", "obligations"],
            ),
            Tier.AUTO_ACTION,
            propose_obligations,
        )
    )
    registry.register(
        ToolSpec(
            "manu_bail_facts",
            "Read the bail facts for this case (criminal only): offence profile, custody and statutory thresholds, antecedents, "
            "case status, prosecution position — with sources and gaps. Facts only; never a recommendation.",
            _obj({}, []),
            Tier.AUTO_READ,
            liberty,
        )
    )
    registry.register(
        ToolSpec(
            "manu_brief_save",
            "Save the hearing brief for this case as markdown. Every fact in it must name its source (order date, page).",
            _obj({"markdown": {"type": "string"}}, ["markdown"]),
            Tier.AUTO_ACTION,
            save_brief,
        )
    )
    return registry
