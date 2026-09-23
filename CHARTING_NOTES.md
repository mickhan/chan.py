# 指数缠论图生成记录

记录日期：2026-09-22。本文核对现有脚本、配置及结果摘要，记录截至本次整理的工作状态。已确认的七张图生成于 2026-09-17；本次只整理文档，未刷新行情或重绘。

## 1. 环境

- 项目：`chan.py`，macOS，业务时区 `Asia/Shanghai`。
- Python：pyenv 已安装的 **3.12.8**，项目根目录 `.python-version` 固定版本；未更改全局 Python。
- 依赖隔离：项目根目录 `.venv/`。
- 基础依赖清单：`Script/requirements.txt`。
- 本次安装版本快照：`Script/requirements-charting-resolved.txt`。
- 关键安装版本：baostock 0.9.3、matplotlib 3.11.2、numpy 2.5.3、pandas 3.0.5、requests 2.34.2。
- 绘图使用 Matplotlib 的 `Agg` 后端，不需要桌面窗口；字体缓存放在 `output/.matplotlib/`。
- 本轮绘图没有依赖 AkShare 或 PyQt6。GUI 的额外依赖不属于本次已配置环境的保证范围。

在项目根目录运行：

```bash
source .venv/bin/activate
python --version
python -m pip check
```

重建环境时（前提是 pyenv 中已安装 3.12.8）：

```bash
PYENV_VERSION=3.12.8 pyenv exec python -m venv .venv
source .venv/bin/activate
python -m pip install -r Script/requirements-charting-resolved.txt
```

版本快照缺失时可使用 `Script/requirements.txt`，但它只有最低版本限制，不能保证重建出相同依赖版本。

## 2. 指数与代码

| 指数 | 程序图题/带市场前缀代码 | 新浪接口 symbol |
|---|---|---|
| 上证指数 | sh.000001 | sh000001 |
| 创业板指 | sz.399006 | sz399006 |
| 中证 A500 | sh.000510 | sh000510 |

A500 指中证 A500，不是中证 500，也不是 A500 ETF。中证 A500 正式发布日期为 2024-09-23；图中更早的数据属于供应商提供的回溯历史。

官方参考：[中证 A500 指数资料](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000510factsheet.pdf)。

所有指数图使用不复权口径 `AUTYPE.NONE`。

## 3. 数据来源和接入方式

### BaoStock：上证日线、创业板周线

- 使用仓库自带 `DataAPI/BaoStockAPI.py`，`DATA_SRC.BAO_STOCK`。
- 脚本每次运行会联网，截止日期为 `date.today()`，实际末条日期以接口返回为准。
- 仓库接口明确禁止指数分钟线，因此指数 30m 使用新浪。
- 2026-09-17 查询 A500 时，BaoStock 基本信息、日线和周线均返回空数据；这只是当次观察，不保证服务将来仍无数据。
- 本次未保存 BaoStock 原始日/周行情快照，所以这两张图不能保证以后逐字节复现。

### 新浪：三个指数的 30m、A500 日线

已实际使用的公开行情端点：

```text
https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData
```

请求参数：

| 参数 | 已使用值 | 说明 |
|---|---|---|
| symbol | sh000001 / sz399006 / sh000510 | 指数代码 |
| scale | 30 / 240 | 本次分别返回 30 分钟 / 日线数据 |
| ma | no | 不请求均线 |
| datalen | 1970 | 请求的条数；实际范围取决于接口返回 |

返回 JSONP，数据字段包括 `day, open, high, low, close, volume`，部分返回还含 `amount`。抓取过程是一次性命令，尚未封装为独立下载脚本。

以下示例只下载快照，不计算缠论；重新执行会覆盖同名数据文件：

```python
import json
from pathlib import Path
import requests

symbol, scale = "sh000510", "30"
output_file = Path("output/a500_30m_source.json")
response = requests.get(
    "https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData",
    params={"symbol": symbol, "scale": scale, "ma": "no", "datalen": "1970"},
    timeout=30,
)
response.raise_for_status()
rows = json.loads(response.text.split("=(", 1)[1].rsplit(");", 1)[0])
assert isinstance(rows, list) and rows
output_file.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
```

更新 A500 日线时改 `scale="240"`，保存到 `output/a500_daily_source.json`。其他指数 30m 分别保存到 `shanghai_30m_source.json`、`chinext_30m_source.json`。

接入计算的方式：本地 JSON → `CKLine_Unit` → `CChan.trigger_load()`。这些脚本虽然传入 `DATA_SRC.CSV`，实际并没有调用 CSV 数据源读取器；行情的真实来源仍是新浪，CSV 枚举仅作为初始化占位。

### A500 周线：由新浪日线汇总

直接查询新浪 `scale=1200` 只返回 2024 年以来的周线，已保存为 `output/a500_weekly_source.json`，**但最终周图没有使用该文件**。

最终使用 `a500_daily_source.json`，通过 pandas `resample('W-FRI')` 汇总：

- open：周内首日开盘；high：周内最高；low：周内最低。
- close：周内末日收盘；volume：周内成交量之和。
- 周标签使用周五，即使节假日导致该周最后交易日不是周五。
- 现有脚本排除运行当天所在的整周；周五收盘后运行也仍排除当周。
- 最终使用的日/周数据另存 `a500_daily_used.csv`、`a500_weekly_used.csv`。

## 4. 缠论计算配置

七张图共用的显式形态参数如下：

```python
{
    "bi_strict": True,
    "divergence_rate": float("inf"),
    "bsp2_follow_1": False,
    "bsp3_follow_1": False,
    "min_zs_cnt": 0,
    "bs1_peak": False,
    "macd_algo": "peak",
    "bs_type": "1,2,3a,1p,2s,3b",
    "print_warning": True,
    "zs_algo": "normal",
}
```

- `trigger_step=False`：BaoStock 的上证日线、创业板周线，初始化时直接加载计算。
- `trigger_step=True`：新浪本地快照脚本，防止初始化自动拉取数据，之后通过 `trigger_load()` 输入 K 线；并不表示这些脚本在执行交易回测。
- 每张图独立计算一个周期，未做多周期联立或“共振”确认。

部分未显式覆盖、但影响结果的当前源码默认值：

| 参数 | 当前值 |
|---|---|
| bi_algo / bi_fx_check | normal / strict |
| bi_end_is_peak / bi_allow_sub_peak | True / True |
| gap_as_kl | False |
| seg_algo / left_seg_method | chan / peak |
| zs_combine / zs_combine_mode | True / zs |
| one_bi_zs | False |
| bsp1_only_multibi_zs | True |
| max_bs2_rate | 0.9999 |
| bsp2s_follow_2 / strict_bsp3 | False / False |
| MACD fast / slow / signal | 12 / 26 / 9 |

以 `ChanConfig.py`、`Bi/BiConfig.py`、`BuySellPoint/BSPointConfig.py` 等实际源码为准。此前讲解引用快速指南时提到的某些默认值与当前代码不一致，例如当前 `divergence_rate` 默认是 inf，`max_bs2_rate` 默认是 0.9999，而非指南所写的 0.9、0.618。

这些是宽松的演示参数：`divergence_rate=inf` 基本放开背驰力度阈值，`min_zs_cnt=0` 不要求最低中枢数量，二、三类点不要求先出现合格的一类点。图上 b1/b1p 不代表已经完成严格背驰验证。

## 5. 绘图配置和图例

```python
plot_config = "kline,bi,seg,zs,bsp,macd"
plot_para = {"figure": {"x_range": 0, "w": 30, "h": 10}}
```

- `x_range=0`：显示本次输入的全部 K 线。最初上证图用过 200，后来已改为全范围。
- `w=30, h=10`：Matplotlib 图尺寸设置；MACD 子图会增加整体高度，不是像素尺寸。
- 使用 `CPlotDriver.save2img()` 保存 PNG，内部 `bbox_inches='tight'`；没有显式固定 dpi。
- 原始 K 线红涨绿跌；黑色折线为笔，绿色粗线为线段，橙色框为中枢。
- `b` 为买点、`s` 为卖点，后缀是类别；不是评分或成功率。
- 虚线表示相关结构尚未确认。
- 当前未开启 `kline_combine`：显示的是原始周期 K 线，不是合并后的蜡烛。计算内部仍会处理包含关系。若需叠加合并范围框，在 `plot_config` 中增加 `kline_combine`。
- 周图上的中枢来自该图输入周 K 的笔段计算，不自动等同于严格递归理论定义的“周线级别中枢”。

## 6. 已生成结果快照

下表来自现有 `*_summary.json`，是 2026-09-17 的结果，不是 2026-09-22 最新行情。

| 图文件（output/ 内） | 首根 K 线 | 末根 K 线 | 根数 | 笔 / 段 / 中枢 |
|---|---|---|---:|---|
| shanghai_daily.png | 2024-01-02 | 2026-09-16 | 657 | 31 / 8 / 2 |
| shanghai_30m.png | 2026-06-22 10:00 | 2026-09-17 11:30 | 508 | 35 / 5 / 4 |
| chinext_30m.png | 2026-06-22 10:00 | 2026-09-17 11:30 | 508 | 30 / 5 / 5 |
| chinext_weekly.png | 2020-01-03 | 2026-09-11 | 343 | 17 / 5 / 1 |
| a500_weekly.png | 2020-01-03 | 2026-09-11 | 343 | 18 / 4 / 2 |
| a500_daily.png | 2024-01-02 | 2026-09-17 | 658 | 37 / 9 / 3 |
| a500_30m.png | 2026-06-22 10:00 | 2026-09-17 15:00 | 512 | 34 / 4 / 4 |

30m 窗口取快照最后一根有效 K 线日期向前 90 个自然日，并非固定 90 个交易日。各图抓取时点不同，末条时间不完全一致。

另外发现 `output/shanghai_daily_1d.png`，当前记录中的脚本没有引用它，也没有对应独立摘要；未将其纳入已核实结果表。

## 7. 运行入口与更新行为

在项目根目录激活环境后执行对应命令；会覆盖同名图和摘要。

| 命令 | 输入方式 | 产物 |
|---|---|---|
| python examples/run_shanghai.py | 每次联网请求 BaoStock | 上证日图及 shanghai_summary.json |
| python examples/run_chinext_weekly.py | 每次联网请求 BaoStock | 创业板周图及摘要 |
| python examples/run_shanghai_30m.py | 本地 shanghai_30m_source.json | 上证 30m 图及摘要 |
| python examples/run_chinext_30m.py | 本地 chinext_30m_source.json | 创业板 30m 图及摘要 |
| python examples/run_a500_30m.py | 本地 a500_30m_source.json | A500 30m 图及摘要 |
| python examples/run_a500_daily_weekly.py | 本地 a500_daily_source.json | A500 日、周图，摘要及使用数据 CSV |

**重绘本地新浪快照不等于更新行情。** 需要先重新下载对应 source JSON，再运行绘图脚本。

## 8. 未完成 K 线和复现限制

- 新浪 30m 接口可能提前返回当前正在形成的 K 线，时间戳写的是未来收盘时间。创业板和 A500 脚本会过滤时间戳晚于当前上海时间的条目；上证 30m 旧脚本尚无该过滤。
- 创业板原始快照包含抓取时未完成的 `2026-09-17 13:30` 条目，原图运行时已排除。现在重跑旧快照，该时间已过去，会把当时保存的半根 K 线纳入。**不能仅靠当前时间判断旧快照是否完整**；应重新获取已收盘行情，或固定原始抓取时点再过滤。
- A500 周线按运行当天排除当周。旧日线快照跨周重跑，可能把快照截止日所在的不完整周当作历史周纳入。例如旧快照截至 9 月 17 日，9 月 22 日重跑可能产生标记为 9 月 18 日、实际只有周一至周四的周 K。应先更新日线，或固定当时的截止边界。
- 现有 source JSON 尚未附带统一的抓取时点、完成状态和请求元数据。需要严格复现时，必须同时保留脚本、依赖、原始数据、过滤截止时间和结果摘要。
- 买卖点标在形态对应的高低点，并非首次可识别时间；随后可能移动或消失。`bsp.bi.is_sure` 只表示所属笔已确认，不等于整个信号以后不会变化。
- 单次静态绘图没有执行交易回测，也没有验证跨指数或跨周期共振。

## 9. 保存位置与版本管理

- 本文 `CHARTING_NOTES.md` 放在项目根目录，不受 `output/` 忽略规则影响，可加入版本管理。
- `.python-version` 保存项目 Python 版本。
- `.venv/` 和整个 `output/` 已加入 `.gitignore`。迁移后示例脚本位于 `examples/`，依赖快照位于 `Script/requirements-charting-resolved.txt`，可纳入版本管理。数据快照、图和摘要仍在 `output/`，**不会随普通 git add 自动纳入版本管理**。
- 行情与图片仍是本机历史归档；Git 克隆不会包含这些文件。重新运行脚本会覆盖同名产物，长期保留时请先另行备份。


## 10. 2026-09-23 迁移说明

- 从本机 `chan.py_bak` 迁入当前 fork；两者核心代码均为提交 `429d6ed`。
- 六个绘图脚本移至 `examples/`，只更新入口说明，计算逻辑保持原样。
- Python 版本与绘图依赖快照已保存；未复制虚拟环境，未验证新环境依赖安装。
- 本文前述结果表是历史记录。现有上证日线及 30m 元数据已更新至 2026-09-23 抓取、最后 K 线为 2026-09-22，不能将全部产物视为同一批次。
- 上证日线快照元数据标记来源为新浪，但 `examples/run_shanghai.py` 仍调用 BaoStock，无法用该脚本直接复现此新浪快照结果。
- 上证 30m 未过滤未收盘 K 线；其他快照脚本使用运行时刻过滤，A500 周线也按运行日期排除当周。迁移没有修复这些已知限制，重跑旧快照前应先确定抓取时点和完整 K 线边界。
- 本次只迁移文件，没有刷新行情或重绘图片。


## 11. 2026-09-23 环境重建与运行验证

- 使用本机 pyenv 的 Python 3.12.8 创建项目 `.venv`；未修改全局 Python。
- 安装 `Script/requirements-charting-resolved.txt`，34 个固定依赖版本全部匹配，`python -m pip check` 通过。
- 在临时项目副本运行全部 6 个绘图脚本，退出码均为 0：4 个本地快照脚本及 2 个 BaoStock 联网脚本。
- 生成 7 张 PNG，并通过 Pillow 文件完整性校验；没有执行图表内容的人工视觉验收。
- 通过 SHA-256 核对，原 `output/` 中全部 25 个归档文件保持不变。
- 本次验证的图片、摘要、日志及结果 JSON 保存在本机 `output/validation-2026-09-23/`，该目录不进入 Git。
- 运行成功不表示旧快照严格复现：创业板 30m 本次为 509 根，纳入了旧记录提到的 2026-09-17 13:30 条目；A500 周线为 344 根，包含标记为 2026-09-18 的不完整周。这些是已有时间过滤限制，本次未修改算法。
- GUI 的 PyQt6、AkShare 依赖未安装或验证。

进入项目后激活：

```bash
source .venv/bin/activate
python --version
python -m pip check
```
