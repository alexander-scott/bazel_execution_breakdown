import datetime
import json
from pathlib import Path

import pytest


@pytest.fixture
def build_start_time() -> datetime.datetime:
    return datetime.datetime(2026, 2, 9, 17, 7, 35)


@pytest.fixture
def profiles_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "profiles"


def make_event_str(cat: str, name: str, ts: int, dur: int, **kwargs: object) -> str:
    """Return a clean JSON event string (no trailing comma/newline) suitable for use in event_groups."""
    event: dict[str, object] = {"cat": cat, "name": name, "ph": "X", "ts": ts, "dur": dur, "pid": 1}
    event.update(kwargs)
    return json.dumps(event)


def make_raw_event(cat: str, name: str, ts: int, dur: int, tid: int, **kwargs: object) -> str:
    """Return a raw event string (with leading spaces and trailing comma+newline) as it appears in profile files.

    Uses compact JSON separators so that the field regexes (e.g. ``ts\":(\\d+)``) used by the
    profile parser match without any intervening whitespace.
    """
    event: dict[str, object] = {"cat": cat, "name": name, "ph": "X", "ts": ts, "dur": dur, "pid": 1, "tid": tid}
    event.update(kwargs)
    return f"    {json.dumps(event, separators=(',', ':'))},\n"
