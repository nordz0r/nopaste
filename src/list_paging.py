"""Paginate paste lists by the last N populated calendar days."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

LIST_DAY_WINDOW = 7


def paste_calendar_day(created_at: Any) -> date | None:
    """Return the UTC calendar day for a paste timestamp, if it has one."""
    if isinstance(created_at, datetime):
        value = created_at
        if value.tzinfo is not None:
            value = value.astimezone(UTC)
        return value.date()
    if isinstance(created_at, date):
        return created_at
    return None


def paginate_pastes_by_day_window(
    pastes: list[dict[str, Any]],
    page: int,
    *,
    window_days: int = LIST_DAY_WINDOW,
) -> dict[str, Any]:
    """Split pastes into pages of up to ``window_days`` populated days.

    Empty calendar days do not count. Page 1 is the last N days that actually
    have pastes (newest first); the next older populated days go to page 2.
    """
    total_count = len(pastes)
    page = 1 if not isinstance(page, int) or page < 1 else page
    window_days = max(1, window_days)

    dated: list[tuple[date, int, dict[str, Any]]] = []
    undated: list[dict[str, Any]] = []
    for index, paste in enumerate(pastes):
        day = paste_calendar_day(paste.get("created_at"))
        if day is None:
            undated.append(paste)
        else:
            dated.append((day, index, paste))

    if not dated:
        groups = []
        if undated and page == 1:
            groups.append({"day": "", "pastes": undated})
        return {
            "groups": groups,
            "page": 1,
            "total_pages": 1 if groups else 0,
            "has_next": False,
            "has_prev": False,
            "total_count": total_count,
            "window_start": None,
            "window_end": None,
        }

    def _sort_stamp(item: dict[str, Any]) -> datetime:
        value = item.get("created_at")
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        return datetime.min.replace(tzinfo=UTC)

    by_day: dict[date, list[tuple[int, dict[str, Any]]]] = {}
    for day, index, paste in dated:
        by_day.setdefault(day, []).append((index, paste))

    populated_days = sorted(by_day.keys(), reverse=True)
    total_pages = max(1, (len(populated_days) + window_days - 1) // window_days)
    if page > total_pages:
        page = total_pages

    start = (page - 1) * window_days
    page_days = populated_days[start : start + window_days]

    groups: list[dict[str, Any]] = []
    for day in page_days:
        day_pastes = [
            paste
            for _index, paste in sorted(
                by_day[day],
                key=lambda item: (_sort_stamp(item[1]), -item[0]),
                reverse=True,
            )
        ]
        groups.append({"day": day.isoformat(), "pastes": day_pastes})

    if undated and page == 1:
        groups.append({"day": "", "pastes": undated})

    window_end = page_days[0].isoformat() if page_days else None
    window_start = page_days[-1].isoformat() if page_days else None

    return {
        "groups": groups,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "total_count": total_count,
        "window_start": window_start,
        "window_end": window_end,
    }
