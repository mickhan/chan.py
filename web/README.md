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
./start_web.sh
```

脚本会从仓库根目录启动本机 HTTP 服务；从其他目录调用也可以。只启动 API 时前端构建可省略，脚本会提示首页尚未构建。

打开 <http://127.0.0.1:8765/>。代码开发时，可同时运行 `npm --prefix web/frontend run dev`，Vite 会把 `/api` 请求代理到本机 Python 服务。

## 快速选择

成功生成图表后，页面会在当前浏览器保留最近分析的 10 个标的；清除当前选择或刷新页面后，可直接点击“最近分析”中的标的重新选择。这个列表保存在浏览器本地存储，与 SQLite 行情缓存分开。日期栏提供“最近 30 天”“最近 1 季度”“最近 1 年”快捷项，以上海当天为终点；如数据源有确定的起止边界，日期会截取到该范围；点击快捷项只填写日期，仍需点击“分析图表”请求数据。

## 数据与限制

- BaoStock 提供股票日、周、月、分钟线及指数日、周、月线；AkShare 为股票日、周、月线提供备用行情；新浪接口为指数提供动态 30 分钟线。页面依据实际数据源能力显示可选周期和复权方式。
- 新浪 30 分钟线接口每次只提供最新约 1970 根，已获取的旧 K 线可以继续保存在本地；尚未缓存且超出新浪当前窗口的旧数据无法补取，会报告日期范围不可用。最后一根尚未收盘的 K 线不参与分析。
- 单次最多分析 5000 根 K 线。时间按 `Asia/Shanghai` 显示，分析结果中的首末时间来自实际返回的 K 线。
- 数据源可能因网络、限流或供应商接口变化失败。遇到 `SOURCE_TIMEOUT` 可稍后重试；`DATE_RANGE_UNAVAILABLE` 可缩短日期范围；`UNSUPPORTED_PERIOD` 应改选页面提供的周期。

## 本地行情缓存

网页分析会把原始 K 线保存到仓库根目录的 `data/market.sqlite3`，该目录不会提交到 Git。标的搜索目录也保存在这个数据库：第一次没有本地目录时会完整获取一次，之后重启可直接读取；目录超过一天时先返回本地结果，再在后台刷新，刷新失败仍保留旧目录。缓存按数据源、标的、周期和复权方式区分；再次分析相同的历史范围会直接读取本地数据，扩大日期范围时只补取缺失区间，并重取末尾几天覆盖行情修正。最近三天的请求会刷新尾部，未来日期不会被标记为已获取。缠论结构和指标每次根据读取到的 K 线重新计算，不保存分析结果。

删除 `data/market.sqlite3` 后，下次分析会重新获取行情。复权数据若因后续分红送转导致较早历史价格整体变化，也可删除此文件以强制全量刷新。

## 验证

```bash
.venv/bin/python -m pytest tests/web -q
npm --prefix web/frontend run test:unit -- --run
npm --prefix web/frontend run build
npm --prefix web/frontend exec -- playwright install chromium
npm --prefix web/frontend run test:e2e
```

端到端测试使用固定模拟行情，不依赖行情供应商。实际行情请在本机运行后用短日期范围手动确认。

BaoStock 股票使用标的上市日期作为最早可选日期；AkShare 和指数没有可靠的通用历史边界时，能力接口中的日期边界可能为空。分析时会核对交易日历：如果首根 K 线前已有应该出现的交易周期，会返回 `DATE_RANGE_UNAVAILABLE`，避免把上市前历史静默截成局部数据；休市日或同一周/月内的正常首根 K 线仍可使用。
