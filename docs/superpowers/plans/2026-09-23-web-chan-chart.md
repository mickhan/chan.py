# Web Chan Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个本机浏览器应用，让用户按标的、周期和日期范围生成可交互的缠论 K 线图。

**Architecture:** FastAPI 负责数据源能力、标的搜索、行情和 `CChan` 分析；Vue 前端提交查询并用 ECharts 绘制结构化响应。后端通过版本化 DTO 隔离 `CChan` 内部对象，生产环境由 FastAPI 同源提供已构建的前端静态文件。

**Tech Stack:** Python 3.12.8、FastAPI、Pydantic、pytest、Vue 3、TypeScript、Vite、Apache ECharts、Vitest、Playwright。

**Spec:** `docs/superpowers/specs/2026-09-23-web-chan-chart-design.md`

## Global Constraints

- 面向个人本机使用，服务监听 `127.0.0.1`；不提供登录和远程多人访问。
- 初始标的范围为 A 股股票和指数。加密货币、回测、实时推送、扫描器和云部署不在首版范围。
- 历史数据周期至少覆盖日线、周线和 30 分钟线中由数据源实际支持的组合。
- 股票复权方式由数据源能力决定；指数不提供复权选项。日期和时间统一按 `Asia/Shanghai` 解释，并在响应中明确时区。
- 首版采用稳定的默认 `CChanConfig`，不让网页提交任意内部参数；图层开关只影响展示。
- 缠论计算按单周期进行；多级别联立图表不属于首版目标。
- 指数 30 分钟行情须动态取数；静态 JSON 只能用于离线 fixture 和手工回归。
- BaoStock 连接生命周期受类级状态影响；首版对 BaoStock 请求加锁并一次只运行一个分析请求。

## Review Focus

- 未支持的标的/周期组合必须在调用供应商前返回 `UNSUPPORTED_PERIOD`；Task 2 添加该测试。
- 请求日期跨出供应商实际覆盖范围时必须报告 `DATE_RANGE_UNAVAILABLE`，不得静默返回局部历史；Task 3 添加新浪适配器范围测试。
- 新浪 JSONP 缺少字段、日期重复或 OHLC 不合法时必须返回 `SOURCE_ERROR`，不能构造错误 K 线；Task 3 添加 fixture 测试。
- 请求日期边界、上海时区和供应商最后一根未完成 K 线不能导致响应伪造数据范围；Task 4 添加时区与实际首末 K 线测试。
- 两个并发 BaoStock 请求不能互相登录/退出；Task 2 添加锁生命周期测试。

---

### Task 1: 建立后端应用、类型契约和测试入口

**Files:**
- Create: `Script/requirements-web.txt`
- Create: `pytest.ini`
- Create: `web/__init__.py`
- Create: `web/backend/__init__.py`
- Create: `web/backend/app.py`
- Create: `web/backend/routes.py`
- Create: `web/backend/schemas.py`
- Create: `tests/web/backend/test_schemas.py`
- Create: `tests/web/backend/test_api.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces `AnalysisRequest`, `InstrumentOption`, `PeriodCapability`, `CapabilityResponse`, `ChartResponse` 和 `ErrorResponse` Pydantic 模型。
- Produces `create_app(registry, analysis_service) -> FastAPI`，以依赖注入方式构造 app，便于测试替身。
- Initial API routes: `GET /api/v1/capabilities`, `GET /api/v1/instruments`, `POST /api/v1/analysis`。

- [ ] **Step 1: 写请求校验失败测试并准备测试依赖**

创建 `Script/requirements-web.txt`，内容包含 `-r requirements.txt`、`fastapi`、`uvicorn`、`akshare`、`pytest`、`pytest-mock` 和 `httpx`。创建 `pytest.ini`，配置仓库导入路径及 `tests/` 默认目录。此时不要创建 schemas 实现。

```python
import pytest
from pydantic import ValidationError
from web.backend.schemas import AnalysisRequest


def test_analysis_request_rejects_reversed_dates():
    with pytest.raises(ValidationError):
        AnalysisRequest(
            market="cn", instrument="sh.000001", period="1d",
            begin_time="2026-09-23", end_time="2026-09-01", adjustment="none",
        )
```

同时添加响应模型测试，验证响应必须有 `schema_version == 1`、实际 `first_bar`/`last_bar`、K 线数组和覆盖层数组。

- [ ] **Step 2: 安装 Web 测试依赖并确认红灯**

Run: `.venv/bin/python -m pip install -r Script/requirements-web.txt && .venv/bin/python -m pytest tests/web/backend/test_schemas.py -q`
Expected: FAIL，显示 `web.backend.schemas` 尚不存在。

- [ ] **Step 3: 实现 schemas 模型**

`AnalysisRequest` 字段为 `market`, `instrument`, `period`, `begin_time`, `end_time`, `adjustment`；验证开始日期不晚于结束日期。为 K 线、MACD、笔/线段、中枢、买卖点及 `meta` 定义独立模型。应用工厂接受 registry 和 analysis service，不在模块导入时访问网络。

- [ ] **Step 4: 实现最小 FastAPI 应用工厂和三条路由**

`create_app(registry, analysis_service)` 将依赖保存在 `app.state`，并挂载三条 `/api/v1` 路由。`GET /api/v1/capabilities` 与 `GET /api/v1/instruments` 调用 registry；`POST /api/v1/analysis` 调用 analysis service。`.gitignore` 忽略 `web/frontend/node_modules/`、`web/frontend/dist/` 和 `.pytest_cache/`。

- [ ] **Step 5: 运行模型和路由测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_schemas.py tests/web/backend/test_api.py -q`
Expected: PASS；应用测试用 fake registry 和 fake analysis service，不发真实行情请求。

- [ ] **Step 6: 提交后端契约基础**

```bash
git add Script/requirements-web.txt pytest.ini web tests/web/backend .gitignore
git commit -m "feat: add web chart api contracts"
```

### Task 2: 数据源能力注册与标的搜索

**Files:**
- Create: `web/backend/providers/base.py`
- Create: `web/backend/providers/errors.py`
- Create: `web/backend/providers/registry.py`
- Create: `web/backend/capabilities.py`
- Create: `web/backend/instruments.py`
- Create: `web/backend/providers/baostock.py`
- Create: `web/backend/providers/akshare.py`
- Create: `tests/web/backend/test_capabilities.py`
- Create: `tests/web/backend/test_instruments.py`
- Create: `tests/web/backend/test_provider_registry.py`
- Modify: `web/backend/routes.py`

**Interfaces:**
- `ProviderAdapter` exposes `source_id`, `chan_data_source`, `supports(instrument, period, adjustment) -> bool`, `capabilities(market, instrument=None) -> list[PeriodCapability]`, `search_instruments(market, query, limit) -> list[InstrumentOption]`, `fetch_klines(request, max_bars) -> list[CKLine_Unit]`, `period_to_kl_type(period) -> KL_TYPE` and `adjustment_to_autype(adjustment) -> AUTYPE`。
- Provider exceptions are `UnsupportedPeriodError`, `DateRangeUnavailableError`, `SourceDataError` and `SourceTimeoutError`; each has an API code and safe message.
- `ProviderRegistry.resolve(market, instrument, period, adjustment) -> ProviderAdapter`；无匹配时抛出 `UnsupportedPeriodError`。
- `ProviderRegistry.capabilities(market, instrument=None) -> CapabilityResponse`。
- `ProviderRegistry.search(market, query, limit=20) -> list[InstrumentOption]`。
- `ProviderRegistry.guard(provider) -> ContextManager[None]`；同一数据源的读数生命周期串行执行。

- [ ] **Step 1: 写 registry 解析失败测试**

用 `FakeProvider` 测试注册后能按 A 股/指数、代码、周期和复权方式匹配；不支持的周期抛 `UnsupportedPeriodError`；多个 provider 都匹配时按注册优先级稳定选中第一个。此测试不进行网络请求。

- [ ] **Step 2: 运行测试确认 registry 不存在**

Run: `.venv/bin/python -m pytest tests/web/backend/test_provider_registry.py -q`
Expected: FAIL，`ProviderRegistry` 尚未实现。

- [ ] **Step 3: 实现 provider 错误类**

在 `providers/errors.py` 定义 `ProviderError`、`UnsupportedPeriodError`、`DateRangeUnavailableError`、`SourceDataError` 和 `SourceTimeoutError`。每种类型都保留稳定的 API `code` 与用户可读 `message`。

- [ ] **Step 4: 实现 provider protocol 和 registry**

定义只读 provider 描述、显式 `supports` 匹配以及确定性 `resolve`。未知市场或无匹配组合抛出有结构的 `UnsupportedPeriodError`，不要选择任意默认数据源。

- [ ] **Step 5: 运行 registry 测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_provider_registry.py -q`
Expected: PASS；不访问真实供应商。

- [ ] **Step 6: 写能力和标的目录失败测试**

测试 BaoStock 和 AkShare 的周期/复权 capability fixture；测试股票和指数返回规范代码/名称；代码片段和名称片段均可搜索，空查询和无匹配分别返回限定数量目录与空列表。

- [ ] **Step 7: 运行能力/目录测试确认红灯**

Run: `.venv/bin/python -m pytest tests/web/backend/test_capabilities.py tests/web/backend/test_instruments.py -q`
Expected: FAIL，BaoStock/AkShare adapters 尚未注册。

- [ ] **Step 8: 实现 BaoStock/AkShare capability 映射**

每个 provider 显式列出其实际周期、标的类型、复权能力和可用日期边界。将供应商代码规范化为市场代码；索引由已有 provider 搜索能力取得，不在前端内置供应商别名转换。

- [ ] **Step 9: 实现股票和指数目录适配器**

用 BaoStock/AkShare 的目录查询实现按代码和名称搜索；将行情代码转换为 canonical instrument ID，并在 provider 内转换回供应商代码。搜索结果限制为每次 20 项，且代码或名称子串都能命中。

- [ ] **Step 10: 接入 capability 和 instrument 路由**

`GET /api/v1/capabilities` 调用 `registry.capabilities()`；`GET /api/v1/instruments` 校验市场和 query 长度后调用 `registry.search()`。两端都通过 `app.state` 注入 registry。

- [ ] **Step 11: 写 BaoStock 锁生命周期测试**

用两个线程和 `threading.Event` 验证同一 BaoStock provider 的两个 `registry.guard(provider)` 不能同时进入；不同 provider 的 guard 不共享锁。测试不得 sleep 轮询，使用事件同步。

- [ ] **Step 12: 运行锁测试确认红灯**

Run: `.venv/bin/python -m pytest tests/web/backend/test_provider_registry.py -q`
Expected: 锁生命周期测试失败，因为 guard 尚未串行同源请求。

- [ ] **Step 13: 实现 per-provider 请求锁并跑源层测试**

BaoStock/AkShare adapter 通过既有 `CCommonStockApi` 子类读取 K 线：调用 `do_init()`、构造 provider class、完整消费 `get_kl_data()`、无论成功或异常都执行 `do_close()`。在 registry 中按 `source_id` 保存锁；分析服务在 `fetch_klines()` 外使用 guard，确保 BaoStock `do_init`、K 线迭代和 `do_close` 位于同一锁区间。

Run: `.venv/bin/python -m pytest tests/web/backend/test_provider_registry.py tests/web/backend/test_capabilities.py tests/web/backend/test_instruments.py -q`
Expected: PASS；所有网络行为都由 mock 拦截。

- [ ] **Step 14: 提交 registry 与标的目录**

```bash
git add web/backend/providers/base.py web/backend/providers/errors.py web/backend/providers/registry.py web/backend/capabilities.py web/backend/instruments.py web/backend/providers/baostock.py web/backend/providers/akshare.py web/backend/routes.py tests/web/backend

git commit -m "feat: add market capabilities and instrument search"
```

### Task 3: 动态指数分钟线 Sina 适配器

**Files:**
- Create: `DataAPI/SinaAPI.py`
- Create: `web/backend/providers/sina.py`
- Create: `tests/web/backend/test_sina_api.py`
- Create: `tests/web/backend/fixtures/sina_30m.jsonp`
- Modify: `web/backend/providers/registry.py`
- Modify: `web/backend/capabilities.py`

**Interfaces:**
- `parse_sina_jsonp(text: str) -> list[dict]` 只接受格式正确且唯一递增的 OHLCV 数据。
- `CSina` 实现 `CCommonStockApi` 的 `SetBasciInfo`, `get_kl_data`, `do_init`, `do_close` 生命周期接口。
- `SinaAdapter.fetch_klines(request, max_bars) -> list[CKLine_Unit]`，通过 `CSina` 生命周期获取分钟 K 线。
- `CSina` 通过 CChan custom source 字符串 `custom:SinaAPI.CSina` 调用。

- [ ] **Step 1: 写固定 JSONP fixture 解析测试**

至少覆盖有效行、缺少 `day` 或 OHLCV、重复时间、非递增行、`low > high`。错误行不得产生 `CKLine_Unit`。

- [ ] **Step 2: 运行 Sina 测试确认红灯**

Run: `.venv/bin/python -m pytest tests/web/backend/test_sina_api.py -q`
Expected: FAIL，解析器尚不存在。

- [ ] **Step 3: 实现纯 JSONP 解析函数**

从 JSONP 包装中提取 JSON 数组；验证每行必需字段、时间可解析、时间唯一递增、价格字段可转浮点且 `low <= open/close <= high`。把输入格式错误映射为 `SourceDataError`。

- [ ] **Step 4: 运行 parser fixture 测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_sina_api.py -q`
Expected: JSONP 正常 fixture 通过，五类不合法 fixture 按预期抛 `SourceDataError`。

- [ ] **Step 5: 写请求、覆盖范围和 custom source 测试**

Mock `requests.get` 测试 `symbol`, `scale=30`, `ma=no`, `datalen`, timeout 参数、请求区间筛选和超时映射。测试供应商返回空、请求开始时间早于首根可用 K 线、HTTP timeout 三种结果。另验证 `CChan(code="sh.000001", data_src="custom:SinaAPI.CSina", lv_list=[KL_TYPE.K_30M], config=CChanConfig({"trigger_step": True})).GetStockAPI()` 能加载 `CSina` 且不发网络请求。

- [ ] **Step 6: 运行请求测试确认红灯**

Run: `.venv/bin/python -m pytest tests/web/backend/test_sina_api.py -q`
Expected: FAIL，`CSina` 或 provider adapter 尚未实现。

- [ ] **Step 7: 实现 `CSina` 行情读取**

`CSina.get_kl_data()` 使用明确请求超时，通过 code、开始/结束日期和 `AUTYPE.NONE` 构造 `CKLine_Unit`；分钟 `CTime` 使用 `auto=False`。首根 K 线晚于请求开始日期时抛 `DateRangeUnavailableError`；网络 timeout 抛 `SourceTimeoutError`；不从 `output/*.json` 读取行情。

- [ ] **Step 8: 实现 SinaProvider 与能力注册**

`SinaAdapter.fetch_klines()` 完整消费 `CSina.get_kl_data()` 并限制最大 K 线数量。注册指数 30m 的 `source_id="sina"`、`chan_data_source="custom:SinaAPI.CSina"` 和 `KL_TYPE.K_30M` 映射；能力返回供应商实际可覆盖的日期范围。

- [ ] **Step 9: 运行 Sina 和 custom source 测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_sina_api.py tests/web/backend/test_provider_registry.py tests/web/backend/test_capabilities.py -q`
Expected: PASS；全部测试仅使用 JSONP fixture 与 mock HTTP。

- [ ] **Step 10: 提交 Sina 适配器**

```bash
git add DataAPI/SinaAPI.py web/backend/providers/sina.py web/backend/providers/registry.py web/backend/capabilities.py tests/web/backend/test_sina_api.py tests/web/backend/fixtures/sina_30m.jsonp
git commit -m "feat: add dynamic index intraday provider"
```

### Task 4: CChan 分析服务与图表序列化

**Files:**
- Modify: `Chan.py`
- Create: `web/backend/analysis_service.py`
- Create: `web/backend/serializers.py`
- Create: `tests/web/backend/test_chan_prefetched.py`
- Create: `tests/web/backend/test_serializers.py`
- Create: `tests/web/backend/test_analysis_service.py`
- Create: `tests/web/backend/conftest.py`
- Create: `tests/web/backend/fixtures/chan_bars.json`
- Modify: `web/backend/routes.py`

**Interfaces:**
- `CChan(..., defer_load: bool = False)` 保持原有默认行为；`defer_load=True` 时初始化内部结构但不在构造时读取行情，随后由 `trigger_load()` 接收预取的 K 线。
- `AnalysisService(registry, chan_factory=CChan, max_bars=5000).analyze(request: AnalysisRequest) -> ChartResponse`。
- `serialize_chan(chan: CChan, request: AnalysisRequest, source_id: str, kl_type: KL_TYPE) -> ChartResponse`。
- `map_analysis_error(error: Exception) -> ErrorResponse`，供应商和 `CChanException` 转成设计文档定义的错误码。

- [ ] **Step 1: 写 CChan 预取 K 线构造测试**

用固定 `CKLine_Unit` fixture 构造 `CChan(code="sh.000001", lv_list=[KL_TYPE.K_30M], config=CChanConfig(), defer_load=True)`；mock `GetStockAPI` 以确保构造期间不访问供应商。调用 `trigger_load({KL_TYPE.K_30M: klines})` 后验证 K 线数量、笔、线段和中枢由完整批处理计算得到。再验证默认构造路径仍会按原方式加载数据。

- [ ] **Step 2: 运行构造测试确认红灯**

Run: `.venv/bin/python -m pytest tests/web/backend/test_chan_prefetched.py -q`
Expected: FAIL，`CChan.__init__` 尚不接受 `defer_load`。

- [ ] **Step 3: 为 CChan 增加延迟加载参数**

在 `Chan.py` 给构造函数增加默认值为 `False` 的 `defer_load`；仅当 `defer_load=False` 且 `config.trigger_step=False` 时执行原来的自动 `load()`。这样预取场景可保留正常批处理配置，在 `trigger_load()` 结束时计算线段、中枢和买卖点。

- [ ] **Step 4: 运行预取构造测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_chan_prefetched.py -q`
Expected: PASS；默认加载行为不回归，预取路径不访问网络。

- [ ] **Step 5: 写 K 线和 MACD 序列化失败测试**

```python
from Common.CEnum import KL_TYPE
from web.backend.serializers import serialize_chan


def test_serializer_uses_klu_time_and_macd_values(fake_chan, analysis_request):
    result = serialize_chan(fake_chan, analysis_request, "fixture", KL_TYPE.K_30M)
    assert result.candles[0].time == "2026-09-01T10:00:00+08:00"
    assert result.indicators.macd[0].diff == 1.25
    assert result.meta.first_bar == result.candles[0].time
```

`conftest.py` 提供 `analysis_request`、含足够数据的确定性 `chan_bars.json`、用 `defer_load=True` 和真实 `CChan.trigger_load()` 构建的 `fixture_chan`，以及带固定 MACD 值的 `fake_chan`。fixture 测试确认真实引擎结果能序列化；fake 对象用于精确断言数值。验证日线零时按 `Asia/Shanghai` 输出，不依赖运行机器时区。

- [ ] **Step 6: 运行 K 线/MACD 测试，确认 serializer 不存在**

Run: `.venv/bin/python -m pytest tests/web/backend/test_serializers.py -q`
Expected: FAIL，`web.backend.serializers` 尚不存在。

- [ ] **Step 7: 实现 K 线和 MACD 序列化**

用 `chan[kl_type].klu_iter()` 遍历 K 线单元并输出 `time/open/high/low/close/volume`；分析服务使用已解析 provider 的 `period_to_kl_type(request.period)` 得到 `kl_type`。成交量从 `klu.trade_info.metric[DATA_FIELD.FIELD_VOLUME]` 读取。时间由 `CTime.year/month/day/hour/minute/second` 显式构造带 `ZoneInfo("Asia/Shanghai")` 的 `datetime`；不要使用系统本地时间戳转换。MACD 从 `klu.macd.DIF`、`klu.macd.DEA`、`klu.macd.macd` 输出。

- [ ] **Step 8: 运行 K 线/MACD serializer 测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_serializers.py -q`
Expected: PASS；上海偏移、OHLCV 和 MACD 数值与 fixture 一致。

- [ ] **Step 9: 写缠论覆盖层序列化失败测试**

用 fake `CChan` 图层对象覆盖一笔、线段、中枢、买点和卖点，验证使用结构端点 K 线的时间和价格，而不是把整数 x 索引输出给浏览器；同时验证 `bi_is_sure` 保持原值。

- [ ] **Step 10: 实现笔、线段、中枢和买卖点序列化**

笔使用 `CBi.get_begin_klu()`、`get_end_klu()`、`get_begin_val()`、`get_end_val()`；线段使用 `CSeg` 的对应取值方法；中枢使用 `begin`、`end`、`low`、`high`；买卖点遍历 `bs_point_lst.bsp_iter()` 与 `seg_bs_point_lst.bsp_iter()`，输出 `klu` 时间、`bi.get_end_val()` 价格、`is_buy` 方向、`type2str()` 类别和 `bi.is_sure`。

- [ ] **Step 11: 运行 serializer 和真实 CChan fixture 测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_serializers.py -q`
Expected: PASS；只用固定 fixture，不读取 `output/` 或访问网络。

- [ ] **Step 12: 写分析服务失败路径测试**

用 fake registry/provider 验证 unsupported period 时 `fetch_klines` 不被调用；验证日期超出 provider 边界和超过 5000 K 线时映射为 `DATE_RANGE_UNAVAILABLE`、`INVALID_REQUEST`；用空结果、供应商 timeout 和 `CChanException` 验证 `NO_DATA`、`SOURCE_TIMEOUT`、`ANALYSIS_ERROR`。成功路径使用实际末根 K 线早于请求结束日的 fixture，验证 `meta.last_bar` 等于数据源实际时间且不会补齐到请求结束日。另验证错误响应不含 traceback。

- [ ] **Step 13: 运行分析服务测试确认失败**

Run: `.venv/bin/python -m pytest tests/web/backend/test_analysis_service.py -q`
Expected: FAIL，`AnalysisService` 尚未实现。

- [ ] **Step 14: 实现分析编排和错误映射**

用 `registry.resolve()` 校验能力，再在 `registry.guard(provider)` 内调用 `provider.fetch_klines(request, max_bars=5000)`。空数据映射为 `NO_DATA`，超过 5000 根映射为 `INVALID_REQUEST`，越过供应商范围映射为 `DATE_RANGE_UNAVAILABLE`。由 provider 得到 `kl_type` 和 `autype`；创建 `CChan(code=request.instrument, lv_list=[kl_type], config=CChanConfig(), autype=autype, defer_load=True)`，再调用 `trigger_load({kl_type: klines})`，保持引擎原有完整批处理计算笔、线段、中枢和买卖点。`map_analysis_error()` 将异常转为稳定错误码和安全文案，由 API 路由返回对应 `ErrorResponse`；未预期错误记完整服务日志但不向网页返回 traceback。

- [ ] **Step 15: 接入 API 并运行服务层测试**

Run: `.venv/bin/python -m pytest tests/web/backend/test_chan_prefetched.py tests/web/backend/test_schemas.py tests/web/backend/test_api.py tests/web/backend/test_serializers.py tests/web/backend/test_analysis_service.py -q`
Expected: PASS；用 `chan_factory` 替身验证 API 不需要外网。

- [ ] **Step 16: 提交分析和序列化层**

```bash
git add Chan.py web/backend/analysis_service.py web/backend/serializers.py web/backend/routes.py tests/web/backend
git commit -m "feat: serialize chan analysis for web charts"
```

### Task 5: 前端项目、查询表单和 API 状态

**Files:**
- Create: `web/frontend/package.json`
- Create: `web/frontend/package-lock.json`
- Create: `web/frontend/index.html`
- Create: `web/frontend/vite.config.ts`
- Create: `web/frontend/tsconfig.json`
- Create: `web/frontend/src/main.ts`
- Create: `web/frontend/src/App.vue`
- Create: `web/frontend/src/api/client.ts`
- Create: `web/frontend/src/api/types.ts`
- Create: `web/frontend/src/api/client.spec.ts`
- Create: `web/frontend/src/components/QueryForm.vue`
- Create: `web/frontend/src/components/ChartStatus.vue`
- Create: `web/frontend/src/components/QueryForm.spec.ts`

**Interfaces:**
- `fetchCapabilities(market: string): Promise<CapabilityResponse>`。
- `searchInstruments(market: string, query: string): Promise<InstrumentOption[]>`。
- `analyzeChart(request: AnalysisRequest): Promise<ChartResponse>`。
- `QueryForm` 发出 `submit(request: AnalysisRequest)`，且仅在用户提交时发出。

- [ ] **Step 1: 写表单行为测试**

测试初始 capability 加载、标的名称/代码搜索、市场切换后清空旧标的、周期选项跟随 capability、开始日期晚于结束日期时禁止提交、点击“分析”只发送一次请求。`client.spec.ts` 验证 API 路径、snake_case 请求/响应字段映射和稳定错误结构。

```typescript
it('submits only after an explicit click', async () => {
  const wrapper = mount(QueryForm, { props: { capabilities: fixtureCapabilities } })
  expect(wrapper.emitted('submit')).toBeUndefined()
  await wrapper.get('button[type="submit"]').trigger('click')
  expect(wrapper.emitted('submit')).toHaveLength(1)
})
```

- [ ] **Step 2: 安装前端测试脚手架并确认红灯**

在 `web/frontend/package.json` 加入 Vue 3、ECharts、Vite、TypeScript、Vitest、Vue Test Utils、jsdom、`vue-tsc` 与 Playwright；定义 `dev`, `build`, `test:unit` 和 `test:e2e` scripts。用 `npm --prefix web/frontend install` 生成 lockfile；首次运行 E2E 前执行 `npm --prefix web/frontend exec -- playwright install chromium` 安装浏览器，再运行 `npm --prefix web/frontend run test:unit -- --run`，预期因组件缺失而失败。

- [ ] **Step 3: 实现共享类型和 API 客户端**

`types.ts` 定义匹配 Pydantic JSON 的 snake_case wire types 和 camelCase 页面类型；`client.ts` 集中编码/解码字段。API 客户端使用同源 `/api/v1`，把错误响应转换成含 `code/message/supportedOptions` 的 `ApiError`；网络断开时显示“无法连接本机分析服务”。

- [ ] **Step 4: 实现 Vue 查询表单和状态组件**

`QueryForm.vue` 展示市场、搜索建议、周期、日期和复权控件；控件值来自 capabilities。未获取能力时禁用提交。`ChartStatus.vue` 表示初始、加载、空结果和错误信息。App 保存最后一次成功响应，提交期间禁用重复分析。

- [ ] **Step 5: 运行前端单元测试并提交**

Run: `npm --prefix web/frontend run test:unit -- --run`
Expected: PASS；测试只使用本地 mock API。

```bash
git add web/frontend/package.json web/frontend/package-lock.json web/frontend/index.html web/frontend/vite.config.ts web/frontend/tsconfig.json web/frontend/src

git commit -m "feat: add web chart query interface"
```

### Task 6: ECharts 缠论图层与交互

**Files:**
- Create: `web/frontend/src/chart/buildChartOption.ts`
- Create: `web/frontend/src/chart/ChartView.vue`
- Create: `web/frontend/src/chart/buildChartOption.spec.ts`
- Create: `web/frontend/src/components/LayerToggles.vue`
- Modify: `web/frontend/src/App.vue`

**Interfaces:**
- `buildChartOption(response: ChartResponse, visibleLayers: LayerVisibility): EChartsOption`。
- `LayerVisibility` 含 `bi`, `segments`, `zones`, `buySellPoints`, `macd` 五个布尔值。
- `ChartView` 接收 `response` 和 `visibleLayers`，事件监听器在组件卸载时销毁图表实例。

- [ ] **Step 1: 写图表选项测试**

```typescript
it('maps OHLC in ECharts candle order and uses response times', () => {
  const option = buildChartOption(fixtureResponse, allLayersVisible)
  const candles = option.series.find((series) => series.id === 'candles')
  expect(candles.data[0]).toEqual([10, 12, 9, 13])
  expect(option.xAxis[0].data[0]).toBe('2026-09-01T10:00:00+08:00')
})
```

`fixtureResponse` 和 `allLayersVisible` 在测试文件内直接定义，图表 builder 固定主 series ID 为 `candles`，`xAxis` 固定为数组。

再验证笔和线段坐标使用 DTO 的起止时间/价格，中枢上下界正确，买卖点类别可见，关闭图层时相应 series 被隐藏，MACD 数组长度与 K 线一致，option 含 `dataZoom` 和十字线 `axisPointer` 配置。

- [ ] **Step 2: 运行测试确认图表 option 构造器缺失**

Run: `npm --prefix web/frontend run test:unit -- --run`
Expected: 新图表测试因 `buildChartOption` 不存在失败。

- [ ] **Step 3: 实现 K 线、覆盖层和 MACD option 构造器**

构造 K 线主 series 和 MACD 下方 grid。蜡烛数据按 ECharts 顺序 `[open, close, low, high]` 传入。笔/线段为带端点时间和价格的折线覆盖层，中枢为上下界区域，买卖点为散点 marker。颜色采用 A 股常用红涨绿跌。加入 `dataZoom`、`axisPointer` 十字线和统一 tooltip。

- [ ] **Step 4: 实现图层开关与图表组件生命周期**

`LayerToggles.vue` 控制五个显示层，不发新的分析请求。`ChartView.vue` 初始化 ECharts、窗口 resize 时调用 resize、响应或图层变化时更新 option、卸载时 dispose。

- [ ] **Step 5: 运行图表单测和前端构建**

Run: `npm --prefix web/frontend run test:unit -- --run && npm --prefix web/frontend run build`
Expected: PASS；TypeScript/Vite 构建成功。

- [ ] **Step 6: 提交图表层**

```bash
git add web/frontend/src/chart web/frontend/src/components/LayerToggles.vue web/frontend/src/App.vue

git commit -m "feat: render interactive chan chart layers"
```

### Task 7: 本机同源运行、端到端验收和使用说明

**Files:**
- Create: `web/backend/static_app.py`
- Create: `web/__main__.py`
- Create: `web/README.md`
- Create: `web/frontend/playwright.config.ts`
- Create: `tests/web/e2e/chart-page.spec.ts`
- Create: `tests/web/e2e/fixtures/chart-response.json`
- Modify: `web/frontend/vite.config.ts`
- Modify: `web/backend/app.py`
- Modify: `.gitignore`

**Interfaces:**
- `python -m web` 启动 FastAPI 于 `127.0.0.1`，本机页面路径为 `/`，API 路径为 `/api/v1/...`。
- 开发时 Vite 代理 `/api` 到 FastAPI；生产构建输出挂载到同一 FastAPI 应用。

- [ ] **Step 1: 写端到端页面场景**

Playwright 配置 `webServer.cwd` 为仓库根目录、`webServer.command=".venv/bin/python -m web"` 和 `baseURL="http://127.0.0.1:8765"`，并写测试 mock `/api/v1/capabilities`, `/api/v1/instruments`, `/api/v1/analysis`。测试从搜索标的、选周期/日期、提交分析到 K 线和笔图层出现；再让 analysis 返回 `NO_DATA`，验证表单保留且错误可读。

- [ ] **Step 2: 运行端到端测试确认本机启动入口缺失**

Run: `npm --prefix web/frontend run test:e2e`
Expected: FAIL，生产入口和静态文件服务尚未实现。

- [ ] **Step 3: 配置 Vite 开发代理**

开发 server 将 `/api` 代理到 `127.0.0.1:8765`；生产构建输出 `web/frontend/dist`。运行 `npm --prefix web/frontend run build` 并检查构建成功。

- [ ] **Step 4: 挂载生产静态文件**

`static_app.py` 只在 `web/frontend/dist` 存在时挂载静态文件，并为 `/` 返回 `index.html`；没有构建产物时 API 测试仍可启动。

- [ ] **Step 5: 实现本机启动入口**

`web/__main__.py` 用 Uvicorn 启动 `web.backend.app:app`，固定监听 `127.0.0.1:8765`，不接受 `0.0.0.0` 覆盖。

- [ ] **Step 6: 编写运行说明**

`web/README.md` 说明 Python Web 可选依赖安装、`npm --prefix web/frontend ci`、`npm --prefix web/frontend exec -- playwright install chromium`、`npm --prefix web/frontend run build`、`.venv/bin/python -m web`、支持数据源/周期、Sina 覆盖范围、错误排查和本机 URL。基础 `Script/requirements.txt` 不加入 Web 专属依赖。

- [ ] **Step 7: 运行完整自动检查**

Run: `.venv/bin/python -m pytest tests/web -q && npm --prefix web/frontend run test:unit -- --run && npm --prefix web/frontend run build && npm --prefix web/frontend run test:e2e`
Expected: 全部测试通过，构建产物可由 FastAPI 同源读取；测试请求不访问真实行情。

- [ ] **Step 8: 本机人工验收实际行情**

运行 `.venv/bin/python -m web`，浏览器查询一个 A 股股票日线、一个指数周线和一个由能力接口报告支持的指数 30m 区间。对比 API `meta` 与 K 线首末时间、缩放、十字线、每个图层开关和错误状态。此验收产生的临时行情、PNG 和日志不加入 Git。

- [ ] **Step 9: 提交本机运行入口和验收说明**

```bash
git add web/backend/static_app.py web/__main__.py web/README.md web/frontend/vite.config.ts web/backend/app.py tests/web/e2e .gitignore

git commit -m "feat: serve chan chart web app locally"
```

## Self-Review Checklist

- Spec 第 1 节成功标准由 Task 4–7 的 API、交互图表和端到端验收覆盖。
- Spec 第 2–3 节范围和技术选择由 Task 1、2、3、5、6、7 覆盖；没有账号、回测或实时行情实现任务。
- Spec 第 4–5 节组件和页面交互由 Task 1–7 覆盖。
- Spec 第 6 节 API、时间、价格、覆盖层和错误 DTO 由 Task 1–4 覆盖。
- Spec 第 7–8 节动态数据源、BaoStock 锁、资源限制与错误日志由 Task 2–4 覆盖。
- Spec 第 9–10 节验证和实施顺序由各任务独立测试、端到端测试和人工验收覆盖。
- 每个 Review Focus 风险都有对应 Task 2、3 或 4 的 fixture/并发测试。
- 类型、函数名和路由在全计划中保持一致；每项工作都落在任务文件清单中，并给出测试、命令或验收结果。
