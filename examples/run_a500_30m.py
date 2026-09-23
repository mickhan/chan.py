"""Render the saved Sina 30-minute data: python examples/run_a500_30m.py."""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'output' / '.matplotlib'))
import matplotlib
matplotlib.use('Agg')
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE, DATA_FIELD
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from Plot.PlotDriver import CPlotDriver

rows = json.loads((ROOT / 'output/a500_30m_source.json').read_text())
rows.sort(key=lambda row: row['day'])
# Sina can return the current unfinished bar with a future closing timestamp.
now = datetime.now(ZoneInfo('Asia/Shanghai')).replace(tzinfo=None)
rows = [row for row in rows if datetime.fromisoformat(row['day']) <= now]
assert rows, 'No completed bars returned'
cutoff = (datetime.fromisoformat(rows[-1]['day']) - timedelta(days=90)).date().isoformat()
rows = [row for row in rows if row['day'] >= cutoff]
assert rows and len({row['day'] for row in rows}) == len(rows)
config = CChanConfig({
    'bi_strict': True, 'trigger_step': True,
    'divergence_rate': float('inf'), 'bsp2_follow_1': False,
    'bsp3_follow_1': False, 'min_zs_cnt': 0, 'bs1_peak': False,
    'macd_algo': 'peak', 'bs_type': '1,2,3a,1p,2s,3b',
    'print_warning': True, 'zs_algo': 'normal',
})
chan = CChan(code='sh.000510', data_src=DATA_SRC.CSV,
             lv_list=[KL_TYPE.K_30M], config=config, autype=AUTYPE.NONE)
klines = []
for row in rows:
    dt = datetime.fromisoformat(row['day'])
    assert (dt.hour, dt.minute) in {(10,0),(10,30),(11,0),(11,30),(13,30),(14,0),(14,30),(15,0)}
    fields = {DATA_FIELD.FIELD_TIME: CTime(dt.year,dt.month,dt.day,dt.hour,dt.minute,auto=False)}
    for key, field in [('open', DATA_FIELD.FIELD_OPEN), ('high', DATA_FIELD.FIELD_HIGH),
                       ('low', DATA_FIELD.FIELD_LOW), ('close', DATA_FIELD.FIELD_CLOSE),
                       ('volume', DATA_FIELD.FIELD_VOLUME)]:
        fields[field] = float(row[key])
    assert fields[DATA_FIELD.FIELD_LOW] <= min(float(row['open']),float(row['close'])) <= max(float(row['open']),float(row['close'])) <= fields[DATA_FIELD.FIELD_HIGH]
    klines.append(CKLine_Unit(fields))
chan.trigger_load({KL_TYPE.K_30M: klines})
plot = CPlotDriver(chan, plot_config='kline,bi,seg,zs,bsp,macd',
                   plot_para={'figure': {'x_range': 0, 'w': 30, 'h': 10}})
plot.save2img(str(ROOT / 'output/a500_30m.png'))
summary = {'code': chan.code, 'source': 'Sina CN_MarketDataService.getKLineData',
           'period': '30 minutes', 'first_bar': str(klines[0].time),
           'last_bar': str(klines[-1].time), 'bar_count': len(klines),
           'bi_count': len(chan[0].bi_list), 'segment_count': len(chan[0].seg_list),
           'zhongshu_count': len(chan[0].zs_list.zs_lst)}
(ROOT / 'output/a500_30m_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
