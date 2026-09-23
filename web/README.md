# 本机缠论图表

本应用在浏览器中选择 A 股股票或指数、周期与日期范围，显示 K 线、笔、线段、中枢、买卖点和 MACD。仅监听 `127.0.0.1:8765`，供个人本机使用。

## 安装和运行

在仓库根目录执行：

```bash
pyenv local 3.12.8
python -m venv .venv
.venv/bin/python -m pip install -r Script/requirements-web.txt
npm --prefix web/frontend ci
npm --prefix web/frontend run build
.venv/bin/python -m web
```

打开 <http://127.0.0.1:8765/>。代码开发时，可同时运行 `npm --prefix web/frontend run dev`，Vite 会把 `/api` 请求代理到本机 Python 服务。

## 数据与限制

- BaoStock 提供股票日、周、月、分钟线及指数日、周、月线；AkShare 为股票日、周、月线提供备用行情；新浪接口为指数提供动态 30 分钟线。页面依据实际数据源能力显示可选周期和复权方式。
- 新浪 30 分钟线接口单次最多请求 1970 根，超过实际可取范围会报告日期范围不可用。最后一根尚未收盘的 K 线不参与分析。
- 单次最多分析 5000 根 K 线。时间按 `Asia/Shanghai` 显示，分析结果中的首末时间来自实际返回的 K 线。
- 数据源可能因网络、限流或供应商接口变化失败。遇到 `SOURCE_TIMEOUT` 可稍后重试；`DATE_RANGE_UNAVAILABLE` 可缩短日期范围；`UNSUPPORTED_PERIOD` 应改选页面提供的周期。

## 验证

```bash
.venv/bin/python -m pytest tests/web -q
npm --prefix web/frontend run test:unit -- --run
npm --prefix web/frontend run build
npm --prefix web/frontend exec -- playwright install chromium
npm --prefix web/frontend run test:e2e
```

端到端测试使用固定模拟行情，不依赖行情供应商。实际行情请在本机运行后用短日期范围手动确认。
