"""Persistent Sina minute snapshots with shared cooldown, tail updates and backoff."""
import json
import math
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from DataAPI.SinaAPI import SINA_KLINE_URL, parse_sina_jsonp
from .providers.errors import SourceDataError, SourceTimeoutError
from .providers.registry import source_lock

SHANGHAI = ZoneInfo('Asia/Shanghai')


@dataclass
class QuoteSnapshot:
    rows: list[dict]
    fetched_at: datetime
    stale: bool = False
    warning: str = ''


class SinaLiveQuotes:
    def __init__(self, path: Path, http_get=requests.get,
                 now=lambda: datetime.now(SHANGHAI), min_interval: float = 2):
        self.path = Path(path)
        self.http_get = http_get
        self.now = now
        self.min_interval = min_interval
        self._last_call = 0.0

    def _fetch(self, instrument, period, count):
        time.sleep(max(0, self.min_interval - (time.monotonic() - self._last_call)))
        self._last_call = time.monotonic()
        try:
            response = self.http_get(url=SINA_KLINE_URL,
                params={'symbol': instrument.replace('.', ''), 'scale': period[:-1], 'ma': 'no', 'datalen': str(count)},
                timeout=15)
            response.raise_for_status()
            rows = parse_sina_jsonp(response.text)
            if not rows:
                raise SourceDataError('新浪未返回近期行情')
            return rows
        except requests.Timeout as exc:
            raise SourceTimeoutError('新浪盘中行情请求超时') from exc
        except requests.RequestException as exc:
            raise SourceDataError('新浪盘中行情暂时不可用') from exc

    def get(self, instrument: str, period: str) -> QuoteSnapshot:
        if period not in {'5m', '30m'}:
            raise ValueError('Live snapshots support 5m and 30m only')
        # Held through fetch: simultaneous panels/readers share one refresh, including failed attempts.
        with source_lock('sina-live'):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path, timeout=30) as db:
                db.execute('CREATE TABLE IF NOT EXISTS live_snapshots ('
                           'instrument TEXT, period TEXT, rows_json TEXT, fetched_at REAL, '
                           'failures INTEGER, retry_after REAL, warning TEXT, PRIMARY KEY(instrument,period))')
                record = db.execute('SELECT rows_json,fetched_at,failures,retry_after,warning FROM live_snapshots '
                                    'WHERE instrument=? AND period=?', (instrument, period)).fetchone()
            now = self.now()
            old, fetched, failures, retry_after, warning = (json.loads(record[0]), *record[1:]) if record else ([], 0, 0, 0, '')
            active = now.weekday() < 5 and ('09:30' <= now.strftime('%H:%M') <= '11:30' or '13:00' <= now.strftime('%H:%M') <= '15:00')
            ttl = 30 if active else 3600
            crossed_close = now.weekday() < 5 and any(
                fetched < now.replace(hour=hour, minute=minute, second=0, microsecond=0).timestamp() <= now.timestamp()
                for hour, minute in [(11,30), (15,0)])
            if now.timestamp() < retry_after:
                if old:
                    return QuoteSnapshot(old, datetime.fromtimestamp(fetched, SHANGHAI), True, warning)
                raise SourceDataError('盘中行情正在退避，请稍后重试')
            if old and now.timestamp() - fetched < ttl and not crossed_close:
                return QuoteSnapshot(old, datetime.fromtimestamp(fetched, SHANGHAI), False, warning)
            count = min(1970, max(32, math.ceil((now.timestamp() - fetched) / (int(period[:-1]) * 60)) + 2)) if old else 1970
            try:
                rows = self._fetch(instrument, period, count)
                warning = ''
                if old and not ({r['day'] for r in rows} & {r['day'] for r in old}):
                    if count < 1970:
                        rows = self._fetch(instrument, period, 1970)
                    if not ({r['day'] for r in rows} & {r['day'] for r in old}):
                        old = []
                        warning = '近期行情与旧缓存不连续，已重新获取可用窗口'
                merged = {r['day']: r for r in old}
                merged.update({r['day']: r for r in rows})
                # Keep previously observed history while replacing the mutable tail.
                values = [merged[key] for key in sorted(merged)]
                fetched = self.now().timestamp()
                self._save(instrument, period, values, fetched, 0, 0, warning)
                return QuoteSnapshot(values, datetime.fromtimestamp(fetched, SHANGHAI), False, warning)
            except (SourceDataError, SourceTimeoutError) as exc:
                failures += 1
                warning = '盘中更新失败，当前显示上次成功获取的数据'
                self._save(instrument, period, old, fetched, failures,
                           self.now().timestamp() + min(900, 60 * 2 ** min(failures - 1, 4)), warning)
                if old:
                    return QuoteSnapshot(old, datetime.fromtimestamp(fetched, SHANGHAI), True, warning)
                raise exc

    def _save(self, instrument, period, rows, fetched, failures, retry_after, warning):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute('INSERT OR REPLACE INTO live_snapshots VALUES (?,?,?,?,?,?,?)',
                       (instrument, period, json.dumps(rows), fetched, failures, retry_after, warning))
