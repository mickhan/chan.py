"""Combine stable historical bars with recent unadjusted snapshots."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
import time as clock

from Common.CEnum import DATA_FIELD
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from .instruments import instrument_kind
from .live_quotes import SHANGHAI
from .providers.errors import ProviderError, SourceDataError


def timestamp(bar):
    t = bar.time
    return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, tzinfo=SHANGHAI)


def unit(at, opening, high, low, close, volume):
    return CKLine_Unit({DATA_FIELD.FIELD_TIME: CTime(at.year, at.month, at.day, at.hour, at.minute, auto=False),
        DATA_FIELD.FIELD_OPEN: opening, DATA_FIELD.FIELD_HIGH: high, DATA_FIELD.FIELD_LOW: low,
        DATA_FIELD.FIELD_CLOSE: close, DATA_FIELD.FIELD_VOLUME: volume})


def aggregate(rows, at):
    return unit(at, rows[0].open, max(r.high for r in rows), min(r.low for r in rows), rows[-1].close,
                sum(r.trade_info.metric.get(DATA_FIELD.FIELD_VOLUME) or 0 for r in rows))


def merge_verified(history, recent):
    if not recent:
        return history
    original = {timestamp(r): r for r in history}
    incoming = {timestamp(r): r for r in recent}
    overlap = sorted(original.keys() & incoming.keys())[-32:]
    if history and not overlap:
        raise SourceDataError('历史与盘中数据没有重叠区间，无法校验拼接')
    for at in overlap:
        for field_name in ['open', 'high', 'low', 'close']:
            old = getattr(original[at], field_name)
            new = getattr(incoming[at], field_name)
            if abs(old - new) > max(.0011, abs(old) * .0001):
                raise SourceDataError('历史与盘中价格不一致，已停止拼接，请检查复权或数据源')
    # Historical closed bars are authoritative. Only append the newer live tail.
    last = max(original) if original else None
    original.update({at: row for at, row in incoming.items() if last is None or at > last})
    return [original[key] for key in sorted(original)]


@dataclass
class MarketData:
    rows: list
    source: str
    status: str = 'historical'
    fetched_at: datetime | None = None
    provisional: set[str] = field(default_factory=set)
    warnings: list[str] = field(default_factory=list)


class MarketDataService:
    def __init__(self, registry, cache, live, now=lambda: datetime.now(SHANGHAI), min_interval=2):
        self.registry, self.cache, self.live, self.now = registry, cache, live, now
        self.min_interval = min_interval
        self._history_calls = {}
        self._history_failures = {}

    def _fetch_history(self, request, provider, max_bars):
        key = (provider.source_id, request.instrument, request.period, request.adjustment)
        failure = self._history_failures.get(key)
        if failure and self.now().timestamp() < failure[1]:
            raise failure[2]
        clock.sleep(max(0, self.min_interval - (clock.monotonic() - self._history_calls.get(provider.source_id, 0))))
        self._history_calls[provider.source_id] = clock.monotonic()
        try:
            rows = provider.fetch_klines(request, max_bars)
            self._history_failures.pop(key, None)
            return rows
        except ProviderError as exc:
            count = failure[0] + 1 if failure else 1
            self._history_failures[key] = (count, self.now().timestamp() + min(900, 60 * 2 ** min(count - 1, 4)), exc)
            raise

    def _history(self, request, provider, max_bars):
        if request.begin_time > request.end_time:
            return []
        with self.registry.guard(provider):
            if self.cache is None:
                return self._fetch_history(request, provider, max_bars)
            return self.cache.get(provider.source_id, request, max_bars,
                                  lambda part, limit: self._fetch_history(part, provider, limit))

    def _daily(self, snapshot, now):
        grouped = defaultdict(list)
        for row in snapshot.rows:
            at = datetime.fromisoformat(row['day']).replace(tzinfo=SHANGHAI)
            if at > now + timedelta(minutes=30) or at.date() > now.date():
                continue
            grouped[at.date()].append(unit(at, row['open'], row['high'], row['low'], row['close'], row['volume']))
        slots = ['10:00', '10:30', '11:00', '11:30', '13:30', '14:00', '14:30', '15:00']
        result = []
        for day, rows in sorted(grouped.items()):
            seen = [timestamp(row).strftime('%H:%M') for row in rows]
            # Never aggregate a window starting mid-session or with missing bars.
            if seen != slots[:len(seen)] or (day < now.date() and len(seen) != 8):
                continue
            result.append(aggregate(rows, datetime.combine(day, time(), SHANGHAI)))
        return result

    def load(self, request, provider, max_bars):
        now = self.now()
        today = now.date()
        wants_live = request.end_time >= today and instrument_kind(request.instrument) in {'stock', 'etf', 'index'}
        if not wants_live or request.adjustment != 'none':
            rows = self._history(request, provider, max_bars)
            result = MarketData(rows, provider.source_id)
            if wants_live:
                result.status = 'delayed'
                result.warnings.append('当前复权方式使用历史行情；盘中更新仅支持不复权，避免混合价格口径')
            return result

        # A forming day/week must never be marked as covered in the historical cache.
        historical_end = today - timedelta(days=1)
        if request.period == '1w':
            historical_end = today - timedelta(days=today.weekday() + 1)
        history_request = request.model_copy(update={'end_time': historical_end})
        # Preserve previously accumulated index history beyond the current remote window.
        if provider.source_id == 'sina':
            history = self.cache.read('sina', history_request) if self.cache else []
        else:
            history = self._history(history_request, provider, max_bars)
        result = MarketData(history, provider.source_id)
        try:
            snapshot = self.live.get(request.instrument, request.period if request.period in {'5m','30m'} else '30m')
            result.fetched_at = snapshot.fetched_at
            as_of = min(now, snapshot.fetched_at)
            if snapshot.warning:
                result.warnings.append(snapshot.warning)
            if request.period in {'5m','30m'}:
                minutes = int(request.period[:-1])
                recent = []
                for row in snapshot.rows:
                    at = datetime.fromisoformat(row['day']).replace(tzinfo=SHANGHAI)
                    if at.date() > today or at > now + timedelta(minutes=minutes):
                        continue
                    recent.append(unit(at, row['open'], row['high'], row['low'], row['close'], row['volume']))
                merged = merge_verified(history, recent)
                provisional = {timestamp(r).isoformat() for r in merged if timestamp(r) > as_of}
            else:
                daily_recent = self._daily(snapshot, now)
                if request.period == '1d':
                    merged = merge_verified(history, daily_recent)
                else:
                    begin = timestamp(history[-1]).date() + timedelta(days=1) if history else request.begin_time - timedelta(days=request.begin_time.weekday())
                    daily_request = request.model_copy(update={'period':'1d', 'begin_time':begin, 'end_time':today-timedelta(days=1)})
                    daily_provider = self.registry.resolve(request.market, request.instrument, '1d', 'none')
                    daily_history = self._history(daily_request, daily_provider, max_bars)
                    daily = merge_verified(daily_history, daily_recent)
                    weeks = defaultdict(list)
                    for row in daily:
                        if timestamp(row).date() >= begin:
                            weeks[timestamp(row).date().isocalendar()[:2]].append(row)
                    merged = [*history, *(aggregate(rows, timestamp(rows[-1])) for _, rows in sorted(weeks.items()))]
                provisional = set()
                for row in merged:
                    day = timestamp(row).date()
                    if (request.period == '1d' and datetime.combine(day, time(15), SHANGHAI) > as_of) or (
                        request.period == '1w' and day.isocalendar()[:2] == today.isocalendar()[:2] and
                        datetime.combine(day + timedelta(days=4-day.weekday()), time(15), SHANGHAI) > as_of):
                        provisional.add(timestamp(row).isoformat())
            result.rows = [r for r in merged if request.begin_time <= timestamp(r).date() <= request.end_time]
            result.provisional = provisional
            result.source = f'{provider.source_id}+sina' if history and provider.source_id != 'sina' else 'sina'
            result.status = 'delayed' if snapshot.stale else 'live'
            if not any(timestamp(r).date() == today for r in result.rows):
                result.warnings.append('盘中源尚未返回今天的数据，请留意最后一根 K 线时间')
                result.status = 'delayed'
        except ProviderError as exc:
            if not history:
                raise
            result.status = 'delayed'
            result.warnings.append(exc.message)
        return result
