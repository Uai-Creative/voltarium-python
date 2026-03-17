"""Unit tests for client-level helper functions."""

import pytest

from voltarium.client import _split_month_range


def test_same_month():
    assert _split_month_range("2024-03", "2024-03") == [("2024-03", "2024-03")]


def test_within_12_months():
    result = _split_month_range("2024-01", "2024-12")
    assert result == [("2024-01", "2024-12")]


def test_exactly_13_months_splits_into_two():
    result = _split_month_range("2024-01", "2025-01")
    assert result == [("2024-01", "2024-12"), ("2025-01", "2025-01")]


def test_multi_year_range():
    result = _split_month_range("2020-01", "2026-03")
    # Every window must be at most 12 months
    for start, end in result:
        sy, sm = map(int, start.split("-"))
        ey, em = map(int, end.split("-"))
        assert (ey - sy) * 12 + (em - sm) < 12

    # Must cover the full range with no gaps
    assert result[0][0] == "2020-01"
    assert result[-1][1] == "2026-03"

    for i in range(len(result) - 1):
        _, window_end = result[i]
        next_start, _ = result[i + 1]
        ey, em = map(int, window_end.split("-"))
        sy, sm = map(int, next_start.split("-"))
        # next window starts exactly the month after current window ends
        expected_next = (ey + 1, 1) if em == 12 else (ey, em + 1)
        assert (sy, sm) == expected_next


def test_year_boundary():
    result = _split_month_range("2023-07", "2024-06")
    assert result == [("2023-07", "2024-06")]


def test_year_boundary_exceeds_12():
    result = _split_month_range("2023-07", "2024-07")
    assert result == [("2023-07", "2024-06"), ("2024-07", "2024-07")]


def test_inverted_range_raises():
    with pytest.raises(ValueError, match="initial_month"):
        _split_month_range("2024-06", "2024-01")


def test_invalid_max_months_raises():
    with pytest.raises(ValueError, match="max_months"):
        _split_month_range("2024-01", "2024-12", max_months=0)
