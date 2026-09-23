"""Sina daily K-lines for listed LOF funds."""
from datetime import date

import akshare as ak

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from .CommonStockAPI import CCommonStockApi


class CSinaFund(CCommonStockApi):
    def SetBasciInfo(self):
        self.name = self.code
        self.is_stock = True

    @classmethod
    def do_init(cls):
        pass

    @classmethod
    def do_close(cls):
        pass

    def get_kl_data(self):
        if self.k_type != KL_TYPE.K_DAY or self.autype != AUTYPE.NONE:
            raise ValueError('新浪 LOF 仅支持不复权日线')
        frame = ak.fund_etf_hist_sina(symbol=self.code)
        for row in frame.to_dict('records'):
            day = row['date']
            if not isinstance(day, date):
                day = date.fromisoformat(str(day)[:10])
            if self.begin_date and day < date.fromisoformat(self.begin_date):
                continue
            if self.end_date and day > date.fromisoformat(self.end_date):
                continue
            yield CKLine_Unit({
                DATA_FIELD.FIELD_TIME: CTime(day.year, day.month, day.day, 0, 0),
                DATA_FIELD.FIELD_OPEN: float(row['open']),
                DATA_FIELD.FIELD_HIGH: float(row['high']),
                DATA_FIELD.FIELD_LOW: float(row['low']),
                DATA_FIELD.FIELD_CLOSE: float(row['close']),
                DATA_FIELD.FIELD_VOLUME: float(row['volume']),
                DATA_FIELD.FIELD_TURNOVER: float(row.get('amount') or 0),
            })
