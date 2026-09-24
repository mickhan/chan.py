"""Persistent local K-line cache with date-range coverage tracking."""
from __future__ import annotations

import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

from Common.CEnum import DATA_FIELD, TRADE_INFO_LST
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit

from .schemas import AnalysisRequest


DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[2] / 'data' / 'market.sqlite3'
_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
  source TEXT NOT NULL, instrument TEXT NOT NULL, period TEXT NOT NULL,
  adjustment TEXT NOT NULL, time TEXT NOT NULL, auto INTEGER NOT NULL,
  open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
  close REAL NOT NULL, volume REAL, turnover REAL, turnover_rate REAL,
  PRIMARY KEY (source, instrument, period, adjustment, time)
);
CREATE TABLE IF NOT EXISTS coverage (
  source TEXT NOT NULL, instrument TEXT NOT NULL, period TEXT NOT NULL,
  adjustment TEXT NOT NULL, begin_date TEXT NOT NULL, end_date TEXT NOT NULL,
  fetched_at REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (source, instrument, period, adjustment, begin_date, end_date)
);
"""


class KlineCache:
    def __init__(self, path: Path = DEFAULT_CACHE_PATH,
                 today: Callable[[], date] = lambda: datetime.now(ZoneInfo('Asia/Shanghai')).date(),
                 now: Callable[[], float] = time.time, refresh_seconds: float = 6 * 3600):
        self.path = Path(path)
        self.today = today
        self.now = now
        self.refresh_seconds = refresh_seconds

    def get(self, source: str, request: AnalysisRequest, max_bars: int,
            fetch: Callable[[AnalysisRequest, int], list[CKLine_Unit]]) -> list[CKLine_Unit]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        key = (source, request.instrument, request.period, request.adjustment)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.executescript(_SCHEMA)
            if 'fetched_at' not in {row[1] for row in db.execute('PRAGMA table_info(coverage)')}:
                db.execute('ALTER TABLE coverage ADD COLUMN fetched_at REAL NOT NULL DEFAULT 0')
            today = self.today()
            coverage = list(db.execute(
                'SELECT begin_date, end_date, fetched_at FROM coverage WHERE source=? AND instrument=? '
                'AND period=? AND adjustment=? ORDER BY begin_date', key))
            intervals = [
                (date.fromisoformat(begin), date.fromisoformat(end))
                for begin, end, _ in coverage
            ]
            missing = self._missing(request.begin_time, request.end_time, intervals)
            if missing:
                # Revisit the trailing few dates when extending the cached range.
                last_begin, last_end = missing[-1]
                if last_begin > request.begin_time and any(end < last_begin for _, end in intervals):
                    missing[-1] = (max(request.begin_time, last_begin - timedelta(days=2)), last_end)
            elif request.end_time >= today - timedelta(days=2):
                # Recent historical bars need low-frequency calibration, not a download on every click.
                fresh = [(date.fromisoformat(begin), date.fromisoformat(end)) for begin, end, fetched in coverage
                         if self.now() - fetched < self.refresh_seconds]
                missing = self._missing(max(request.begin_time, today - timedelta(days=2)), request.end_time, fresh)

            for begin, end in missing:
                part = request.model_copy(update={'begin_time': begin, 'end_time': end})
                rows = fetch(part, max_bars)
                if len(rows) > max_bars:
                    return rows
                self._save(db, key, begin, end, rows, today, self.now())

            return self._read_rows(db, key, request)

    def read(self, source: str, request: AnalysisRequest) -> list[CKLine_Unit]:
        """Read accumulated closed history without refreshing it from the network."""
        if not self.path.exists():
            return []
        with sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=30) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='candles'").fetchone():
                return []
            return self._read_rows(db, (source, request.instrument, request.period, request.adjustment), request)

    @staticmethod
    def _read_rows(db, key, request):
        result = []
        for row in db.execute(
            'SELECT time, auto, open, high, low, close, volume, turnover, turnover_rate '
            'FROM candles WHERE source=? AND instrument=? AND period=? AND adjustment=? '
            'AND substr(time, 1, 10) BETWEEN ? AND ? ORDER BY time',
            (*key, request.begin_time.isoformat(), request.end_time.isoformat()),
        ):
            when = datetime.fromisoformat(row[0])
            fields = {
                DATA_FIELD.FIELD_TIME: CTime(when.year, when.month, when.day,
                                             when.hour, when.minute, when.second,
                                             auto=bool(row[1])),
                DATA_FIELD.FIELD_OPEN: row[2], DATA_FIELD.FIELD_HIGH: row[3],
                DATA_FIELD.FIELD_LOW: row[4], DATA_FIELD.FIELD_CLOSE: row[5],
            }
            fields.update(zip(TRADE_INFO_LST, row[6:]))
            result.append(CKLine_Unit(fields))
        return result

    @staticmethod
    def _missing(begin: date, end: date, intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
        missing = []
        cursor = begin
        for covered_begin, covered_end in intervals:
            if covered_end < cursor:
                continue
            if covered_begin > end:
                break
            if covered_begin > cursor:
                missing.append((cursor, min(end, covered_begin - timedelta(days=1))))
            cursor = max(cursor, covered_end + timedelta(days=1))
            if cursor > end:
                break
        if cursor <= end:
            missing.append((cursor, end))
        return missing

    @staticmethod
    def _save(db: sqlite3.Connection, key: tuple[str, str, str, str],
              begin: date, end: date, rows: list[CKLine_Unit], today: date, fetched_at: float) -> None:
        db.execute(
            'DELETE FROM candles WHERE source=? AND instrument=? AND period=? AND adjustment=? '
            'AND substr(time, 1, 10) BETWEEN ? AND ?',
            (*key, begin.isoformat(), end.isoformat()),
        )
        for item in rows:
            t = item.time
            timestamp = datetime(t.year, t.month, t.day, t.hour, t.minute, t.second).isoformat()
            metrics = item.trade_info.metric
            db.execute(
                'INSERT OR REPLACE INTO candles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (*key, timestamp, int(t.auto), item.open, item.high, item.low, item.close,
                 *(metrics.get(field) for field in TRADE_INFO_LST)),
            )
        if begin <= today:
            db.execute('INSERT OR REPLACE INTO coverage (source,instrument,period,adjustment,begin_date,end_date,fetched_at) '
                       'VALUES (?, ?, ?, ?, ?, ?, ?)',
                       (*key, begin.isoformat(), min(end, today).isoformat(), fetched_at))
        db.commit()
