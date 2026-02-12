# ClimABC 当前交付模式

本文档描述仓库**当前真实执行的工程模式**，偏实现与交付，不做泛化方法论展开。

## 1. 核心原则

- 数据源按来源拆分 fetcher，共享基础能力。
- 数据源元信息由配置驱动（`indicators.yaml`）。
- 生产刷新流程不使用合成数据。
- 分拆 parquet 是主存储契约。
- 前端展示遵循数据契约，不依赖临时结构。

## 2. 运行架构

### 观测数据路径

- 当前前端契约所需观测主要来自 PSL。
- Fetcher: `src/climabc/fetchers/psl.py` 中的 `PSLFetcher`。
- 写入前统一做标准化与异常值清洗。

### 预报数据路径

预报模块位于：

- `src/climabc/fetchers/forecast/iri.py`
- `src/climabc/fetchers/forecast/jamstec.py`

关键行为：
- IRI：先抓 `current` 页面，再按月份回补历史 quick-look 页面。
- JAMSTEC：从 SINTEX DMI CSV 中识别发布分界并生成批次。

## 3. 数据契约

默认 `generate` 输出：

```text
data/
  observations/
    <metric>.parquet
  forecasts/
    _index.parquet
    <metric>/
      <issued_month>.parquet
```

字段约定：

- 观测 parquet：
  - `date`, `value`
- 预报 parquet：
  - `forecast_id`, `source`, `issued_date`, `target_date`, `metric`, `value`, `is_historical`
- 预报索引 parquet：
  - `metric`, `issued_date`, `source`, `forecast_id`, `is_historical`

## 4. CLI 契约

主命令：

```bash
uv run climabc generate --split-output-dir data
```

职责：
- 拉取真实数据源
- 归并并规范化观测指标
- 在 parquet 落盘前将缺测标记和检测出的异常值替换为 `NaN`
- 写出分拆 parquet

可选输出（merged parquet / json）属于兼容与调试能力，不是主路径。

## 5. 前端数据模式

前端加载策略：
- 开发环境：直接读取 `/data/...` parquet（由 Vite 中间件暴露）
- 生产环境（GitHub Pages）：直接读取 raw GitHub 上的 parquet（`main/data`）
- 可选覆盖：`VITE_DATA_BASE_URL`

运行时组装：
- 前端按指标读取观测 parquet
- 通过 `forecasts/_index.parquet` 发现可用 `(metric, issued_date)` 文件
- 将预报行数据在前端合并为批次结构

## 6. CI/CD 模式

### 数据刷新工作流

- 每 5 天定时执行。
- 运行 `climabc generate`。
- 仅提交 `data/` 变更到 `main`。

### Pages 部署工作流

- `main` push 自动触发，但忽略 `data/**` 变更。
- 构建前端并部署 `frontend/dist` 到 GitHub Pages。
- 仅数据刷新提交不会触发前端重编译；页面运行时直接读取最新 parquet。

## 7. 测试模式

- Fetcher 解析与适配脚本单测。
- CLI 回归测试覆盖：
  - 指标范围
  - 分拆 parquet 输出
  - 异常值清洗
  - 预报批次拆分
- 前端工具层测试覆盖预报批次与时间轴行为。

## 8. 扩展规则

新增数据源时：
- 先补 `indicators.yaml` 配置
- 再实现对应 fetcher 模块
- 映射到现有前端指标键（或明确扩展指标契约）
- 增加解析与输出布局回归测试
- 非版本化迁移前，不破坏分拆 parquet 目录契约

若后续模式发生结构性变化，请用新版本文档显式替换本文件。
