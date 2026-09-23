import json
import math
import re
from datetime import datetime

from web.backend.providers.errors import SourceDataError

_JSONP = re.compile(r"\s*[^()]*\(\s*(\[[\s\S]*\])\s*\)\s*;?\s*")
_REQUIRED = ("day", "open", "high", "low", "close", "volume")


def parse_sina_jsonp(text: str) -> list[dict]:
    match = _JSONP.fullmatch(text)
    if match is None:
        raise SourceDataError("新浪行情响应不是有效 JSONP")
    try:
        raw = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SourceDataError("新浪行情 JSON 格式错误") from exc
    if not isinstance(raw, list):
        raise SourceDataError("新浪行情响应不是 K 线数组")

    result = []
    previous = None
    for item in raw:
        if not isinstance(item, dict) or any(field not in item for field in _REQUIRED):
            raise SourceDataError("新浪 K 线缺少必要字段")
        try:
            point = datetime.fromisoformat(item["day"])
            values = {field: float(item[field]) for field in _REQUIRED[1:]}
        except (ValueError, TypeError) as exc:
            raise SourceDataError("新浪 K 线时间或价格格式错误") from exc
        if point.tzinfo is not None or (previous is not None and point <= previous):
            raise SourceDataError("新浪 K 线时间重复或未递增")
        if not all(math.isfinite(value) for value in values.values()):
            raise SourceDataError("新浪 K 线价格或成交量不是有限数值")
        if not (0 < values["low"] <= values["open"] <= values["high"]
                and values["low"] <= values["close"] <= values["high"]
                and values["volume"] >= 0):
            raise SourceDataError("新浪 K 线 OHLCV 数值不合法")
        result.append({"day": item["day"], **values})
        previous = point
    return result


from datetime import date
from zoneinfo import ZoneInfo

import requests

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from DataAPI.CommonStockAPI import CCommonStockApi
from web.backend.providers.errors import DateRangeUnavailableError, UnsupportedPeriodError

SINA_KLINE_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData"
SHANGHAI = ZoneInfo("Asia/Shanghai")


class CSina(CCommonStockApi):
    def __init__(self, code, k_type=KL_TYPE.K_30M, begin_date=None, end_date=None,
                 autype=AUTYPE.NONE, http_get=None, now=None):
        self.http_get = http_get or requests.get
        self.now = now or (lambda: datetime.now(SHANGHAI))
        super().__init__(code, k_type, begin_date, end_date, autype)

    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = False

    @classmethod
    def do_init(cls):
        return None

    @classmethod
    def do_close(cls):
        return None

    def get_kl_data(self):
        if self.k_type != KL_TYPE.K_30M or self.autype != AUTYPE.NONE:
            raise UnsupportedPeriodError("新浪指数行情只支持不复权的 30 分钟线")
        response = self.http_get(
            url=SINA_KLINE_URL,
            params={"symbol": self.code.replace(".", ""), "scale": "30", "ma": "no", "datalen": "1970"},
            timeout=15,
        )
        response.raise_for_status()
        rows = parse_sina_jsonp(response.text)
        current = self.now()
        if current.tzinfo is None:
            current = current.replace(tzinfo=SHANGHAI)
        begin = date.fromisoformat(str(self.begin_date)) if self.begin_date else None
        end = date.fromisoformat(str(self.end_date)) if self.end_date else None
        complete_rows = []
        for row in rows:
            when = datetime.fromisoformat(row["day"])
            if when.replace(tzinfo=SHANGHAI) <= current:
                complete_rows.append((when, row))
        if complete_rows and begin and begin < complete_rows[0][0].date():
            raise DateRangeUnavailableError(
                f"新浪 30 分钟历史仅覆盖 {complete_rows[0][0].date().isoformat()} 起的日期"
            )
        for when, row in complete_rows:
            if (begin and when.date() < begin) or (end and when.date() > end):
                continue
            fields = {
                DATA_FIELD.FIELD_TIME: CTime(
                    when.year, when.month, when.day, when.hour, when.minute,
                    when.second, auto=False,
                ),
                DATA_FIELD.FIELD_OPEN: row["open"],
                DATA_FIELD.FIELD_HIGH: row["high"],
                DATA_FIELD.FIELD_LOW: row["low"],
                DATA_FIELD.FIELD_CLOSE: row["close"],
                DATA_FIELD.FIELD_VOLUME: row["volume"],
            }
            yield CKLine_Unit(fields)
