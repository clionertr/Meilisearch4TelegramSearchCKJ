# 功能名称：代码分割与路由懒加载

> **定位**：WebUI 性能优化 — 减少首屏 bundle 大小，实现按需加载

---

## 1. 业务目标（一句话）

通过 `React.lazy()` + `Suspense` 实现路由级代码分割，将首屏加载 JS 体积减少 40%+，提升弱网/移动端加载速度。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：路由懒加载
- **Given** 用户访问 `/login`
- **When** 页面加载
- **Then** 仅加载 Login chunk + 公共 chunk，不包含 Settings / AIConfig 等页面代码

### AC-2：首屏体积下降
- **Given** 执行 `npm run build`
- **When** 比较 chunk 体积
- **Then** 入口 chunk（`index-*.js`）体积相比改造前减少 30%+

### AC-3：懒加载页面过渡
- **Given** 用户从 Dashboard 切换到 Storage
- **When** Storage chunk 尚未下载完成
- **Then** 展示 Suspense fallback（骨架屏或 loading 指示器），不白屏

---

## 3. 技术设计 & 非功能需求

### 3.1 实现方案

```tsx
// App.tsx
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Search = lazy(() => import('./pages/Search'));
const Settings = lazy(() => import('./pages/Settings'));
const Storage = lazy(() => import('./pages/Storage'));
const SyncedChats = lazy(() => import('./pages/SyncedChats'));
const SelectChats = lazy(() => import('./pages/SelectChats'));
const AIConfig = lazy(() => import('./pages/AIConfig'));

// Login 保持同步导入（首屏必需）
import Login from './pages/Login';
```

```tsx
<Suspense fallback={<PageSkeleton />}>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/dashboard" element={<Dashboard />} />
    ...
  </Routes>
</Suspense>
```

### 3.2 Vite splitChunks 配置

```typescript
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom', 'react-router-dom'],
        query: ['@tanstack/react-query'],
      }
    }
  }
}
```

### 3.3 非功能需求

- **兼容性**：使用 Vite 内建的 dynamic import，无需额外配置
- **体验**：Suspense fallback 使用骨架屏（依赖 SPEC-P1-skeleton-empty-states）
- **可度量**：`npm run build` 后检查 chunk 分布

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📋 当前 bundle 基线分析 (15 min)
  - 执行 `npx vite-bundle-visualizer`
  - 记录当前入口 chunk 体积

- [ ] **Task 1.2** — 🔧 页面懒加载改造 (25 min)
  - 在 `App.tsx` 中将除 Login 外的页面改为 `React.lazy()`
  - 添加 `<Suspense>` fallback

- [ ] **Task 1.3** — 🔧 Vite chunk 优化 (15 min)
  - 配置 `manualChunks` 分离 vendor / query 库
  - 重新 build 验证

- [ ] **Task 1.4** — ✅ 验证与对比 (15 min)
  - 再次 `npx vite-bundle-visualizer`
  - 对比前后入口 chunk 体积
  - 各页面切换无白屏
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | `npm run build` | 零错误，chunk 按页面分割 |
| T2 | 加载 `/login` | DevTools Network 仅下载 login + vendor chunk |
| T3 | `/dashboard` → `/settings` | Settings chunk 按需下载 |
| T4 | 弱网模拟（Chrome DevTools 3G） | Suspense fallback 展示，不白屏 |
| T5 | Bundle 分析对比 | 入口 chunk 体积减少 30%+ |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-014：Login 页保持同步导入

- **背景**：所有页面都可以懒加载，但 Login 是未认证用户的首屏页面。
- **决定**：Login 保持 eagerly imported。
- **理由**：登录页是进入应用的第一个页面，懒加载反而增加首屏延迟。
- **后果**：入口 chunk 仍包含 Login 代码（约 10KB），但这是合理的性能取舍。
