"""The connectors Manu ships with.

`FixtureConnector` reads JSON court records from a directory. It powers the demo, the
tests, and — pointed at a folder a clerk keeps — the human tier.

`ECourtsOpenApiConnector` is the tier-1 slot. eCourts exposes an Open API to onboarded
institutional litigants; access is granted per institution, so this connector reports
itself unavailable until `MANU_ECOURTS_API_BASE` and `MANU_ECOURTS_API_TOKEN` are set.
It does not scrape.

`BrowserPortalConnector` is the tier-3 slot. It will run a Kimi turn with the page tool
against the public portal (services.ecourts.gov.in); captchas and consent screens go to
a human through the runtime's approval path. Until that agent spec ships it reports
itself unavailable, so the ladder falls through honestly.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from manu.connectors.base import ConnectorUnavailable, CourtRecord, Tier


class FixtureConnector:
    name = "fixture"

    def __init__(self, root: str | Path, *, tier: Tier = Tier.OFFICIAL_PUBLIC_DATA) -> None:
        self.root = Path(root)
        self.tier = tier

    def fetch(self, cnr: str) -> CourtRecord | None:
        path = self.root / f"{cnr}.json"
        if not path.is_file():
            return None
        try:
            return CourtRecord.model_validate(json.loads(path.read_text()))
        except (OSError, ValueError) as exc:
            raise ConnectorUnavailable(f"fixture {path.name} unreadable: {exc}") from exc


_RELATIVE = re.compile(r"^@([+-]\d+)$")
_INLINE = re.compile(r"\{@([+-]\d+)\}")


def _resolve_relative(value: Any, today: date) -> Any:
    if isinstance(value, str):
        match = _RELATIVE.match(value)
        if match:
            return (today + timedelta(days=int(match.group(1)))).isoformat()
        # Inside prose (an order's text) a date is written the way courts write it.
        return _INLINE.sub(lambda m: (today + timedelta(days=int(m.group(1)))).strftime("%d.%m.%Y"), value)
    if isinstance(value, list):
        return [_resolve_relative(v, today) for v in value]
    if isinstance(value, dict):
        return {k: _resolve_relative(v, today) for k, v in value.items()}
    return value


class DemoConnector(FixtureConnector):
    """Fixtures whose dates are written relative to today ("@-14", "@+3"), so the demo
    diary is always current. Demo only; never registered outside `manu demo`."""

    name = "demo"

    def __init__(self, root: str | Path, *, today: date | None = None) -> None:
        super().__init__(root)
        self.today = today or date.today()

    def fetch(self, cnr: str) -> CourtRecord | None:
        path = self.root / f"{cnr}.json"
        if not path.is_file():
            return None
        return CourtRecord.model_validate(_resolve_relative(json.loads(path.read_text()), self.today))


class ECourtsOpenApiConnector:
    name = "ecourts_api"
    tier = Tier.OFFICIAL_API

    def __init__(self) -> None:
        self.base = os.getenv("MANU_ECOURTS_API_BASE", "").rstrip("/")
        self.token = os.getenv("MANU_ECOURTS_API_TOKEN", "")

    def fetch(self, cnr: str) -> CourtRecord | None:
        if not (self.base and self.token):
            raise ConnectorUnavailable("eCourts Open API not configured for this installation")
        raise ConnectorUnavailable("eCourts Open API client not implemented yet")


class BrowserPortalConnector:
    name = "ecourts_portal_browser"
    tier = Tier.BROWSER

    def fetch(self, cnr: str) -> CourtRecord | None:
        raise ConnectorUnavailable("portal browser agent not enabled")
