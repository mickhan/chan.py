from __future__ import annotations

import re
from collections.abc import Iterable

from .schemas import InstrumentOption

_CANONICAL = re.compile(r"^(sh|sz|bj)\.[0-9]{6}$")


def instrument_kind(instrument: str) -> str:
    if not _CANONICAL.fullmatch(instrument):
        raise ValueError(f"无效的标的代码: {instrument}")
    if instrument.startswith("sh.000") or instrument.startswith("sz.399"):
        return "index"
    return "stock"


def normalize_baostock_record(row: tuple[str, ...] | list[str]) -> InstrumentOption:
    if len(row) < 6 or row[4] not in {"1", "2"}:
        raise ValueError("BaoStock catalog row is not a stock or index")
    code, name = row[0], row[1]
    if not _CANONICAL.fullmatch(code):
        raise ValueError(f"invalid BaoStock code: {code}")
    return InstrumentOption(
        market="cn", instrument=code, name=name, exchange=code.split(".")[0],
        kind="stock" if row[4] == "1" else "index",
    )


def normalize_akshare_record(row: dict[str, str]) -> InstrumentOption:
    code = str(row["code"])
    if not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError(f"invalid AkShare code: {code}")
    exchange = "sh" if code[0] in {"6", "9"} else "bj" if code[0] in {"4", "8"} else "sz"
    return InstrumentOption(
        market="cn", instrument=f"{exchange}.{code}", name=str(row["name"]),
        exchange=exchange, kind="stock",
    )


def filter_instruments(
    catalog: Iterable[InstrumentOption], query: str, limit: int,
) -> list[InstrumentOption]:
    term = query.strip().casefold()
    result = []
    for option in catalog:
        if term and term not in option.instrument.casefold() and term not in option.name.casefold():
            continue
        result.append(option)
        if len(result) >= limit:
            break
    return result
