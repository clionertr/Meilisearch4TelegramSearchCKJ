# 已完成 SPEC 归档索引

> 此文件记录已实现并从 `docs/specs/` 主目录删除的规格文档，便于后续追溯依赖上下文。

---

## 归档列表

| SPEC 文件 | 完成时间 | 相关变更 | 原始定位 |
|-----------|---------|----------|----------|
| SPEC-P0-tailwind-v4-unification.md | 2025-02-25 | Tailwind v4 CSS-first 统一，删除 `tailwind.config.js` | WebUI 构建基础设施修复 — 消除 v3/v4 共存 |
| SPEC-P0-config-policy-service.md | 2025-02-25 | `ConfigPolicyService` 落地 | 统一白/黑名单读写入口 |
| SPEC-P0-search-service.md | 2025-02-25 | `SearchService` 落地 | 统一 Bot/API 搜索过滤、高亮、分页 |
| SPEC-P0-service-layer-architecture.md | 2025-02-25 | Service 层架构 + `ServiceContainer` | 共享 service 实例注入 |
| SPEC-P0-runtime-control-service.md | 2025-02-25 | `RuntimeControlService` 落地 | 任务启停状态机与并发锁 |
| SPEC-P1-observability-service.md | 2025-02-25 | `ObservabilityService` 落地 | 统一可观测性快照采集 |
| SPEC-P1-docs-utils-cleanup.md | 2025-02-25 | formatBytes 去重、README 更新 | 文档/工具函数整理 |
| SPEC-P3-dead-code-cleanup.md | 2025-02-25 | geminiService 移除、旧类型清理 | 死代码清理 |

---

## 依赖关系说明

以下当前活跃 SPEC 依赖已归档的 SPEC 提供的基础能力：

- **SPEC-P1-dark-light-toggle** 依赖 **SPEC-P0-tailwind-v4-unification**（暗色模式必须为 class-based 策略 `@custom-variant dark`）→ ✅ 已完成
- **SPEC-P2-search-filters-theme Phase C** 依赖 **SPEC-P0-tailwind-v4-unification**（暗色变量统一到 `@theme`）→ ✅ 已完成
