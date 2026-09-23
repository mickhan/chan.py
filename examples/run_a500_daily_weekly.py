"""Render A500 daily and weekly charts from the saved Sina daily data."""
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
import matplotlib.pyplot as plt
import pandas as pd
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE, DATA_FIELD
from Common.CTime import CTime
from KLine.KLine_Unit import CKLine_Unit
from Plot.PlotDriver import CPlotDriver

rows = json.loads((ROOT / 'output/a500_daily_source.json').read_text())
now = datetime.now(ZoneInfo('Asia/Shanghai'))
cutoff = now.date() if now.hour >= 15 else now.date()-timedelta(days=1)
df = pd.DataFrame(rows)
df['day'] = pd.to_datetime(df['day'])
df = df.set_index('day').sort_index()
assert df.index.is_unique
for c in ['open','high','low','close','volume']:
    df[c] = pd.to_numeric(df[c])
df = df[df.index.date <= cutoff]
assert ((df['low'] <= df[['open','close']].min(axis=1)) & (df[['open','close']].max(axis=1) <= df['high'])).all()
week = df.resample('W-FRI').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
# Exclude the current calendar week, which may still change.
week = week[week.index < pd.Timestamp(now.date()-timedelta(days=now.weekday()))]
for label, level, bars in [('daily',KL_TYPE.K_DAY,df.loc['2024-01-01':]),
                            ('weekly',KL_TYPE.K_WEEK,week.loc['2020-01-01':])]:
    config = CChanConfig({
        'bi_strict':True, 'trigger_step':True,
        'divergence_rate':float('inf'), 'bsp2_follow_1':False,
        'bsp3_follow_1':False, 'min_zs_cnt':0, 'bs1_peak':False,
        'macd_algo':'peak', 'bs_type':'1,2,3a,1p,2s,3b',
        'print_warning':True, 'zs_algo':'normal',
    })
    chan = CChan(code='sh.000510',data_src=DATA_SRC.CSV,lv_list=[level],config=config,autype=AUTYPE.NONE)
    klines=[]
    for dt,row in bars.iterrows():
        fields={DATA_FIELD.FIELD_TIME:CTime(dt.year,dt.month,dt.day,0,0)}
        for c,field in [('open',DATA_FIELD.FIELD_OPEN),('high',DATA_FIELD.FIELD_HIGH),
                        ('low',DATA_FIELD.FIELD_LOW),('close',DATA_FIELD.FIELD_CLOSE),('volume',DATA_FIELD.FIELD_VOLUME)]:
            fields[field]=float(row[c])
        klines.append(CKLine_Unit(fields))
    assert klines
    chan.trigger_load({level:klines})
    plot=CPlotDriver(chan,plot_config='kline,bi,seg,zs,bsp,macd',plot_para={'figure':{'x_range':0,'w':30,'h':10}})
    plot.save2img(str(ROOT / f'output/a500_{label}.png'))
    plt.close(plot.figure)
    bars.to_csv(ROOT / f'output/a500_{label}_used.csv')
    summary={'code':chan.code,'source':'Sina daily OHLC; weekly aggregated W-FRI' if label=='weekly' else 'Sina daily OHLC',
             'period':label,'first_bar':str(klines[0].time),'last_bar':str(klines[-1].time),
             'bar_count':len(klines),'bi_count':len(chan[0].bi_list),'segment_count':len(chan[0].seg_list),
             'zhongshu_count':len(chan[0].zs_list.zs_lst),
             'note':'Pre-launch data before 2024-09-23 is back-history. Weekly timestamps label Fridays.'}
    (ROOT / f'output/a500_{label}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
