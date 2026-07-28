"""Unit tests for client-level helper functions."""

import pytest

from voltarium.client import VoltariumClient, _split_date_range, _split_month_range


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


def test_split_date_range_same_day():
    assert _split_date_range("2024-03-15", "2024-03-15") == [("2024-03-15", "2024-03-15")]


def test_split_date_range_within_12_months():
    result = _split_date_range("2024-01-15", "2024-12-15")
    assert result == [("2024-01-15", "2024-12-15")]


def test_split_date_range_over_12_months_splits():
    result = _split_date_range("2024-01-15", "2025-06-15")
    # Every window must span at most 12 months
    for start, end in result:
        sy, sm, sd = map(int, start.split("-"))
        ey, em, ed = map(int, end.split("-"))
        assert (ey - sy) * 12 + (em - sm) <= 12

    # Must cover the full range with no gaps/overlaps
    assert result[0][0] == "2024-01-15"
    assert result[-1][1] == "2025-06-15"
    for i in range(len(result) - 1):
        _, window_end = result[i]
        next_start, _ = result[i + 1]
        from datetime import date, timedelta

        ey, em, ed = map(int, window_end.split("-"))
        sy, sm, sd = map(int, next_start.split("-"))
        assert date(sy, sm, sd) == date(ey, em, ed) + timedelta(days=1)


def test_split_date_range_leap_day_clamping():
    # Adding 12 months from a leap day should clamp to Feb 28 on a non-leap year, not error.
    result = _split_date_range("2024-02-29", "2024-02-29")
    assert result == [("2024-02-29", "2024-02-29")]


def test_split_date_range_inverted_raises():
    with pytest.raises(ValueError, match="initial_date"):
        _split_date_range("2024-06-01", "2024-01-01")


def test_split_date_range_invalid_max_months_raises():
    with pytest.raises(ValueError, match="max_months"):
        _split_date_range("2024-01-01", "2024-12-31", max_months=0)


async def test_list_change_requests_requires_exactly_one_range_pair():
    # list_change_requests is an async generator: the validation only runs once the
    # generator is actually iterated, not at call time.
    client = VoltariumClient(client_id="id", client_secret="secret")

    generator = client.list_change_requests(
        agent_code="1",
        profile_code="1",
        request_status="CRIADA",
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
    )
    with pytest.raises(ValueError, match="exactly one of"):
        await generator.__anext__()


async def test_list_change_requests_rejects_both_range_pairs():
    client = VoltariumClient(client_id="id", client_secret="secret")

    generator = client.list_change_requests(
        agent_code="1",
        profile_code="1",
        request_status="CRIADA",
        request_type="SUSPENSAO_FORNECIMENTO_RESILICAO",
        initial_reference_month="2024-01",
        final_reference_month="2024-12",
        initial_request_date="2024-01-01",
        final_request_date="2024-12-31",
    )
    with pytest.raises(ValueError, match="exactly one of"):
        await generator.__anext__()
