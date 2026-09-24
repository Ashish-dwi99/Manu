"""Indian courts keep Indian dates. "Today" is the date in India, whatever the server's clock."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

IST = timedelta(hours=5, minutes=30)


def india_today() -> date:
    return (datetime.now(UTC) + IST).date()
