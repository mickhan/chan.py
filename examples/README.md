# 指数绘图示例

从项目根目录运行，使用 Python 3.12.8。环境重建示例：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r Script/requirements-charting-resolved.txt
mkdir -p output
python examples/run_shanghai.py
```

依赖快照来自旧绘图环境。2026-09-23 已使用 pyenv Python 3.12.8 重建项目 `.venv`，34 个固定依赖版本核对一致，`pip check` 通过，6 个绘图脚本运行通过。GUI 的 PyQt6、AkShare 依赖未安装或验证。

| 脚本 | 数据输入 | 图表 |
|---|---|---|
| `run_shanghai.py` | 联网 BaoStock | 上证日线 |
| `run_chinext_weekly.py` | 联网 BaoStock | 创业板周线 |
| `run_shanghai_30m.py` | `output/shanghai_30m_source.json` | 上证 30m |
| `run_chinext_30m.py` | `output/chinext_30m_source.json` | 创业板 30m |
| `run_a500_30m.py` | `output/a500_30m_source.json` | A500 30m |
| `run_a500_daily_weekly.py` | `output/a500_daily_source.json` | A500 日线与周线 |

`output/` 是被 Git 忽略的本地历史数据和产物目录，新克隆不包含行情快照。快照脚本要求先提供对应输入文件；下载示例和配置说明见 [绘图记录](../CHARTING_NOTES.md)。

运行会覆盖同名图片、摘要和派生 CSV；保留历史结果时请先备份。重绘快照不会更新行情。现有时间过滤不能保证旧快照严格复现，详见绘图记录第 8、10 节。
