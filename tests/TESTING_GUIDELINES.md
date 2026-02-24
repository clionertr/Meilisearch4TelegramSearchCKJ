# Testing Guidelines

本规范用于统一本项目测试体系，目标是：
- 单元测试与集成测试彻底分层
- 默认执行稳定、快速、可复现
- 外部依赖（MeiliSearch/API/Telegram）按需显式启用

## 1. 目录结构

- `tests/unit/`: 纯单元测试。禁止依赖真实外部服务。
- `tests/integration/`: 集成测试。允许访问真实 MeiliSearch / API 服务。
- `tests/helpers/`: 测试共享工具函数（环境检查、跳过门控、公共断言）。
- `tests/conftest.py`: 全局 pytest 配置（只放 marker 注册和通用行为，不注入业务环境变量）。
- `tests/unit/conftest.py`: 单元测试专用 fixtures 和默认测试环境。
- `tests/integration/conftest.py`: 集成测试专用 fixtures 和开关逻辑。

## 2. 标记约定

- `@pytest.mark.unit`: 单元测试。
- `@pytest.mark.integration`: 集成测试。
- `@pytest.mark.e2e`: 端到端场景（通常是 integration 子集）。
- `@pytest.mark.meili`: 依赖真实 MeiliSearch。

说明：
- 新增测试必须显式标记，避免测试层级漂移。
- `tests/unit/` 中测试默认应为 `unit`。
- `tests/integration/` 中测试默认至少带 `integration`，按需追加 `e2e`、`meili`。

## 3. 运行策略

推荐命令：

```bash
# 仅运行单元测试（默认开发流程）
pytest tests/unit -v

# 运行集成测试（需显式开启）
RUN_INTEGRATION_TESTS=true pytest tests/integration -v

# 按 marker 运行
pytest -m unit -v
RUN_INTEGRATION_TESTS=true pytest -m integration -v
```

## 4. 环境与依赖规则

- 单元测试不得在模块顶层写入全局环境变量（`os.environ[...] = ...`）。
- 单元测试需使用 fixture 或 `monkeypatch` 注入环境。
- 集成测试的外部依赖检查必须复用 `tests/helpers/requirements.py`，禁止每个文件重复实现 `_check_meili_available`。
- 集成测试默认可跳过（例如 key 未配置），但跳过原因必须清晰可读。

## 5. 编写规则

- 测试文件命名：`test_*.py`。
- 测试函数命名：`test_*`。
- 禁止将脚本（`print`/临时调试）放在 `test_*.py` 中。
- 对已知缺陷应使用 `xfail` 或明确断言，禁止 `try/except + skip` 掩盖真实回归。

## 6. 迁移与维护规则

- 任何新增真实依赖测试必须放入 `tests/integration/`。
- 若需要从旧测试迁移：
1. 先移动文件到正确层级；
2. 再补 marker；
3. 最后在 CI/本地命令中接入。
- 当测试逻辑与业务契约变化时，先更新本规范再改测试代码。
