from types import SimpleNamespace as NS

from Common.CEnum import DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from web.backend.schemas import AnalysisRequest
from web.backend.serializers import serialize_chan
from test_chan_prefetched import bar


def request():
    return AnalysisRequest(market='cn', instrument='sh.000001', period='30m',
        begin_time='2026-09-01', end_time='2026-09-02', adjustment='none')


def test_real_engine_bars_and_shanghai_time():
    from Chan import CChan
    from ChanConfig import CChanConfig
    chan = CChan('sh.000001', lv_list=[KL_TYPE.K_DAY], config=CChanConfig(), defer_load=True)
    chan.trigger_load({KL_TYPE.K_DAY: [bar(i, 10 + i % 4) for i in range(1, 17)]})
    result = serialize_chan(chan, request(), 'fixture', KL_TYPE.K_DAY)
    assert result.meta.bar_count == 16
    assert result.candles[0].time == '2026-09-01T00:00:00+08:00'
    assert result.meta.last_bar == result.candles[-1].time
    assert len(result.indicators.macd) == 16


def test_overlay_endpoints_and_macd():
    a = bar(1, 10)
    b = bar(2, 12)
    a.macd = NS(DIF=1.25, DEA=.5, macd=1.5)
    b.macd = NS(DIF=1, DEA=.4, macd=1.2)
    line = NS(get_begin_klu=lambda: a, get_end_klu=lambda: b,
        get_begin_val=lambda: 10., get_end_val=lambda: 12., is_sure=False)
    zone = NS(begin=a, end=b, low=10.5, high=11.5)
    buy = NS(klu=b, bi=line, is_buy=True, type2str=lambda: '1')
    sell = NS(klu=a, bi=line, is_buy=False, type2str=lambda: '2')
    points = NS(bsp_iter=lambda: iter([buy, sell]))
    kl = NS(klu_iter=lambda: iter([a, b]), bi_list=[line], seg_list=[line],
        zs_list=[zone], bs_point_lst=points, seg_bs_point_lst=NS(bsp_iter=lambda: iter([])))
    result = serialize_chan({KL_TYPE.K_30M: kl}, request(), 'fixture', KL_TYPE.K_30M)
    assert result.indicators.macd[0].diff == 1.25
    assert result.overlays.bi[0].start_time == '2026-09-01T00:00:00+08:00'
    assert result.overlays.segments[0].end_price == 12
    assert result.overlays.zones[0].lower == 10.5
    assert [p.side for p in result.overlays.buy_sell_points] == ['buy', 'sell']
    assert result.overlays.buy_sell_points[0].bi_is_sure is False
