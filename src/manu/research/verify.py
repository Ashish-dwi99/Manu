"""Check the citations in a piece of text before it goes to court.

Each citation is found by the published grammars (`doc_intel.grammars`), then looked up in
every connected source. The verdict says how far it got:

* `verified`  — an official or licensed copy carries this citation.
* `lead`      — only a lead source (e.g. Indian Kanoon) has it; confirm from an official copy.
* `demo`      — found in the fictional demo library. Not law.
* `not_found` — no connected source knows it. Not proof it is wrong; proof it is unchecked.
"""

from __future__ import annotations

import re

from manu.doc_intel import grammars
from manu.research.sources import STANDING_RANK, ResearchLadder


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def check_citations(text: str, ladder: ResearchLadder) -> dict:
    results = []
    attempts_seen: dict[str, str] = {}
    for match in grammars.find_citations(text):
        hits, attempts = ladder.search(match.value, limit=5)
        for a in attempts:
            attempts_seen[a.source] = a.outcome
        exact = [h for h in hits if any(_norm(c) == _norm(match.value) for c in h.citations)]
        # A lead source may not return the citation string itself; its top hit for an exact
        # citation query is still only a lead.
        candidates = exact or [h for h in hits if h.standing == "lead"]
        best = min(candidates, key=lambda h: STANDING_RANK[h.standing]) if candidates else None
        if best is None:
            status = "not_found"
        elif best.standing in ("official", "licensed") and exact:
            status = "verified"
        elif best.standing == "demo":
            status = "demo"
        else:
            status = "lead"
        results.append(
            {
                "citation": match.value,
                "start": match.start,
                "end": match.end,
                "status": status,
                "match": best.as_dict() if best else None,
            }
        )
    return {"citations": results, "searched": [{"source": k, "outcome": v} for k, v in attempts_seen.items()]}
