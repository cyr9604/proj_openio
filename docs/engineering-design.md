# A股 520 均线分析系统 - 工程设计文档

## 1. 项目概述

全栈 A 股技术分析系统，基于 5 日/20 日移动均线（520 策略）实现趋势判断、买卖信号检测、回测验证和风险提示。支持 Windows/Linux/Docker 部署。

---

## 2. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (React + TS)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │StockSearch│ │WatchList │ │KLineChart│ │BacktestPanel   │  │
│  │Watchlist  │ │GoldenCross│ │Analysis  │ │SettingsPanel   │  │
│  │SignalPanel│ │Screen    │ │Panel     │ │ProviderStatus  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│                      API Client (api/client.ts)              │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP REST (proxy /api -> :8000)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI + Python)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Routers  │ │ Strategy │ │Providers │ │  Config/Schema  │  │
│  │ stocks   │ │ engine   │ │ manager  │ │  database       │  │
│  │ watchlist│ │ signals  │ │ baostock │ │  models         │  │
│  │ analysis │ │ backtest │ │ efinance │ │  schemas        │  │
│  │ backtest │ │ registry │ │ akshare  │ │                │  │
│  │ strategies│ │          │ │ sina     │ │  SQLite         │  │
│  │ providers│ │          │ │ ths_http │ │  config.json    │  │
│  │ settings │ │          │ │ ths_sdk  │ │                │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | React 18 + TypeScript |
| UI 组件 | Ant Design 5.x |
| 图表 | ECharts 5.x + echarts-for-react |
| 路由 | react-router-dom v6 |
| 后端框架 | Python 3.12 + FastAPI + Uvicorn |
| 数据库 | SQLite + SQLAlchemy 2.0 (WAL 模式) |
| 数据源 | Baostock / Efinance(东方财富) / AKShare / 新浪财经 / 同花顺 HTTP API / 同花顺 iFinD SDK |
| 容器化 | Docker (multi-stage build) + docker-compose |

---

## 3. 后端模块详解

### 3.1 入口与基础设施

#### `main.py` (入口)
- 创建 `FastAPI` 实例，注册 CORS 中间件（允许所有来源）
- 注册 7 个路由模块：`stocks`, `watchlist`, `analysis`, `backtest`, `strategy_router`, `providers`, `settings`
- 启动时调用 `init_db()` 初始化数据库表
- 生产环境下（Docker）挂载 `frontend/dist` 静态目录，处理 SPA 路由回退

#### `config.py` (配置管理)
- `ProviderConfig` 类管理 `config.json` 的读写
- 字段：`priority` (数据源优先级队列，默认 `["baostock", "efinance", "ths_http", "ths_sdk", "sina", "akshare"]`)、`ths_http_token`、`ths_http_refresh_token`、`ths_sdk_enabled`、`default_adjust` (默认复权方式)
- 提供 `update(**kwargs)` 方法更新属性后自动调用 `save()` 持久化到 `config.json`
- 对外暴露单例 `settings = ProviderConfig()`

#### `database.py` (数据库引擎)
- 基于 SQLAlchemy 创建 SQLite 引擎，连接参数 `check_same_thread=False`
- 连接时设置 WAL 模式 + NORMAL 同步（读写并发优化）
- 提供 `get_db()` 生成器供 FastAPI 依赖注入使用
- `init_db()` 创建所有 ORM 模型表

#### `models.py` (ORM 模型)
- **`DailyQuote`**: 日线行情表（symbol, trade_date, open/high/low/close, volume, amount, source, adjusted）
- **`Watchlist`**: 自选股表（symbol 唯一约束, name, added_at）
- **`BacktestResult`**: 回测结果表（symbol, 日期范围, 初始资金, 收益率/年化/最大回撤/胜率/交易次数, details JSON）
- **`StockInfo`**: 股票基本信息表（symbol, name, exchange）

#### `schemas.py` (Pydantic 模型)
- 定义所有 API 请求/响应的序列化模型
- 关键：`AnalysisResponse`（含 trend/signals/position/risk/chart_data）、`BacktestRequest`（含 fee_rate/min_fee 自定义费用参数）、`BacktestResponse`（含 trades/equity_curve）、`FullScanStatus`（含扫描进度/结果）

---

### 3.2 Providers 数据源层

设计模式：**抽象策略模式**，支持多数据源自动故障转移。

#### `providers/base.py` (抽象基类)
- `QuoteProvider` 定义三个抽象方法：`fetch_daily()`, `is_available()`, `is_configured()`
- 提供 `normalize()` 方法统一列名（date→trade_date）、类型转换、排序去重
- `ProviderError` 自定义异常携带 provider 名称

#### `providers/manager.py` (提供者管理器)
- 注册 6 个提供者：`baostock`, `efinance`, `sina`, `akshare`, `ths_http`, `ths_sdk`
- **`fetch_daily()` 核心流程**：
  1. 查询 SQLite 缓存 → 若最新缓存日期 >= 请求结束日期则直接返回
  2. 按 `settings.priority` 配置的顺序轮询各数据源
  3. 任一数据源成功则返回数据并调用 `_save_to_db()` 写回缓存
  4. 全部失败则回退到缓存数据；无缓存则抛出异常
- `_save_to_db()`: 逐行写入 `DailyQuote`，按 symbol+date+adjusted 去重
- `get_cached_daily()`: 按 symbol+adjusted+日期范围查询本地缓存

#### `providers/baostock_provider.py` (Baostock 数据源)
- 调用 `baostock.query_history_k_data_plus()` 获取日线数据
- 支持沪/深/京交易所代码转换（6→sh, 0/3→sz, 8/4→bj）
- 免费可用，无需额外配置，需登录/登出

#### `providers/efinance_provider.py` (Efinance/东方财富数据源)
- 调用 `ef.stock.get_quote_history()` 获取日线数据
- 支持前复权/后复权/不复权（映射为 qfq/hfq/空字符串）
- 免费可用，无需配置

#### `providers/akshare_provider.py` (AKShare 数据源)
- 调用 `ak.stock_zh_a_hist()` 获取日线数据
- 支持前复权/后复权/不复权（映射为 qfq/hfq/空字符串）
- 免费可用，无需配置

#### `providers/sina_provider.py` (新浪财经数据源)
- 调用新浪财经 JSON API，支持沪/深/京交易所代码转换（6→sh, 0/3→sz, 8/4→bj）
- 使用 `httpx` 请求，无认证，可用性高

#### `providers/ths_http_provider.py` (同花顺 HTTP API)
- 需配置 `refresh_token`，自动刷新 `access_token`
- 调用 `quantapi.10jqka.com.cn` 的 token/refresh 和 quote/daily 接口
- 支持三种复权方式

#### `providers/ths_ifind_provider.py` (同花顺 iFinD SDK)
- 需启用 `ths_sdk_enabled` 配置项，且本机安装 iFinD 环境
- 通过 `THS.iFinD.THS_iFinDData()` 获取数据

---

### 3.3 Strategy 策略层

#### `strategy/registry.py` (策略注册表)
- 定义系统所有可用回测策略的元数据，当前内置 `ma520`（MA520均线策略）
- 每个策略包含：名称、描述、买入规则列表、卖出规则列表、加仓规则列表
- 每条规则含：类型标签、触发条件、执行动作、优先级
- 导出函数 `get_all_strategies()` 和 `get_strategy_detail(name)`
- 设计为可扩展注册表，新增策略只需在 `STRATEGIES` 字典中添加条目

#### `strategy/engine.py` (策略引擎)
**核心类 `StrategyEngine`**，接收 DataFrame 并计算：
- **技术指标**: MA5, MA20, MA20 斜率, 5日均量, 量比, EMA12, EMA26, MACD
- **方法**:
  - `get_trend()`: 根据 MA20 斜率判断趋势（up/down/flat），阈值 ±0.5%
  - `get_signals()`: 委托 `SignalDetector.detect_all()` 返回最新买卖信号
  - `get_historical_signals()`: 委托 `SignalDetector.scan_history()` 返回全历史信号（去重）
  - `get_position_advice()`: 综合趋势+信号给出仓位建议（0%~50%），包含中文说明
  - `get_risk_warning()`: 基于止损信号/趋势方向评估风险等级（low/medium/high）
  - `to_chart_data()`: 转换图表数据（含 MA5/MA20）
  - `analyze()`: 聚合输出完整 `AnalysisResponse`

#### `strategy/signals.py` (信号检测)
**核心类 `SignalDetector`**，实现 7 个检测方法，产 10 种信号类型：

| 信号类型 | 方法 | 逻辑 |
|---|---|---|
| `golden_cross` 金叉 | `_detect_golden_cross()` | MA5 上穿 MA20，附加条件：20日线向上、量比≥1.5、股价站上20日线 |
| `pullback` 回踩 | `_detect_pullback()` | 金叉后10日内缩量回踩20日线（偏离0~3%），带量站上5日线 |
| `convergence` 均线粘合 | `_detect_convergence()` | 近10日 MA5/MA20 间距均值<1.5%，放量突破前期高点 |
| `macd_plus` MACD+ | `_detect_macd_plus()` | MACD 由负转正（零轴上方确认） |
| `combined_gc_macd` 共振 | `_detect_combined_gc_macd()` | 5日内金叉+MACD+同时出现，强买入信号 |
| `stop_loss_ma5` 跌破MA5止损 | `_detect_stop_loss()` | 连续3日收盘跌破MA5（价格低于买入价） |
| `stop_loss_ma20` 放量破MA20止损 | `_detect_stop_loss()` | 放量跌破MA20，无条件清仓 |
| `death_cross` 死叉 | `_detect_take_profit()` | MA5 下穿 MA20，强势趋势结束 |
| `take_profit_mini` 最小止盈 | `_detect_take_profit()` | 盈利3%~5%时收盘价跌破MA20，锁定利润 |
| `take_profit_normal` 常规止盈 | `_detect_take_profit()` | 盈利达10%~20% |

- `scan_history()`: 回放全量历史数据，每日增量检测信号，`_deduplicate_consecutive()` 去重

#### `strategy/backtest.py` (回测引擎)
**核心类 `BacktestEngine`**，模拟 520 策略的逐日交易：
- 接收 `BacktestRequest` 中的 `strategy` 字段（当前仅支持 `ma520`，为未来多策略扩展预留）
- **买入规则**（按优先级）：
  1. 金叉+MACD+共振 → 半仓 (50%)
  2. 金叉（放量+向上趋势+站上均线）→ 3成仓
  3. 回踩买入（缩量+带量站上5日线）→ 3成仓
  4. 粘合发散 → 4成仓
  5. **禁止买入**: 20日线向下或走平
- **卖出规则**：
  1. 止盈 10%~20%
  2. 死叉
  3. 连续3日跌破 MA5
  4. 放量跌破 MA20
- **加仓逻辑**: 盈利状态下趋势向上，加仓2成（上限50%）
- **费用**: 支持自定义费率 (`fee_rate`) 和保底费用 (`min_fee`)，计算公式 `fee = max(成交金额 × fee_rate, min_fee)`，默认万分之2.5保底5元
- **输出**: `BacktestResponse`（资产曲线、交易记录、总收益率/年化/最大回撤/胜率）

---

### 3.4 Routers API 路由

#### `routers/stocks.py` — 股票搜索与金叉扫描
- `GET /api/stocks/search?q=` — 股票搜索（优先东方财富 → AKShare → 本地DB）
- `GET /api/stocks/golden-cross` — 缓存扫描（遍历本地有缓存的股票，近30天数据，检测金叉+共振信号）
- `POST /api/stocks/golden-cross/full-scan` — 启动全量扫描（异步线程，每只股票拉取近30天，检测 golden_cross 和 combined_gc_macd 两种信号）
- `GET /api/stocks/golden-cross/full-scan/{scan_id}` — 获取扫描进度/结果
- `POST ...pause`, `...resume`, `...seek?index=` — 暂停/继续/跳转扫描
- `GET ...exists` — 检查扫描是否存在
- 全量扫描使用 `threading.Thread` + `_ScanState` 状态对象管理进度/暂停/跳转；扫描结果返回 `GoldenCrossItem` 含 `signal_type` 字段

#### `routers/watchlist.py` — 自选股管理
- `GET /api/watchlist` — 列出所有自选股
- `POST /api/watchlist` — 添加自选股（按 symbol 去重）
- `DELETE /api/watchlist/{symbol}` — 删除自选股
- `GET /api/watchlist/signals` — 获取自选股近3天信号（遍历执行分析，过滤≥3天内的信号）

#### `routers/analysis.py` — 个股分析
- `GET /api/analysis/{symbol}?start=&end=&adjust=forward` — 完整分析（趋势+信号+仓位+风险+图表数据）

#### `routers/backtest.py` — 回测
- `POST /api/backtest` — 运行回测（数据拉取 → 策略模拟 → 结果持久化；请求体含 `strategy`、`fee_rate`、`min_fee` 等参数）
- `GET /api/backtest/history` — 历史回测列表（最近20条）
- `GET /api/backtest/history/{id}` — 回测详情（含完整交易记录）

#### `routers/backtest.py` — `strategy_router` 策略接口
- `GET /api/strategies` — 列出所有可用策略（名称+简介）
- `GET /api/strategies/{name}` — 获取策略详情（含买入/卖出/加仓规则列表）

#### `routers/providers.py` — 数据源状态
- `GET /api/providers/status` — 各数据源可用性/配置状态

#### `routers/settings.py` — 系统配置
- `GET /api/settings/provider` — 获取配置（refresh_token 掩码显示）
- `POST /api/settings/provider` — 保存配置（更新并持久化 config.json）

---

## 4. 前端模块详解

### 4.1 入口与基础架构

- **`main.tsx`**: React 入口，渲染 `<App />`
- **`App.tsx`**: 路由布局，含 Ant Design 顶部导航（首页/配置），`AppLayout` 内注册路由
  - `/` → `HomePage`，`/settings` → `SettingsPage`
  - 提供 `handleAddWatchlist` 回调给子组件
  - 注：`AnalysisPage.tsx` 是独立页组件但当前路由未引用，分析功能通过 HomePage 右侧面板实现
- **`types/index.ts`**: 全部 TypeScript 接口定义
- **`api/client.ts`**: 统一 HTTP 客户端，封装所有后端 API 调用
- **`utils/format.ts`**: 格式化工具（价格/百分比/成交量），信号类型→颜色/中文标签映射

### 4.2 页面

#### `HomePage.tsx` (首页/主工作台)
- 左侧面板（8/24）：StockSearch + WatchList + WatchlistSignalPanel + GoldenCrossScreen + ProviderStatus
- 右侧面板（16/24）：当选中股票后展示 Tabs（策略分析/回测），含 KLineChart + AnalysisPanel + BacktestPanel
- 核心状态：`selectedSymbol`, `analysisResult`, `backtestSignals`
- 选中股票时自动调用 `api.analyzeStock()`，回测结果传入 KLineChart 显示标记

#### `SettingsPage.tsx` (配置页)
- 直接渲染 `SettingsPanel` 组件

#### `AnalysisPage.tsx` (独立分析页)
- 与 HomePage 右侧相同的分析/回测布局，独立路由入口

### 4.3 组件

#### `StockSearch.tsx` (股票搜索)
- 300ms 防抖搜索，输入变化时调用 `api.searchStocks()`
- 下拉列表展示匹配结果，点击执行 `onSelect` 回调（添加自选+分析）

#### `WatchList.tsx` (自选列表)
- 加载自选股列表，每项含"分析"和"删除"按钮
- 依赖 `refreshKey` 属性响应外部刷新

#### `WatchlistSignalPanel.tsx` (自选股信号面板)
- 加载并展示自选股近3天买/卖信号
- 信号以彩色标签展示，支持刷新

#### `GoldenCrossScreen.tsx` (金叉筛选)
- **缓存扫描**: 遍历本地已缓存数据的股票，检测金叉和共振信号
- **全量扫描**: 启动后台线程扫描全市场，前端轮训进度
  - 支持暂停/继续，支持跳转到指定位置
  - 使用 `localStorage` 持久化 `scanId`，页面刷新后自动恢复轮训
  - 扫描结果同时存入 `localStorage`（key: `gcScanResults`），关闭窗口或刷新后仍可直接查看上次结果
  - 进度条展示 `processed/total`
  - 结果列表展示信号类型标签：红色"金叉" / 粉色"共振"

#### `KLineChart.tsx` (K线图表)
- 基于 ECharts 绘制：K线图 + MA5/MA20 均线 + 成交量柱+ 信号标记点
- 信号类型可筛选勾选（金叉/回踩/粘合/MACD+/共振/止损/死叉/止盈）
- 回测信号（买入/卖出）以 pin 标记显示，位置在 K 线最高价上方/下方，标签显示具体策略名称如 `买入(金叉)`、`卖出(死叉)`、`加仓` 等
- 自适应窗口 resize

#### `AnalysisPanel.tsx` (分析结果面板)
- 展示趋势、风险、仓位建议
- 信号列表 Table，支持按类型筛选和排序

#### `BacktestPanel.tsx` (回测面板)
- **策略选择**：下拉框选择回测策略（从 `/api/strategies` 加载列表），默认 `ma520`
- **策略规则展示**：选择策略后同步显示策略详情卡片，分区展示买入/卖出/加仓规则（条件→动作，按优先级排序）
- **表单（两行布局）**：
  - 第一行：时间范围选择器 + 运行回测按钮
  - 第二行：初始资金输入、费率输入（‱ 单位，默认2.5）、保底费用输入（元，默认5）
- **结果显示**：资产曲线 ECharts 图表 + 关键指标（收益率/年化/回撤/胜率/交易次数/费用） + 交易记录表
- 回调 `onBacktestResult` 将交易记录传入父组件展示在 K 线图上

#### `ProviderStatus.tsx` (数据源状态)
- 表格展示各数据源可用性/配置状态
- 显示当前优先级配置

#### `SettingsPanel.tsx` (设置面板)
- 表单：数据源优先级、同花顺 Token、SDK 开关、复权方式
- 保存后调用 `api.saveSettings()`

---

## 5. 数据库设计

### 5.1 ER 关系

```
stock_info (symbol PK) ── 1:N ── daily_quotes (symbol)
     │
     └── 1:1 ── watchlist (symbol FK)

backtest_results (独立表，无外键)
```

### 5.2 表结构

| 表 | 字段 | 说明 |
|---|---|---|
| `daily_quotes` | id, symbol, trade_date, open, high, low, close, volume, amount, source, adjusted, created_at | 日线行情；symbol+trade_date+adjusted 联合去重 |
| `watchlist` | id, symbol (UQ), name, added_at | 自选股 |
| `backtest_results` | id, symbol, start_date, end_date, initial_capital, adjust, total_return, annual_return, max_drawdown, win_rate, total_trades, total_fees, details (JSON text), created_at | 回测结果 |
| `stock_info` | id, symbol (UQ), name, exchange, updated_at | 股票基本信息 |

---

## 6. 部署与运维

### 6.1 Docker 部署
- **Dockerfile**: multi-stage，Stage1 使用 `node:20-alpine` 构建前端，Stage2 使用 `python:3.12-slim` 运行后端
- **docker-compose.yml**: 映射端口 8000，持久化挂载 `stock_analysis.db`、`config.json`、`symbol_cache.json`

### 6.2 Windows 开发
- `start.bat`: 一键启动（安装依赖 → 启动后端 → 启动前端 → 打开浏览器）
- `stop.bat`/`stop.ps1`: 按端口号查找并终止进程

### 6.3 Linux 部署脚本
- `scripts/install.sh` / `install-gitee.sh`: 一键 Docker 部署，支持端口/数据目录/版本参数

---

## 7. 数据流详解

### 7.1 当用户搜索并分析一只股票

```
用户输入代码 → StockSearch (300ms防抖) → GET /api/stocks/search?q=
  ├─ 东方财富 suggest API (优先)
  ├─ AKShare stock_zh_a_spot_em (fallback)
  └─ 本地 StockInfo 表 (最终 fallback)
→ 用户选择结果 → addWatchlist + analyzeStock
  └─ GET /api/analysis/{symbol}
    └─ ProviderManager.fetch_daily()
      ├─ 查 SQLite 缓存 (DailyQuote)
      ├─ 按 priority 轮询各 Provider
      └─ 写回缓存
    └─ StrategyEngine.analyze()
      ├─ _prepare(): MA/量比/MACD 计算
      ├─ get_trend(): MA20 斜率判断
      ├─ SignalDetector.detect_all(): 7种信号
      ├─ get_position_advice(): 仓位建议
      ├─ get_risk_warning(): 风险评估
      └─ to_chart_data(): 图表数据
→ 前端接收 AnalysisResponse → KLineChart + AnalysisPanel 渲染
```

### 7.2 当用户运行回测

```
用户选择日期/资金/费率/保底费用 → BacktestPanel → POST /api/backtest
  └─ ProviderManager.fetch_daily()
  └─ BacktestEngine.run()
    ├─ 读取 self.fee_rate / self.min_fee
    ├─ 逐日遍历 (i=20..len)
    ├─ 买入信号检测 (金叉/回踩/粘合/共振)
    ├─ 仓位管理 (首次30%, 加仓20%, 上限50%)
    ├─ 卖出信号检测 (止盈/死叉/止损)
    ├─ 费用计算: fee = max(金额 × fee_rate, min_fee)
    └─ 记录 equity_curve + trades
  └─ save_result(): 持久化到 BacktestResult
→ 前端接收 BacktestResponse → Statistic + ECharts + Table 渲染
→ backtestSignals 更新 KLineChart 显示买卖标记
```

### 7.3 全量金叉扫描

```
用户点击"全量扫描" → POST /api/stocks/golden-cross/full-scan
  └─ 后台线程遍历 _get_all_symbols() (约5000只A股)
    └─ 每只: ProviderManager → StrategyEngine → 检测 golden_cross + combined_gc_macd
    └─ 数据窗口: 近30天, 最少需27条
  └─ 状态存在 _scan_states[scan_id]
  └─ 返回结果含 signal_type 字段区分信号类型
→ 前端轮训 GET /api/stocks/golden-cross/full-scan/{scan_id}
  └─ 更新 Progress + 结果列表
  └─ 每轮结果同步写入 localStorage (gcScanResults)
→ 用户可暂停/继续/跳转
→ 刷新页面或关闭窗口后: 从 localStorage 读取上次结果直接展示
```

---

## 8. 配置项

### `backend/config.json`
```json
{
  "priority": ["baostock", "efinance", "ths_http", "ths_sdk", "sina", "akshare"],
  "ths_http_token": "",
  "ths_http_refresh_token": "",
  "ths_sdk_enabled": false,
  "default_adjust": "forward"
}
```

### `frontend/vite.config.ts` 开发代理
```
/api → http://127.0.0.1:8000
```

---

## 9. 扩展指南

### 新增数据源
1. 在 `backend/providers/` 下新建类继承 `QuoteProvider`
2. 实现 `fetch_daily()`, `is_available()`, `is_configured()`
3. 在 `ProviderManager.__init__()` 中注册
4. 在 `settings.priority` 中添加名称

### 新增信号类型
1. 在 `SignalDetector` 中新增 `_detect_xxx()` 方法
2. 在 `detect_all()` 中调用
3. 在 `StrategyEngine.get_position_advice()` 中处理新信号的仓位逻辑（可选）
4. 在 `BacktestEngine.run()` 中处理买入/卖出逻辑（可选）
5. 前端 `SIGNAL_COLORS`/`SIGNAL_LABELS` 添加颜色和标签
6. 前端 `KLineChart.tsx` 的 `SIGNAL_OPTIONS` 添加勾选

### 新增回测策略
1. 在 `strategy/registry.py` 的 `STRATEGIES` 字典中添加新策略条目（名称/描述/买入规则/卖出规则/加仓规则）
2. 在 `strategy/backtest.py` 的 `BacktestEngine` 中实现对应策略的回测逻辑（或创建新的 Engine 子类）
3. 策略规则描述会自动在回测面板的策略选择区展示，无需额外前端修改

### 修改策略规则
- **技术指标**: `StrategyEngine._prepare()` 中修改
- **信号条件**: `SignalDetector` 各方法中修改
- **仓位管理**: `StrategyEngine.get_position_advice()` 中修改
- **回测逻辑**: `BacktestEngine.run()` 中修改

---

## 10. 依赖清单

### 后端 (`requirements.txt`)
| 包 | 用途 |
|---|---|---|
| fastapi==0.115.6 | Web 框架 |
| uvicorn[standard]==0.34.0 | ASGI 服务器 |
| sqlalchemy==2.0.36 | ORM |
| pandas==2.2.3 | 数据处理 |
| numpy==2.1.3 | 数值计算 |
| akshare==1.16.84 | 免费 A 股数据 |
| baostock | 免费 A 股数据（需登录/登出） |
| efinance | 东方财富免费数据源 |
| pydantic==2.10.3 | 数据验证 |
| httpx==0.28.1 | HTTP 客户端 |
| python-dateutil==2.9.0 | 日期处理 |

### 前端 (`package.json`)
| 包 | 用途 |
|---|---|
| react 18 | UI 框架 |
| antd 5 | UI 组件库 |
| @ant-design/icons 5 | 图标库 |
| echarts 5 | 图表 |
| echarts-for-react 3 | ECharts React 封装 |
| react-router-dom 6 | 路由 |
| dayjs | 日期处理 |
