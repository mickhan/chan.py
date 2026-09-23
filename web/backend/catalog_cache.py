"""SQLite-backed instrument directory with non-blocking stale refresh."""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import nullcontext
from pathlib import Path
from threading import Lock, Thread
from typing import Callable

from .kline_cache import DEFAULT_CACHE_PATH
from .schemas import InstrumentOption

_log = logging.getLogger(__name__)
_CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS instrument_catalog (
    source TEXT PRIMARY KEY,
    updated_at REAL NOT NULL,
    items_json TEXT NOT NULL
)
"""


class CatalogCache:
    def __init__(self, path: Path = DEFAULT_CACHE_PATH,
                 now: Callable[[], float] = time.time,
                 ttl_seconds: float = 86400, retry_seconds: float = 3600):
        self.path = Path(path)
        self.now = now
        self.ttl_seconds = ttl_seconds
        self.retry_seconds = retry_seconds
        self._lock = Lock()
        self._memory: dict[str, tuple[float, list[InstrumentOption]]] = {}
        self._last_attempt: dict[str, float] = {}
        self._refreshing: set[str] = set()

    def get(self, source: str, loader: Callable[[], list[InstrumentOption]],
            guard: Callable = nullcontext) -> list[InstrumentOption]:
        with self._lock:
            cached = self._memory.get(source)
            if cached is None:
                cached = self._read(source)
                if cached is not None:
                    self._memory[source] = cached
            if cached is not None:
                updated_at, rows = cached
                current = self.now()
                if (current - updated_at >= self.ttl_seconds and source not in self._refreshing
                        and current - self._last_attempt.get(source, float('-inf')) >= self.retry_seconds):
                    self._last_attempt[source] = current
                    self._refreshing.add(source)
                    Thread(target=self._refresh, args=(source, loader, guard), daemon=True).start()
                return rows

        rows = loader()
        if not rows:
            raise ValueError(f'{source} returned an empty instrument catalog')
        current = self.now()
        self._save(source, rows, current)
        with self._lock:
            self._memory[source] = (current, rows)
        return rows

    def _refresh(self, source: str, loader: Callable[[], list[InstrumentOption]],
                 guard: Callable) -> None:
        try:
            with guard():
                rows = loader()
                if not rows:
                    raise ValueError(f'{source} returned an empty instrument catalog')
                current = self.now()
                self._save(source, rows, current)
                with self._lock:
                    self._memory[source] = (current, rows)
        except Exception:
            _log.exception('Instrument catalog refresh failed for %s; keeping cached data', source)
        finally:
            with self._lock:
                self._refreshing.discard(source)

    def _read(self, source: str) -> tuple[float, list[InstrumentOption]] | None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute(_CATALOG_SCHEMA)
            result = db.execute('SELECT updated_at, items_json FROM instrument_catalog WHERE source=?',
                                (source,)).fetchone()
        if result is None:
            return None
        try:
            rows = [InstrumentOption.model_validate(item) for item in json.loads(result[1])]
        except (ValueError, TypeError):
            _log.warning('Invalid cached instrument catalog for %s; fetching again', source)
            return None
        return (result[0], rows) if rows else None

    def _save(self, source: str, rows: list[InstrumentOption], updated_at: float) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([item.model_dump() for item in rows], ensure_ascii=False)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute(_CATALOG_SCHEMA)
            db.execute('INSERT OR REPLACE INTO instrument_catalog VALUES (?, ?, ?)',
                       (source, updated_at, payload))
