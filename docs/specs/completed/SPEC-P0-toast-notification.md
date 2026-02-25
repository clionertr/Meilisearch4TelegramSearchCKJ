# 功能名称：Toast 通知系统

> **定位**：WebUI 基础体验设施 — 替代 `alert()` 和分散式错误展示，建立统一的用户反馈通道

---

## 1. 业务目标（一句话）

建立全局 Toast 通知组件（success / error / warning / info），替换所有 `alert()` 调用和碎片化错误提示，为后续功能提供统一反馈基础。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：Toast 基本渲染
- **Given** 任何页面触发 `toast.success("xxx")` 调用
- **When** Toast 组件渲染
- **Then** 右上角（或底部）显示带图标的通知条，3 秒后自动消失，支持手动关闭

### AC-2：替换 Storage 页 alert()
- **Given** 用户在 Storage 页点击 "Clean Cache"
- **When** 清理完成
- **Then** 不再弹出 `alert()`，改为 Toast 提示 "Cache cleaned successfully"

### AC-3：错误统一展示
- **Given** API 请求返回 4xx/5xx 错误
- **When** 错误被捕获
- **Then** 展示红色 Toast 而非行内红色文本块（Login 页验证码错误除外，保留行内提示）

### AC-4：多 Toast 堆叠
- **Given** 短时间内触发多个通知
- **When** 同时存在 ≥2 个 Toast
- **Then** 垂直堆叠，最新在顶/底部，超过 5 个时最早的自动移除

---

## 3. 技术设计 & 非功能需求

### 3.1 方案选型

推荐 **react-hot-toast** 或自建轻量组件：

| 方案 | 优点 | 缺点 |
|------|------|------|
| `react-hot-toast` | 体积小(~5KB)、API 简洁、支持 Promise | 样式需覆盖以匹配主题 |
| `sonner` | 动画精美、堆叠体验好 | 需验证与 Tailwind v4 兼容 |
| 自建 | 完全可控 | 实现成本较高 |

**推荐**: `react-hot-toast`，配合自定义主题样式。

### 3.2 架构

```
src/
  components/
    Toast/
      ToastProvider.tsx    # 在 App.tsx 根级挂载 <Toaster />
      toast.ts             # 导出统一调用入口 toast.success/error/...
```

### 3.3 非功能需求

- **性能**：Toast 渲染不阻塞主线程，使用 Portal 挂载
- **可访问性**：Toast 区域标注 `role="status"` + `aria-live="polite"`
- **暗色适配**：自动跟随 `dark` class

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📦 安装 Toast 库并创建封装 (20 min)
  - 安装 `react-hot-toast`（或选定方案）
  - 创建 `ToastProvider.tsx` 和 `toast.ts`
  - 在 `App.tsx` 挂载 `<Toaster />`

- [ ] **Task 1.2** — 🎨 Toast 主题适配 (20 min)
  - 匹配项目暗色/亮色主题变量
  - success/error/warning/info 四种变体样式
  - 动画与位置调优

- [ ] **Task 1.3** — 🔧 替换 Storage 页 alert() (15 min)
  - 替换 `alert()` 为 `toast.success()`
  - 清理操作失败时用 `toast.error()`

- [ ] **Task 1.4** — 🔧 统一 API 错误反馈 (30 min)
  - 在 API 层 `onError` 回调中接入 Toast
  - 保留 Login 页行内错误展示（如验证码错误）
  - 清理多余的行内错误 `<div>` 块

- [ ] **Task 1.5** — ✅ 验证与构建 (15 min)
  - `npm run build` 零错误
  - 手动触发 success / error / 多 Toast 堆叠场景

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Storage 页点击 Clean Cache 成功 | Toast 显示成功消息，无 `alert()` |
| T2 | 触发 API 错误（如网络断连模拟） | 红色 Toast 显示错误信息 |
| T3 | 快速连续触发 3 个通知 | 3 个 Toast 垂直堆叠 |
| T4 | Toast 等待 3 秒 | 自动消失 |
| T5 | 点击 Toast 关闭按钮 | 立即消失 |
| T6 | 暗色模式下 Toast | 样式正确，对比度达标 |
| T7 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-006：选用 react-hot-toast 而非自建

- **背景**：项目需要全局反馈通道替代 `alert()` 和碎片化错误展示。
- **决定**：使用 `react-hot-toast`（或 `sonner`），不自建。
- **理由**：
  1. 体积小（gzip ~5KB），对 bundle 影响最低
  2. 内置 Promise toast（适配异步操作）
  3. 可通过自定义主题完全匹配当前设计语言
- **后果**：新增一个运行时依赖，但可在 1h 内完成全部迁移。
