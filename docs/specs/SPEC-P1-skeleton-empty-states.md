# 功能名称：骨架屏 & 空状态设计

> **定位**：WebUI 交互增强 — 提升加载感知与空数据引导，消灭"白屏+圆环转圈"的体验黑洞

---

## 1. 业务目标（一句话）

为核心列表页提供骨架屏（Skeleton）加载动画，并为无数据场景设计空状态插图和引导操作，消除"永远在转圈"的不确定感。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：骨架屏替代 Spinner
- **Given** Dashboard / Search / SyncedChats 页面首次加载
- **When** 数据尚未返回
- **Then** 展示与最终布局形状匹配的灰色脉冲骨架块，而非居中 `animate-spin` 圆环

### AC-2：Search 空结果引导
- **Given** 用户搜索 "asdfqwerty"（无匹配结果）
- **When** API 返回 `total_hits: 0`
- **Then** 展示空状态插图 + "No results found" 文案 + "Try different keywords" 引导

### AC-3：SyncedChats 空状态
- **Given** 用户未同步任何聊天
- **When** SyncedChats 页面加载
- **Then** 展示 "No synced chats yet" + "Start Syncing" 按钮跳转到 SelectChats

### AC-4：Dashboard Activity 空状态
- **Given** 无近期活动数据
- **When** Dashboard 的 ActivityList 为空
- **Then** 展示 "No recent activity" 文案

---

## 3. 技术设计 & 非功能需求

### 3.1 骨架屏组件

```tsx
// components/Skeleton.tsx
interface SkeletonProps {
  variant: 'text' | 'card' | 'avatar' | 'button';
  width?: string;
  height?: string;
  count?: number; // 重复行数
}

// 使用 Tailwind animate-pulse
<div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded" />
```

各页面模板：
- `DashboardSkeleton`: 3 KPI 卡片 + 4 行 Activity
- `SearchSkeleton`: 3 个结果卡片
- `SyncedChatsSkeleton`: 5 行聊天项

### 3.2 空状态组件

```tsx
// components/EmptyState.tsx
interface EmptyStateProps {
  icon: string;          // Material Symbol name
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}
```

### 3.3 非功能需求

- **一致性**：所有骨架屏使用相同的脉冲动画时长（`1.5s`）
- **无闪烁**：数据 <200ms 返回时不展示骨架屏（可选延迟阈值）
- **可访问性**：骨架屏区域标注 `aria-busy="true"`

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 Skeleton 基础组件 (20 min)
  - 创建 `components/Skeleton.tsx`（text / card / avatar 变体）
  - 统一 `animate-pulse` 动画参数

- [ ] **Task 1.2** — 🔧 EmptyState 基础组件 (20 min)
  - 创建 `components/EmptyState.tsx`
  - 支持 icon + title + description + action button

- [ ] **Task 1.3** — 🔧 Dashboard 骨架屏 (20 min)
  - 替换 Dashboard 的 loading spinner
  - KPI 卡片 + Activity 列表骨架

- [ ] **Task 1.4** — 🔧 Search 骨架屏 + 空状态 (25 min)
  - 搜索中：3 个结果卡片骨架
  - 无结果：EmptyState("No results found")

- [ ] **Task 1.5** — 🔧 SyncedChats 空状态 (15 min)
  - 无同步聊天时展示空状态 + "Start Syncing" 引导

- [ ] **Task 1.6** — ✅ 验证 (15 min)
  - 各页面骨架屏 → 数据加载过渡自然
  - 空状态展示正确
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Dashboard 首次加载（慢网络模拟） | 展示骨架屏，数据到达后骨架消失 |
| T2 | Search "xyznoexist" | 空状态插图 + 引导文案 |
| T3 | SyncedChats 无同步聊天 | 空状态 + "Start Syncing" 按钮 |
| T4 | 点击 SyncedChats 空状态的 "Start Syncing" | 跳转到 SelectChats |
| T5 | Dashboard Activity 无数据 | "No recent activity" 文案 |
| T6 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-009：骨架屏使用 Tailwind animate-pulse 而非第三方库

- **背景**：可选方案有 `react-loading-skeleton`、`react-content-loader`、或原生 CSS。
- **决定**：使用 Tailwind 内置 `animate-pulse` + 自定义形状 div。
- **理由**：零额外依赖，与项目 Tailwind 技术栈一致，灵活度足够。
- **后果**：骨架需手动匹配各页面布局形状，但页面数量有限（约 5 个），可控。
