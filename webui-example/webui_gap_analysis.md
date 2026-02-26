# WebUI 历史遗留问题台账（2026-02-26）

> 本文件替代旧版“体验差距报告”，改为可执行的问题台账。
>
> 目标：把“历史遗留问题”从描述性文档，转成可迭代跟踪的行动清单。

---

## 范围与判定

- 范围：`webui-example/`（页面、hooks、api 层、样式与交互）
- 判定口径：
  - `Done`：代码已落地且可在当前分支验证
  - `Backlog`：尚未落地或仅部分落地

---

## 已解决（Done）

| ID | 事项 | 状态说明 |
|----|------|----------|
| D-01 | 登录页多步骤体验 | 已支持手机号验证码 / 2FA / Token 登录，并包含聚焦与错误提示 |
| D-02 | 搜索契约对齐 | 前端字段已对齐后端 `SearchResult`（`formatted_text` 等） |
| D-03 | Toast 通知体系 | 已替换早期 `alert()` 方案，统一 `react-hot-toast` |
| D-04 | 路由过渡动画 | 已通过 `PageTransition` + `framer-motion` 覆盖主页面切换 |
| D-05 | 退出登录入口 | Settings 页已提供退出登录确认流程 |
| D-06 | Dashboard 基础能力 | 已支持活动列表、状态卡片、同步进度展示 |
| D-07 | i18n 基础能力 | 已提供 `en-US` / `zh-CN` 文案资源 |
| D-08 | WebSocket 事件契约 | 已按 `type=progress` + `data.dialog_id` 消费 |

---

## 待处理（Backlog）

### P0（高优先级）

| ID | 问题 | 现状 | 建议落点 |
|----|------|------|----------|
| P0-01 | Search 筛选器能力不完整 | Date/Sender UI 存在，但联动查询能力有限 | `src/pages/Search.tsx` + `src/api/search.ts` |
| P0-02 | 错误语义映射不统一 | 各页面仍有局部错误文案拼装 | `src/api/error.ts` + i18n 错误码字典 |
| P0-03 | 状态空页面引导不足 | 部分页面空状态缺少下一步动作提示 | `src/components/common/EmptyState.tsx` 复用增强 |

### P1（中优先级）

| ID | 问题 | 现状 | 建议落点 |
|----|------|------|----------|
| P1-01 | 搜索结果性能风险 | 长列表场景仍可能出现渲染抖动 | 在 Search 页全面接入 `react-virtuoso` |
| P1-02 | 主题切换入口不足 | 已有主题 hook，但设置入口弱 | `src/pages/Settings.tsx` 增加显式主题控制 |
| P1-03 | 会话列表筛选 | Synced/Select 页面缺少搜索与类型过滤 | `src/pages/SyncedChats.tsx` / `SelectChats.tsx` |
| P1-04 | WebSocket 断线反馈 | 有重连但缺少显式 UI 告知 | 全局 banner 或连接状态 chip |

### P2（优化项）

| ID | 问题 | 现状 | 建议落点 |
|----|------|------|----------|
| P2-01 | 可访问性细节 | 基础焦点态已具备，仍可补键盘流和 aria 语义 | 逐页 a11y 清单 |
| P2-02 | 视觉 token 统一 | 暗色模式仍有少量硬编码色值 | 提炼 CSS 变量与语义 token |
| P2-03 | 指标面板 | 目前仅日志观测，缺少前端内嵌诊断面板 | 增加 dev-only telemetry panel |

---

## 本轮新增（2026-02-26）

- 新增前端 telemetry：`api.start/api.end/api.error/ws.state/ws.message`
- 新增 `.env` 模板：
  - `webui-example/.env.example`
  - `webui-example/.env.development.example`
- 将本文件改为“Done + Backlog”台账结构，便于后续迭代持续更新

---

## 维护约定

- 每完成一个事项，必须同步更新本文件状态与日期。
- 新增问题时需给出：`优先级 + 影响范围 + 建议落点`。
- 不再维护纯描述性的“打分报告”，统一以可执行条目为准。
