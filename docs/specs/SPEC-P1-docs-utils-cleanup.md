# 功能名称：文档更新 & 工具函数去重

> **定位**：WebUI 代码卫生 — 消除过时文档和重复代码，降低维护认知负担

---

## 1. 业务目标（一句话）

更新 `README.md` 和 `CLAUDE.md` 使其反映真实项目状态，并将页面中重复的 `formatBytes` 工具函数提取到共享位置。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：README.md 更新
- **Given** `webui-example/README.md` 已被重写
- **When** 新用户阅读 README
- **Then** 能看到：项目名称（TeleMemory WebUI）、功能简述、技术栈、前置条件、安装/运行命令、与后端的关系说明
- **And** 不再包含 "AI Studio" 与 `GEMINI_API_KEY` 直连说明

### AC-2：CLAUDE.md 目录树同步
- **Given** `webui-example/CLAUDE.md` 的目录结构部分已更新
- **When** 对比实际 `src/` 目录
- **Then** 所有文件和目录一一对应，无遗漏无虚增

### AC-3：formatBytes 去重
- **Given** `src/utils/formatters.ts` 已导出 `formatBytes` 函数
- **When** `grep -r "formatBytes" webui-example/src/`
- **Then** `Settings.tsx` 和 `Storage.tsx` 从 `@/utils/formatters` 导入，而非各自定义

### AC-4：构建通过
- **Given** 所有修改完成
- **When** 运行 `npm run build`
- **Then** 零错误

---

## 3. 技术设计 & 非功能需求

### 3.1 README.md 内容规划

```markdown
# TeleMemory WebUI

Telegram 消息搜索的 Web 管理界面，基于 React 19 + TypeScript + Vite 6 构建。

## 功能
- Telegram 登录（手机号 / Token）
- CJK 全文搜索（无限滚动）
- 同步会话管理
- 存储统计 & 缓存清理
- AI 配置管理
- 实时进度推送（WebSocket）

## 前置条件
- Node.js 18+
- 后端 API 运行在 http://localhost:8000

## 运行
npm install
npm run dev    # http://localhost:3000

## 技术栈
React 19 / TypeScript 5.8 / Vite 6 / Tailwind CSS 4
React Router 7 / Zustand 5 / TanStack React Query 5
```

### 3.2 CLAUDE.md 目录树修正

当前文档中根目录下列出了 `index.tsx`、`App.tsx`、`types.ts` 等文件，但实际它们已位于 `src/` 下。需要：
- 更新目录树使其与 `src/` 下的真实结构匹配
- 补充 `hooks/queries/` 子目录（5 个查询 hook 文件）
- 补充 `components/dashboard/`、`components/layout/` 子目录
- 补充 `api/` 下的 10 个文件（`ai_config.ts`、`config.ts`、`dashboard.ts`、`dialogs.ts`、`error.ts`、`status.ts`、`storage.ts` 等）

### 3.3 formatBytes 提取

当前 `utils/formatters.ts` 只有 `formatTime` 和 `getInitial`。需要添加：

```typescript
export const formatBytes = (bytes: number | null | undefined): string => {
    if (bytes === null || bytes === undefined) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
};
```

然后在 `Settings.tsx` 和 `Storage.tsx` 中替换为 `import { formatBytes } from '@/utils/formatters';`。

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📝 重写 README.md (20 min)
  - 按 3.1 模板重写
  - 确保与后端 CLAUDE.md 中的 WebUI 描述对齐

- [ ] **Task 1.2** — 📝 更新 CLAUDE.md 目录树 (20 min)
  - 运行 `find webui-example/src -type f | sort` 获取真实结构
  - 更新"目录结构"部分
  - 更新"与后端 API 对接"表格（补充 dashboard、storage、ai_config、dialogs、config、status 对接关系）

- [ ] **Task 1.3** — 🔧 提取 formatBytes 到 utils/formatters.ts (15 min)
  - 在 `formatters.ts` 中添加 `formatBytes` 导出
  - 修改 `Settings.tsx`：删除内联定义，添加 import
  - 修改 `Storage.tsx`：删除内联定义，添加 import

- [ ] **Task 1.4** — ✅ 验证 (10 min)
  - `npm run build` 零错误
  - `npx tsc --noEmit` 零错误
  - 确认页面中字节格式化显示正常

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| 1 | `npm run build` | 零错误 |
| 2 | `grep -r "AI Studio" webui-example/` | 无结果 |
| 3 | `grep -r "GEMINI_API_KEY" webui-example/README.md webui-example/CLAUDE.md` | 无结果 |
| 4 | `grep -c "formatBytes" webui-example/src/utils/formatters.ts` | ≥ 1 |
| 5 | `grep -c "const formatBytes" webui-example/src/pages/Settings.tsx` | 0（已删除内联定义） |
| 6 | `grep -c "const formatBytes" webui-example/src/pages/Storage.tsx` | 0（已删除内联定义） |
| 7 | 打开 `/settings`，检查 Storage Usage 字节显示 | 格式正确（如 "12.3 MB"） |
| 8 | 打开 `/storage`，检查 Total Usage 字节显示 | 格式正确 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-002：formatBytes 放置位置

- **背景**：`formatBytes` 在 `Settings.tsx` 和 `Storage.tsx` 各有一份完全相同的实现（签名：`(bytes: number | null) => string`）。
- **候选方案**：
  - (A) 提取到 `utils/formatters.ts`（已有 `formatTime` 和 `getInitial`）
  - (B) 新建 `utils/bytes.ts`
- **决定**：(A) — 放入已有的 `formatters.ts`
- **理由**：`formatBytes` 本质是一个格式化工具，与 `formatTime` 职责相同。独立文件过度拆分。
- **后果**：`formatters.ts` 成为所有格式化 utility 的唯一入口。

### 实现注意

- `CLAUDE.md` 中的代码片段（如 API 层、Hooks 等示例代码）无需修改，仅更新目录树和表格。
- README.md 应使用英文撰写（与代码语言一致），但可以保留中文注释解释 CJK 搜索特性。
