# 功能名称：二次确认对话框

> **定位**：WebUI 安全交互 — 对敏感操作增加确认步骤，防止误操作

---

## 1. 业务目标（一句话）

创建全局可复用的确认对话框组件，替代浏览器原生 `confirm()`，在清理缓存、删除同步、退出登录等敏感操作前要求用户二次确认。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：确认对话框渲染
- **Given** 调用 `confirm({ title, message, onConfirm })`
- **When** 对话框渲染
- **Then** 展示半透明遮罩 + 居中卡片，含标题、描述、Cancel / Confirm 两个按钮

### AC-2：替换 confirm() 调用
- **Given** Logout 使用 `window.confirm()`
- **When** 用户点击 Logout
- **Then** 弹出自定义确认对话框而非浏览器原生弹窗

### AC-3：危险操作高亮
- **Given** 确认对话框类型为 `danger`
- **When** 渲染
- **Then** Confirm 按钮为红色，与普通蓝色确认区分

### AC-4：键盘与可访问性
- **Given** 确认对话框展示
- **When** 按 Escape
- **Then** 对话框关闭（等同 Cancel）

---

## 3. 技术设计 & 非功能需求

### 3.1 组件设计

```tsx
// components/ConfirmDialog.tsx
interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  variant?: 'default' | 'danger';
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}
```

或使用命令式 API（通过 Context/Hook）：

```typescript
// hooks/useConfirm.ts
const { confirm } = useConfirm();
const ok = await confirm({
  title: 'Clear Cache',
  message: 'This will remove all cached search results.',
  variant: 'danger',
});
if (ok) { /* proceed */ }
```

### 3.2 应用场景

| 场景 | 变体 | 出现页面 |
|------|------|----------|
| 清理缓存 | `danger` | Storage |
| 清理媒体 | `danger` | Storage |
| 退出登录 | `danger` | Settings |
| 删除同步配置 | `danger` | SyncedChats (未来) |

### 3.3 非功能需求

- **动画**：配合 framer-motion 淡入/缩放（若已引入）
- **可访问性**：焦点锁定在对话框内 + `aria-modal="true"` + `role="alertdialog"`
- **遮罩点击**：点击遮罩等同 Cancel

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 ConfirmDialog 组件 (30 min)
  - 创建组件：遮罩 + 卡片 + 标题 + 描述 + 两个按钮
  - `default` 和 `danger` 两种变体
  - Escape 关闭 + 遮罩点击关闭

- [ ] **Task 1.2** — 🔧 useConfirm Hook (命令式 API) (20 min)
  - 创建 `ConfirmProvider` + `useConfirm` Hook
  - `await confirm(...)` 返回 Promise<boolean>

- [ ] **Task 1.3** — 🔧 替换现有 confirm() 调用 (15 min)
  - Storage 页 → 使用 `useConfirm`
  - Logout 按钮 → 使用 `useConfirm`

- [ ] **Task 1.4** — ✅ 验证 (10 min)
  - 视觉一致、暗色适配
  - Escape / 遮罩 / Cancel 均关闭
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Storage 页清理缓存 → 弹出确认 | 红色 Confirm 按钮 |
| T2 | 点击 Cancel | 对话框关闭，操作未执行 |
| T3 | 点击 Confirm | 对话框关闭，操作执行 |
| T4 | 按 Escape | 对话框关闭，操作未执行 |
| T5 | 点击遮罩 | 对话框关闭 |
| T6 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-013：命令式 confirm() API 而非纯声明式

- **背景**：多个页面需要在 `onClick` 回调中确认后执行操作。
- **决定**：提供 `useConfirm` Hook 的命令式 `await confirm(...)` API。
- **理由**：
  1. 调用方代码简洁（`if (await confirm(...)) { doThing() }`）
  2. 声明式 `<ConfirmDialog open={open} />` 需在每个页面管理 `open` 状态，冗余
  3. 同时保留声明式接口以支持复杂场景
- **后果**：需要在 App 根级挂载 `<ConfirmProvider>`。
