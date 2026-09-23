# 网页端缠论图表设计

日期：2026-09-23

状态：待用户审阅

项目：chan.py

## 1. 目标

为 chan.py 增加一个个人本机使用的浏览器应用。用户选择 A 股股票或指数、周期和历史日期范围，服务端获取行情并运行现有缠论引擎，浏览器呈现可缩放的 K 线图及缠论结构。

成功标准：

- 用户能按名称或代码查找受支持的标的，选择该标的支持的周期与日期范围并提交分析。
- 图表的 K 线、笔、线段、中枢、买卖点和 MACD 均对应到正确的时间和价格。
- 界面显示实际取得的数据范围；不支持的周期、无行情和数据源错误均显示可读原因。
- 用户能缩放和拖动时间轴、使用十字线查看行情，并独立开关图层。

## 2. 首版范围与假设

- 面向个人本机使用，服务监听 `127.0.0.1`；不提供登录和远程多人访问。
- 初始标的范围为 A 股股票和指数。加密货币、回测、实时推送、扫描器和云部署不在首版范围。
- 历史数据周期至少覆盖日线、周线和 30 分钟线中由数据源实际支持的组合。服务端返回能力矩阵，前端不允许提交不支持的组合。
- 首版保留现有可用数据源。当前示例中的指数 30 分钟数据保存在静态 JSON；为了支持任意标的和日期，需要增加动态指数分钟线适配器。优先将现有 Sina 数据接入方式封装成适配器，并由能力接口报告实际支持范围。
- 股票复权方式由数据源能力决定；指数不提供复权选项。日期和时间统一按 `Asia/Shanghai` 解释，并在响应中明确时区。
- 首版采用稳定的默认 `CChanConfig`，不让网页提交任意内部参数；图层开关只影响展示。高级缠论参数编辑可另行设计。
- 缠论计算按单周期进行；多级别联立图表不属于首版目标。

## 3. 方案选择

采用 FastAPI 服务端、Vue 3 + TypeScript + Vite 前端、Apache ECharts 图表。前端打包后由 FastAPI 同源提供静态文件和 API。

本仓库已有 Python `CChan` 引擎及 BaoStock、AkShare、CCXT 适配器，没有网页应用。现有 `CPlotDriver` 使用 Matplotlib 生成静态图，不能提供网页需要的拖动、缩放、十字线和图层交互。因此网页从服务端取得结构化图表数据并自行绘制；`CPlotDriver` 保持现有用途。

Streamlit 可更快做出 Python 原型，但复杂 K 线与图层交互需要自定义组件，长期边界不如独立网页清楚。只在网页显示 Matplotlib 图片不能满足交互需求。

## 4. 组件与职责

```text
web/
  backend/
    app.py                 FastAPI 应用、静态网页挂载、错误映射
    routes.py              能力、标的搜索、图表分析 API
    schemas.py             请求和响应的数据契约
    capabilities.py        数据源能力与标的目录
    analysis_service.py    校验、取数、创建 CChan、组织分析流程
    serializers.py         将 CChan 输出转换为版本化图表 DTO
    providers/              数据源适配器及其适配测试
  frontend/
    src/                   Vue 页面、表单、API 客户端、图表组件
    dist/                  Vite 构建输出，由 FastAPI 提供
```

- `capabilities` 为前端提供市场、标的、周期、复权方式和可用日期信息。当前 `DataAPI` 主要提供行情接口，没有完整统一的标的搜索和能力接口；新增目录层，不把供应商差异散落在 UI 中。
- `analysis_service` 每次请求创建独立 `CChan` 实例，不复用可变分析结果。
- `providers` 统一数据源的初始化、关闭、标的查找、周期支持、日期限制和 K 线读取行为。
- `serializers` 只依赖缠论结果对象，不依赖 Matplotlib 绘图元数据，避免 API 与 `CPlotDriver` 内部表示耦合。

## 5. 页面交互

页面顶部为参数表单：市场、标的搜索、周期、起止日期、复权方式和“分析”按钮。标的搜索接受代码或名称；在选择市场和标的后，周期及复权选项依据 `/capabilities` 返回值更新。日期控件遵守数据源返回的范围。需要用户显式点击“分析”，改动表单时不自动重复联网和计算。

分析期间禁用重复提交并显示加载状态。结果显示实际首末 K 线日期、K 线数量和数据源。图表主体绘制 K 线、笔、线段、中枢和买卖点；MACD 显示在下方独立窗格。用户可开关图层、缩放或拖动时间轴，并用十字线查看 K 线与指标数值。

状态至少包括初始提示、加载、成功、无数据、请求校验错误、数据源超时或错误、缠论计算错误。错误区域保留当前表单内容并提供可理解的修正办法。

## 6. API 契约

所有接口使用 `/api/v1` 前缀，同源 JSON。

### 能力和标的搜索

- `GET /api/v1/capabilities`：返回市场、数据源、标的类别、周期、复权选项及日期边界。周期能力按“市场 + 数据源 + 标的 + 周期”组合描述。
- `GET /api/v1/instruments?market=cn&q=...`：返回匹配项的规范代码、名称、交易所和标的类别。

### 分析

`POST /api/v1/analysis` 请求包含：

```json
{
  "market": "cn",
  "instrument": "sh.000001",
  "period": "30m",
  "begin_time": "2026-06-01",
  "end_time": "2026-09-23",
  "adjustment": "none"
}
```

具体值由能力接口定义。服务端先校验代码、数据源/周期兼容性、日期顺序、日期范围和最大 K 线数量，再读取行情和执行缠论计算。首版同步返回结果；不增加任务队列和 WebSocket。

响应包含 `schema_version`、规范化的请求、实际数据源、实际首末 K 线时间、K 线数量、K 线数组、MACD 数组及缠论覆盖层。时间用带 `+08:00` 的 ISO 8601 字符串，OHLCV 为数值。

```json
{
  "schema_version": 1,
  "meta": {
    "instrument": "sh.000001",
    "period": "30m",
    "source": "sina",
    "first_bar": "2026-06-01T10:00:00+08:00",
    "last_bar": "2026-09-22T15:00:00+08:00",
    "bar_count": 500
  },
  "candles": [],
  "indicators": {"macd": []},
  "overlays": {
    "bi": [],
    "segments": [],
    "zones": [],
    "buy_sell_points": []
  }
}
```

字段定义如下：

| 对象 | 必需字段 |
|---|---|
| K 线 | `time`, `open`, `high`, `low`, `close`, `volume` |
| MACD | `time`, `diff`, `dea`, `histogram` |
| 笔/线段 | `start_time`, `start_price`, `end_time`, `end_price`, `direction` |
| 中枢 | `start_time`, `end_time`, `lower`, `upper` |
| 买卖点 | `time`, `price`, `side`, `type`, `bi_is_sure` |

覆盖层的线结构以起止时间和起止价格表示；中枢以开始/结束时间和上/下边界表示；买卖点含时间、价格、方向、类别及所属笔确认状态。买卖点的笔确认状态不等于该信号不会变化，UI 标签应表达这一点。

错误响应使用稳定的 `code`、用户可读 `message` 和可选的 `supported_options`。首版错误码至少包含 `INVALID_REQUEST`、`UNSUPPORTED_PERIOD`、`DATE_RANGE_UNAVAILABLE`、`NO_DATA`、`SOURCE_TIMEOUT`、`SOURCE_ERROR` 和 `ANALYSIS_ERROR`。响应不得将 Python traceback 暴露给网页。

## 7. 数据源、并发与资源限制

BaoStock、AkShare 和新增的指数分钟线适配器按能力矩阵选用。用户界面只展示服务端报告的有效组合；不能从静态快照推断动态查询能力。BaoStock 当前连接状态是类级共享的，首版服务在 BaoStock 请求周围使用锁并限制同时分析请求，避免并发登录/退出冲突。每个分析都创建独立 `CChan` 对象。

首版限制最大日期跨度/返回 K 线数量，具体边界按供应商限制确定并通过 capabilities 告知前端。不持久化用户历史，不加 Redis、数据库或后台作业队列。行情缓存暂不作为正确性依赖；后续可增加带 TTL 的数据缓存。

V1 运行只绑定本机回环地址。将来开放局域网或公网前，需要单独设计认证、跨用户隔离、并发限制、作业队列和部署安全。

## 8. 错误处理与可观测性

- 参数校验失败在取数前返回 `INVALID_REQUEST` 或 `UNSUPPORTED_PERIOD`。
- 供应商返回空序列时为 `NO_DATA`；网络超时和供应商失败分别返回 `SOURCE_TIMEOUT` 和 `SOURCE_ERROR`。
- `CChanException` 及未预期计算错误映射成用户可读的 `ANALYSIS_ERROR`，服务端日志记录完整异常。
- 服务日志记录请求市场/代码/周期、耗时、数据源、返回 K 线数量和错误码；不记录无关环境信息。
- 响应中的实际范围和数量始终按数据源返回的 K 线计算，不按用户请求区间伪造。

## 9. 验证方案

- 数据源合同测试：能力列表、标的目录和 K 线范围能被统一适配；不支持的周期明确拒绝。
- 序列化单元测试：使用固定 K 线 fixture 验证笔、线段、中枢、买卖点及 MACD 的时间、价格和类型正确。
- API 测试：覆盖成功、无数据、无效日期、超范围、周期不支持、供应商超时及错误响应结构。
- 前端测试：表单选项跟随能力接口变化；图层切换只影响显示；加载和错误状态正确；图表缩放与十字线可操作。
- 本机验收：运行服务、搜索一个 A 股标的和一个指数，分别选择日线/周线及支持的 30m 区间，确认结果日期和图表元素与分析摘要一致。

## 10. 实施顺序

1. 建立 web 后端骨架、请求/响应模型和数据源能力目录；用 fixture 跑通序列化和 API。
2. 为现有股票/指数数据源接入标的目录和动态 K 线接口；补齐指数 30m 动态适配器及日期分页/范围约束。
3. 实现 Vue 参数表单、ECharts K 线及缠论覆盖层，将响应 DTO 渲染到图表。
4. 完成 API/前端测试、本机端到端验收、运行说明和依赖更新。

本设计阶段只定义产品和架构，不包含实现、部署、实时行情、回测或多用户服务。实现计划须在用户审阅并批准本设计文档后另行编写。

## 11. 参考资料

- [FastAPI concurrency and async/await](https://fastapi.tiangolo.com/async/)
- [Apache ECharts options](https://echarts.apache.org/en/option.html)
- [Vue with TypeScript](https://vuejs.org/guide/typescript/overview)
- 项目现有数据源与绘图记录：`DataAPI/`、`CHARTING_NOTES.md`
