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
| SPEC-P0-toast-notification.md | 2026-02-25 | `react-hot-toast` 安装，`toast.ts` 封装，`alert()` 替换，Toaster 挂载 App.tsx | WebUI 全局 Toast 通知系统 |
| SPEC-P0-dashboard-core.md | 2026-02-25 | 搜索框跳转、StatusCard KPI、SyncProgress WebSocket 进度、Header/FAB 功能化 | Dashboard 核心功能修复 |
| SPEC-P0-logout-entry.md | 2026-02-25 | Settings 页 Logout 按钮、`authApi.logout()` + `useAuthStore.logout()` + `navigate('/login')` | 退出登录入口 |
| SPEC-P1-skeleton-empty-states.md | 2026-02-25 | `<Skeleton>`, `<EmptyState>` | WebUI 界面过渡态 |
| SPEC-P1-dark-light-toggle.md | 2026-02-25 | `useTheme` Hook, localStorage, App.tsx 适配 | WebUI 外观设置 |
| SPEC-P1-page-transitions.md | 2026-02-25 | `framer-motion`, `PageTransition` | WebUI 路由和列表动画 |
| SPEC-P2-search-filters-theme.md | 2026-02-25 | `DateFilter`/`SenderFilter` 激活态高亮样式（`bg-primary/10 border-primary`），暗色 token 校验 | 搜索筛选器激活态 + 主题适配 |
| SPEC-P2-confirmation-dialog.md | 2026-02-25 | `ConfirmDialog.tsx`、`ConfirmProvider.tsx`、`useConfirm` hook，替换 Settings/Storage 的 `window.confirm()` | 二次确认对话框系统 |
| SPEC-P2-code-splitting.md | 2026-02-25 | `App.tsx` `React.lazy` + `Suspense` + `PageSkeleton`，`vite.config.ts` `manualChunks`（vendor/query/motion） | 路由懒加载 + 代码分割 |
| SPEC-P2-search-enhancements.md | 2026-02-25 | `searchHistory.ts`、`telegramLinks.ts`、Search.tsx 接入 `react-virtuoso` 虚拟滚动、搜索历史/建议下拉、"Open in Telegram" 链接 | 搜索增强 |

---

## 依赖关系说明

以下当前活跃 SPEC 依赖已归档的 SPEC 提供的基础能力：

- **SPEC-P1-dark-light-toggle** 依赖 **SPEC-P0-tailwind-v4-unification**（暗色模式必须为 class-based 策略 `@custom-variant dark`）→ ✅ 已完成
- **SPEC-P2-search-filters-theme Phase C** 依赖 **SPEC-P0-tailwind-v4-unification**（暗色变量统一到 `@theme`）→ ✅ 已完成
