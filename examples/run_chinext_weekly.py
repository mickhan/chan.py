"""Run from the repository: .venv/bin/python examples/run_chinext_weekly.py"""
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'output' / '.matplotlib'))
import matplotlib
matplotlib.use('Agg')
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.PlotDriver import CPlotDriver

config = CChanConfig({
    'bi_strict': True, 'trigger_step': False,
    'divergence_rate': float('inf'), 'bsp2_follow_1': False,
    'bsp3_follow_1': False, 'min_zs_cnt': 0, 'bs1_peak': False,
    'macd_algo': 'peak', 'bs_type': '1,2,3a,1p,2s,3b',
    'print_warning': True, 'zs_algo': 'normal',
})
chan = CChan(code='sz.399006', begin_time='2020-01-01',
             end_time=date.today().isoformat(), data_src=DATA_SRC.BAO_STOCK,
             lv_list=[KL_TYPE.K_WEEK], config=config, autype=AUTYPE.NONE)
daily = chan[0]
klines = [klu for klc in daily for klu in klc]
assert klines, 'No market data returned'
plot = CPlotDriver(chan, plot_config='kline,bi,seg,zs,bsp,macd',
                   plot_para={'figure': {'x_range': 0, 'w': 30, 'h': 10}})
plot.save2img(str(ROOT / 'output' / 'chinext_weekly.png'))
summary = {
    'code': chan.code, 'source': 'BaoStock', 'adjustment': 'none',
    'first_bar': str(klines[0].time), 'last_bar': str(klines[-1].time),
    'bar_count': len(klines), 'last_close': klines[-1].close,
    'bi_count': len(daily.bi_list), 'segment_count': len(daily.seg_list),
    'zhongshu_count': len(daily.zs_list.zs_lst),
    'latest_bsp': [{'time': str(b.klu.time), 'side': 'buy' if b.is_buy else 'sell',
                    'type': b.type2str(), 'bi_is_sure': b.bi.is_sure}
                   for b in chan.get_latest_bsp(number=10)],
}
(ROOT / 'output' / 'chinext_weekly_summary.json').write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
