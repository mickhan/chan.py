"""Convert a computed CChan graph to the versioned public chart contract."""
from datetime import datetime
from zoneinfo import ZoneInfo

from Common.CEnum import DATA_FIELD

from .schemas import (AnalysisMeta, BuySellPoint, Candle, ChartResponse, Indicators,
                      LineOverlay, MacdPoint, Overlays, ZoneOverlay)

_SHANGHAI = ZoneInfo('Asia/Shanghai')


def _time(klu) -> str:
    t = klu.time
    return datetime(t.year, t.month, t.day, t.hour, t.minute, t.second,
                    tzinfo=_SHANGHAI).isoformat()


def _line(item) -> LineOverlay:
    start, end = item.get_begin_klu(), item.get_end_klu()
    start_price, end_price = item.get_begin_val(), item.get_end_val()
    return LineOverlay(start_time=_time(start), start_price=start_price,
                       end_time=_time(end), end_price=end_price,
                       direction='up' if end_price >= start_price else 'down',
                       is_sure=item.is_sure)


def _point(item) -> BuySellPoint:
    return BuySellPoint(time=_time(item.klu), price=item.bi.get_end_val(),
                        side='buy' if item.is_buy else 'sell', type=item.type2str(),
                        bi_is_sure=item.bi.is_sure)


def serialize_chan(chan, request, source_id, kl_type) -> ChartResponse:
    kl = chan[kl_type]
    candles = []
    macd = []
    for klu in kl.klu_iter():
        at = _time(klu)
        candles.append(Candle(time=at, open=klu.open, high=klu.high, low=klu.low,
                              close=klu.close,
                              volume=klu.trade_info.metric[DATA_FIELD.FIELD_VOLUME] or 0))
        metric = klu.macd
        macd.append(MacdPoint(time=at, diff=metric.DIF, dea=metric.DEA,
                              histogram=metric.macd))
    if not candles:
        raise ValueError('没有可供绘图的 K 线')
    points = [*kl.bs_point_lst.bsp_iter(), *kl.seg_bs_point_lst.bsp_iter()]
    return ChartResponse(schema_version=1, request=request,
        meta=AnalysisMeta(instrument=request.instrument, period=request.period,
                          source=source_id, first_bar=candles[0].time,
                          last_bar=candles[-1].time, bar_count=len(candles)),
        candles=candles, indicators=Indicators(macd=macd),
        overlays=Overlays(bi=[_line(item) for item in kl.bi_list],
                          segments=[_line(item) for item in kl.seg_list],
                          zones=[ZoneOverlay(start_time=_time(item.begin),
                                             end_time=_time(item.end), lower=item.low,
                                             upper=item.high) for item in kl.zs_list],
                          buy_sell_points=[_point(item) for item in points]))
