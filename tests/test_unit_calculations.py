"""
tests/test_unit_calculations.py
================================
Test IDs 11 (progress calculation) - pure functions, no FastAPI/network
needed, so these also double as a fast sanity check while developing.
"""
from datetime import date

from backend.services.goal_service import progress_percent
from backend.services.practice_service import compute_streaks


def test_progress_percent_normal():
    assert progress_percent(18, 30) == 60.0


def test_progress_percent_caps_at_100():
    assert progress_percent(45, 30) == 100.0


def test_progress_percent_zero_target_is_safe():
    assert progress_percent(5, 0) == 0.0


def test_streak_counts_consecutive_days_ending_today():
    today = date(2026, 9, 29)
    dates = ["2026-09-27", "2026-09-28", "2026-09-29"]
    result = compute_streaks(dates, today=today)
    assert result["current_streak"] == 3
    assert result["longest_streak"] == 3


def test_streak_continues_if_yesterday_logged_but_not_today():
    today = date(2026, 9, 29)
    dates = ["2026-09-26", "2026-09-27", "2026-09-28"]
    result = compute_streaks(dates, today=today)
    assert result["current_streak"] == 3


def test_streak_resets_after_a_gap():
    today = date(2026, 9, 29)
    dates = ["2026-09-20"]  # 9 days ago -> broken
    result = compute_streaks(dates, today=today)
    assert result["current_streak"] == 0
    assert result["longest_streak"] == 1


def test_longest_streak_survives_a_later_break():
    today = date(2026, 9, 29)
    # A 4-day streak two weeks ago, then a fresh 1-day streak today.
    dates = ["2026-09-10", "2026-09-11", "2026-09-12", "2026-09-13", "2026-09-29"]
    result = compute_streaks(dates, today=today)
    assert result["current_streak"] == 1
    assert result["longest_streak"] == 4
