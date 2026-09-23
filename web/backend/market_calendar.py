"""Check whether a requested chart omitted an earlier tradable bar period."""
from datetime import date, timedelta
from collections.abc import Iterable

from .providers.errors import SourceDataError, DateRangeUnavailableError


def _bucket(day: date, period: str):
    if period == '1mo':
        return (day.year, day.month)
    if period == '1w':
        iso = day.isocalendar()
        return (iso.year, iso.week)
    return day


def load_trading_days(begin: date, end: date) -> list[date]:
    """Use the exchange trading calendar, not weekday guesses around holidays."""
    import baostock as bs
    from DataAPI.BaoStockAPI import CBaoStock

    if end < begin:
        return []
    try:
        CBaoStock.do_init()
        result = []
        seen = 0
        query = bs.query_trade_dates(start_date=begin.isoformat(), end_date=end.isoformat())
        if query.error_code != '0':
            raise SourceDataError('交易日历读取失败')
        while query.next():
            seen += 1
            day, flag = query.get_row_data()
            if flag == '1':
                result.append(date.fromisoformat(day))
        if seen == 0:
            raise DateRangeUnavailableError('请求开始日期超出交易日历可用范围')
        return result
    except (SourceDataError, DateRangeUnavailableError):
        raise
    except Exception as exc:
        raise SourceDataError('交易日历读取失败') from exc
    finally:
        CBaoStock.do_close()


def has_missing_trading_period(begin: date, first_bar: date, period: str,
                               trading_days: Iterable[date] | None = None) -> bool:
    if first_bar <= begin or _bucket(begin, period) == _bucket(first_bar, period):
        return False
    days = trading_days if trading_days is not None else load_trading_days(begin, first_bar - timedelta(days=1))
    return any(begin <= day < first_bar and _bucket(day, period) != _bucket(first_bar, period) for day in days)
