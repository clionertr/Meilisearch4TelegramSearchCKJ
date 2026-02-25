# 功能名称：Dashboard 核心功能修复

> **定位**：WebUI 功能修复 — 让 Dashboard 从"静态看板"升级为"可交互控制中心"

---

## 1. 业务目标（一句话）

修复 Dashboard 页面的搜索框跳转、系统状态概览、WebSocket 同步进度可视化，以及 Header 按钮功能，使 Dashboard 成为用户日常操作的核心入口。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：搜索框跳转
- **Given** 用户在 Dashboard 顶部搜索框输入关键词
- **When** 按下 Enter 或点击搜索图标
- **Then** 跳转到 Search 页并自动填充关键词触发搜索

### AC-2：系统状态概览
- **Given** Dashboard 页面加载
- **When** 调用 `GET /api/v1/status`
- **Then** 展示 MeiliSearch 连接状态、索引消息总数、已同步聊天数

### AC-3：WebSocket 同步进度可视化
- **Given** 后台正在执行消息下载
- **When** WebSocket `/api/v1/ws/status` 推送进度事件
- **Then** Dashboard 展示当前下载的聊天名称和进度百分比（进度条或环形图）

### AC-4：退出登录入口（与 SPEC-P0-logout-entry 协同）
- **Given** 用户需要退出登录
- **When** 在 Dashboard 或 Settings 页面找到退出入口
- **Then** 确认后调用 `POST /api/v1/auth/logout`，清除 token，跳转到 Login 页

### AC-5：Header 按钮功能化
- **Given** Dashboard Header 存在菜单和设置按钮
- **When** 点击设置按钮
- **Then** 跳转到 Settings 页面（菜单按钮可暂时移除或关联侧边栏）

---

## 3. 技术设计 & 非功能需求

### 3.1 搜索框

```typescript
// Dashboard.tsx
const navigate = useNavigate();
const handleSearch = (query: string) => {
  navigate(`/search?q=${encodeURIComponent(query)}`);
};
```

Search 页从 URL query params 读取初始搜索词。

### 3.2 系统状态卡片

利用现有 `GET /api/v1/status` + `GET /api/v1/search/stats`：

```typescript
// hooks/queries/useDashboardStatus.ts
const { data: status } = useQuery(['status'], fetchStatus);
const { data: stats } = useQuery(['search-stats'], fetchSearchStats);
```

展示 3 个 KPI 卡片：
- 📊 总索引消息数
- 💬 已同步聊天数
- 🟢/🔴 MeiliSearch 连接状态

### 3.3 WebSocket 进度条

已有 `store/websocketStore.ts`，只需新增 UI 组件消费 store 数据：

```typescript
// components/SyncProgress.tsx
const progress = useWebSocketStore(s => s.progress);
// 渲染进度条 + 当前聊天名
```

### 3.4 非功能需求

- **首屏加载**：状态 API 请求并行发出，不串行阻塞
- **异常降级**：MeiliSearch 不可用时展示降级状态卡片，不阻塞整个 Dashboard
- **WebSocket**：断线自动重连（已有 store 逻辑），UI 展示"重连中..."

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 搜索框跳转 (20 min)
  - Dashboard 搜索框绑定 `onSubmit` 事件
  - `navigate('/search?q=...')`
  - Search 页读取 `searchParams.get('q')` 作为初始值

- [ ] **Task 1.2** — 🔧 系统状态 KPI 卡片 (30 min)
  - 创建 `hooks/queries/useDashboardStatus.ts`
  - 调用 `/api/v1/status` + `/api/v1/search/stats`
  - 创建 `components/StatusCard.tsx`（3 个 KPI 卡片）

- [ ] **Task 1.3** — 🔧 WebSocket 同步进度 UI (40 min)
  - 创建 `components/SyncProgress.tsx`
  - 消费 `useWebSocketStore` 进度数据
  - 进度条 + 当前聊天名 + 百分比

- [ ] **Task 1.4** — 🔧 Header 按钮功能化 (15 min)
  - 设置按钮 → `navigate('/settings')`
  - 菜单按钮：暂时移除或为 `noop` + Tooltip "Coming soon"

- [ ] **Task 1.5** — 🔧 FAB 按钮处理 (10 min)
  - FAB `chat_add_on` → `navigate('/synced-chats/select')`

- [ ] **Task 1.6** — ✅ 验证 (20 min)
  - Dashboard 搜索框 → Search 页带预填词
  - 状态卡片展示正确数据
  - WebSocket 进度条与后台下载同步
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Dashboard 搜索框输入 "hello" 回车 | 跳转到 `/search?q=hello`，搜索自动触发 |
| T2 | Dashboard 加载时 MeiliSearch 在线 | KPI 卡片显示绿色连接状态 + 消息总数 |
| T3 | Dashboard 加载时 MeiliSearch 离线 | KPI 卡片显示红色降级状态 |
| T4 | 后台正在下载消息 | 进度条展示当前聊天名和进度 |
| T5 | 后台无下载任务 | 进度区域显示 "No active sync" 或隐藏 |
| T6 | 点击 Header 设置按钮 | 跳转到 `/settings` |
| T7 | 点击 FAB 按钮 | 跳转到聊天选择页 |
| T8 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-007：Dashboard 使用并行数据获取而非瀑布流请求

- **背景**：Dashboard 需要同时展示状态 + 统计 + WebSocket 进度。
- **决定**：使用多个独立 `useQuery` 并行获取，不串行等待。
- **理由**：
  1. 首屏速度最优（不互相阻塞）
  2. 各卡片独立 loading/error 状态
  3. React Query 内置缓存 + 重试
- **后果**：Dashboard 会短暂出现部分卡片 loading 的状态，需要骨架屏配合（见 SPEC-P1-skeleton-empty-states）。
