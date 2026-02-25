# 功能名称：搜索筛选器 & 暗色主题变量统一

> **定位**：WebUI 交互增强 — 让 Search 页 Filter Chips 真正可用，并统一暗色主题到 CSS 变量

---

## 1. 业务目标（一句话）

实现 Search 页日期与发送者筛选（前后端联动，契约一致），并将组件内散落的暗色硬编码 hex 值统一为语义化主题变量。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：日期筛选可用（后端参数直达）
- **Given** 用户在 Search 页点击 `Date: Anytime`
- **When** 选择 `Last 7 days`
- **Then** 请求包含 `date_from` 参数，返回结果仅包含最近 7 天消息

### AC-2：发送者筛选可用（后端参数直达）
- **Given** 用户在 Search 页点击 `Sender: All`
- **When** 选择发送者 `alice`
- **Then** 请求包含 `sender_username=alice`（或约定后的等价字段），结果仅包含该发送者消息

### AC-3：筛选器重置
- **Given** 用户已设置日期和发送者筛选
- **When** 点击 `Clear filters`
- **Then** 搜索恢复为仅按关键词查询（不携带 `date_from/date_to/sender_*`）

### AC-4：后端契约和索引设置已落地
- **Given** 后端 `/api/v1/search` 已支持发送者筛选参数
- **When** 执行后端单测与接口联调
- **Then** SearchService 会构造合法 Meili filter，且索引 `filterableAttributes` 包含发送者字段

### AC-5：暗色变量统一
- **Given** `index.css` 的 `@theme` 已补充暗色语义变量
- **When** 执行：
  - `grep -R -n '#192d33\|#325a67\|#233f48\|#162a30\|#1a3039\|#1e3a44\|#111e22\|#92bbc9\|#15262d\|#101d22' webui-example/src/ --exclude='index.css'`
  - `grep -n 'background-color:[[:space:]]*#101d22' webui-example/src/index.css`
- **Then** 两条命令均无输出（变量定义允许保留在 `index.css`，但组件与样式规则中不允许继续硬编码）

---

## 3. 技术设计 & 非功能需求

### 3.1 搜索筛选器：前后端契约

#### 当前现实

- 后端已支持：`date_from/date_to`
- 后端暂不支持：直接透传 `filter` 字符串
- 当前索引 filterable 字段：`chat.id/chat.type/date/from_user.id/reactions_scores`

> 结论：不能仅改前端去发 `filter`。必须补齐后端契约，否则 Sender 筛选会“看起来有 UI，实际无效果”。

#### 后端改造（本 SPEC 范围内）

1. `src/tg_search/services/contracts.py`：`SearchQuery` 新增发送者筛选字段（推荐 `sender_username`，也可约定为 `from_username`）
2. `src/tg_search/api/routes/search.py`：新增同名 Query 参数并下传到 `SearchQuery`
3. `src/tg_search/services/search_service.py`：在 `_build_filter` 拼接发送者条件
4. `src/tg_search/config/settings.py`：`INDEX_CONFIG.filterableAttributes` 增加 `from_user.username`
5. 索引设置刷新后执行一次增量重建/确认任务，保证新 filterable 生效

示意（后端）：

```python
# routes/search.py
sender_username: Optional[str] = Query(None, description="发送者用户名")

SearchQuery(
    q=q,
    ...,
    sender_username=sender_username,
)
```

```python
# search_service.py
if query.sender_username:
    safe = query.sender_username.replace('"', '\\"')
    conditions.append(f'from_user.username = "{safe}"')
```

#### 前端改造

```typescript
// api/search.ts
export interface SearchRequest {
  q: string;
  limit?: number;
  offset?: number;
  chat_id?: number;
  date_from?: string;
  date_to?: string;
  sender_username?: string;
}
```

```typescript
// hooks/queries/useSearch.ts
interface SearchFilters {
  dateFrom?: string;
  dateTo?: string;
  senderUsername?: string;
}

useSearchQuery(query, limit, filters)
```

Search 页面交互：
1. DateFilter：Anytime / Last 24h / Last 7 days / Last 30 days
2. SenderFilter：可输入用户名并清除
3. filters 与 query 共用 300ms 防抖
4. `queryKey` 包含 filters，避免跨筛选条件缓存污染

### 3.2 暗色主题变量统一

#### 需迁移的硬编码值

| 硬编码 Hex | 语义 | CSS 变量名 |
|-----------|------|-----------|
| `#192d33` | 暗色卡片背景 | `--color-card-dark` |
| `#325a67` | 暗色输入边框 | `--color-border-dark` |
| `#233f48` | 暗色分割线/次级边框 | `--color-divider-dark` |
| `#162a30` | 暗色下拉背景 | `--color-dropdown-dark` |
| `#1e3a44` | 暗色高亮底色 | `--color-highlight-dark` |
| `#1a3039` | 暗色代码底色 | `--color-code-dark` |
| `#111e22` | 暗色次级按钮底色 | `--color-button-secondary-dark` |
| `#92bbc9` | 暗色次级文本 | `--color-muted-dark` |
| `#15262d` | 暗色替代卡片底色 | `--color-surface-alt-dark` |
| `#101d22` | 已有背景主色 | 使用 `background-dark` |

迁移方式：
1. 在 `index.css` `@theme` 中定义/补齐变量
2. 统一替换组件内 `dark:bg-[#xxxxxx]`、`dark:border-[#xxxxxx]`、`dark:text-[#xxxxxx]`
3. 对 `#101d22` 使用已有 `background-dark` 语义色，不重复造变量

### 3.3 非功能需求

- **一致性**：筛选参数从 UI 到后端到索引设置全链路一致
- **性能**：筛选变化与关键词共用 300ms 防抖
- **可访问性**：下拉面板支持 Escape 关闭与焦点回收
- **可回滚性**：若后端 sender 参数未发布，前端 SenderFilter 必须暂时禁用并提示 `Backend pending`

---

## 4. 任务拆分

### Phase A：后端契约先行

- [ ] **Task A.1** — 🔧 扩展 SearchQuery 与路由参数（20 min）
  - 修改 `contracts.py` / `routes/search.py`
  - 增加 `sender_username`（或最终约定字段）

- [ ] **Task A.2** — 🔧 SearchService filter 拼接（20 min）
  - `_build_filter` 增加发送者条件
  - 处理引号转义，避免非法 filter 表达式

- [ ] **Task A.3** — 🔧 索引 filterableAttributes 更新（15 min）
  - 在 `settings.py` 增加 `from_user.username`
  - 触发索引设置同步并验证可筛选

- [ ] **Task A.4** — ✅ 后端验证（20 min）
  - 增加/更新测试：sender + date 组合筛选

### Phase B：前端筛选器接入

- [ ] **Task B.1** — 🔧 API 与 Hook 参数扩展（20 min）
  - `api/search.ts` 增加 `date_from/date_to/sender_username`
  - `useSearchQuery` 接收 `filters` 并加入 `queryKey`

- [ ] **Task B.2** — 🔧 DateFilter / SenderFilter 组件（40 min）
  - 新建 `components/search/DateFilter.tsx`
  - 新建 `components/search/SenderFilter.tsx`

- [ ] **Task B.3** — 🔧 Search 页面集成（20 min）
  - 替换静态 Chip
  - 增加 `Clear filters`

- [ ] **Task B.4** — ✅ 联调验证（20 min）
  - 关键词 + 日期
  - 关键词 + 发送者
  - 日期 + 发送者 + 分页

### Phase C：暗色变量统一

- [ ] **Task C.1** — 📋 收集并建映射（10 min）
  - `grep -rn` 全量收集暗色 hex

- [ ] **Task C.2** — 🔧 `@theme` 变量补齐（10 min）
  - 在 `index.css` 添加语义变量

- [ ] **Task C.3** — 🔧 全局替换（30 min）
  - 覆盖 `Login/Search/Settings/Storage/SyncedChats/SelectChats/AIConfig/BottomNav` 等页面

- [ ] **Task C.4** — ✅ 视觉回归与构建（15 min）
  - `npm run build`
  - 深色页面逐页检查

---

## 5. E2E 测试用例清单

### 后端契约

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | `GET /api/v1/search?q=hello&sender_username=alice` | 仅返回 `from_user.username=alice` 的结果 |
| T2 | `GET /api/v1/search?q=hello&date_from=...&date_to=...` | 日期范围正确 |
| T3 | `GET /api/v1/search?q=hello&sender_username=alice&date_from=...` | 返回交集 |
| T4 | 索引设置检查 `filterableAttributes` | 包含 `from_user.username` |

### 前端行为

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T5 | 输入关键词，不设筛选 | 行为与当前一致 |
| T6 | 设 `Last 7 days` | 请求含 `date_from`，结果受限 |
| T7 | 设 `Sender: alice` | 请求含 `sender_username`，结果受限 |
| T8 | 同时设日期 + 发送者 | 结果为交集 |
| T9 | 清除筛选 | 请求不带筛选参数 |
| T10 | 空搜索词 + 有筛选 | 不发起搜索请求 |

### 暗色变量

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T11 | `grep -R -n '#192d33\|#325a67\|#233f48\|#162a30\|#1a3039\|#1e3a44\|#111e22\|#92bbc9\|#15262d\|#101d22' webui-example/src/ --exclude='index.css'` + `grep -n 'background-color:[[:space:]]*#101d22' webui-example/src/index.css` | 两条命令均无命中 |
| T12 | 深色模式页面巡检 | 视觉不回退 |
| T13 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-003：发送者筛选必须走后端契约，不接受“纯前端假筛选”

- **背景**：仅在前端 local results 过滤会与分页冲突，导致结果不完整。
- **决定**：前后端联动，后端暴露 sender 参数并由 Meili filter 执行。
- **理由**：
  1. 分页场景正确性可保证
  2. 大结果集性能更稳定
  3. 行为可通过 API 契约测试精确验证

### ADR-004：发送者筛选字段选择 `from_user.username`

- **背景**：现有 filterable 默认包含 `from_user.id`，但 UI 更自然的是按用户名筛选。
- **决定**：扩展索引设置加入 `from_user.username`，前端使用 `sender_username` 参数。
- **后果**：索引设置变更后需要一次同步/重建确认。

### ADR-005：暗色硬编码统一采用语义变量

- **背景**：多个页面存在暗色 hex 漫游，修改成本高。
- **决定**：统一迁移到 `@theme` 语义变量，组件只使用 `bg-* / text-* / border-*`。
- **后果**：后续亮暗主题扩展仅需在主题层增量维护。
