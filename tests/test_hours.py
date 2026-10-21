"""Declared opening is evaluated at Tehran arrival, never equated with live availability."""

from datetime import datetime
import pytest


def shift(start, end):
    return {"status": "declared", "shifts": [{"start_time": start, "end_time": end}]}


@pytest.mark.parametrize(
    "hours,at,want",
    [
        ({"thu": shift("10:00:00", "21:00:00")}, "2026-10-22T20:15:00+03:30", "open"),
        ({"thu": shift("10:00:00", "21:00:00")}, "2026-10-22T21:00:00+03:30", "closed"),
        ({"thu": shift("10:00", "21:00")}, "2026-10-22T06:30:00+00:00", "open"),
        ({"wed": shift("22:00", "02:00")}, "2026-10-22T01:00:00+03:30", "open"),
        (
            {"wed": shift("22:00", "02:00"), "thu": {"status": "closed", "shifts": []}},
            "2026-10-22T02:00:00+03:30",
            "closed",
        ),
        ({"thu": {"status": "closed", "shifts": []}}, "2026-10-22T12:00:00+03:30", "closed"),
        ({"thu": {"status": "unsupported", "shifts": []}}, "2026-10-22T12:00:00+03:30", "unknown"),
        ({"thu": shift("00:00", "00:00")}, "2026-10-22T12:00:00+03:30", "unknown"),
        (None, "2026-10-22T12:00:00+03:30", "unknown"),
        ({}, "2026-10-22T12:00:00+03:30", "unknown"),
        ({"thu": shift("bad", "25:00")}, "2026-10-22T12:00:00+03:30", "unknown"),
    ],
)
def test_declared_hours(hours, at, want):
    from torob.hours import hours_state

    assert hours_state(hours, datetime.fromisoformat(at)) == want


def test_dummy_interval_does_not_erase_valid_shift():
    from torob.hours import hours_state

    hours = {
        "thu": {
            "status": "declared",
            "shifts": [
                {"start_time": "00:00", "end_time": "00:00"},
                {"start_time": "10:00", "end_time": "21:00"},
            ],
        }
    }
    assert hours_state(hours, datetime.fromisoformat("2026-10-22T20:00:00+03:30")) == "open"


def test_naive_datetime_rejected():
    from torob.hours import hours_state

    with pytest.raises(ValueError):
        hours_state({}, datetime(2026, 10, 22, 20))
