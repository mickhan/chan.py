from datetime import date
from web.backend.market_calendar import has_missing_trading_period


def test_market_calendar_distinguishes_closure_and_missing_daily_history():
    days = [date(2024, 1, 2), date(2024, 1, 3)]
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 1, 2), '1d', days) is False
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 1, 4), '1d', days) is True


def test_market_calendar_groups_weekly_and_monthly_bars():
    days = [date(2024, 1, 2), date(2024, 1, 8)]
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 1, 5), '1w', days) is False
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 1, 12), '1w', days) is True
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 1, 31), '1mo', days) is False
    assert has_missing_trading_period(date(2024, 1, 1), date(2024, 2, 29), '1mo', days) is True
