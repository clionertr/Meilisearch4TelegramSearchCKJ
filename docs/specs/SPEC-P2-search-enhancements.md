# 功能名称：搜索增强（历史记录 / 自动建议 / 虚拟滚动）

> **定位**：WebUI 体验精细化 — 提升 Search 页面的实用性和性能

---

## 1. 业务目标（一句话）

为搜索页增加搜索历史记录、搜索建议/自动补全、虚拟滚动（大结果集不卡顿），以及结果卡片跳转到 Telegram 原始消息的链接。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：搜索历史
- **Given** 用户曾搜索过 "hello"
- **When** 聚焦搜索框（未输入文字）
- **Then** 下拉展示最近 10 条搜索历史，点击可快速填充并搜索

### AC-2：搜索历史清除
- **Given** 搜索历史下拉可见
- **When** 点击 "Clear History" 按钮
- **Then** 清除 localStorage 中的搜索历史记录

### AC-3：虚拟滚动
- **Given** 搜索返回 100+ 条结果
- **When** 用户滚动浏览
- **Then** 仅渲染可视区域 ± buffer 的 DOM 节点，帧率稳定不卡顿

### AC-4：跳转原始消息
- **Given** 搜索结果卡片展示了一条消息
- **When** 点击结果卡片上的 "Open in Telegram" 链接
- **Then** 打开 `https://t.me/c/{chat_id}/{msg_id}` 或对应格式的 Telegram 深链接

---

## 3. 技术设计 & 非功能需求

### 3.1 搜索历史

存储于 `localStorage`，key 为 `search_history`，值为 `string[]` (最多 20 条，FIFO)。

```typescript
// utils/searchHistory.ts
export function addSearchHistory(query: string): void;
export function getSearchHistory(): string[];
export function clearSearchHistory(): void;
```

### 3.2 虚拟滚动

推荐 `react-virtuoso`（与 React Query `useInfiniteQuery` 集成最佳）：

```tsx
import { Virtuoso } from 'react-virtuoso';

<Virtuoso
  data={allResults}
  endReached={loadMore}
  itemContent={(index, item) => <SearchResultCard result={item} />}
/>
```

### 3.3 Telegram 深链接

```typescript
// utils/telegramLinks.ts
export function getTelegramLink(chatId: number, msgId: number): string {
  // Private/group: t.me/c/{adjusted_chat_id}/{msg_id}
  // Public: t.me/{username}/{msg_id}
  const adjustedId = Math.abs(chatId) - 1000000000000; // 去掉 -100 前缀
  return `https://t.me/c/${adjustedId}/${msgId}`;
}
```

### 3.4 非功能需求

- **性能**：虚拟滚动需保证 1000+ 结果下帧率 >55fps
- **隐私**：搜索历史仅存本地 localStorage
- **降级**：无法构造 Telegram 链接时（缺少 chatId/msgId）隐藏链接

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 搜索历史工具函数 (15 min)
  - 创建 `utils/searchHistory.ts`
  - add / get / clear 方法

- [ ] **Task 1.2** — 🔧 搜索历史 UI 集成 (30 min)
  - 搜索框聚焦时展示历史下拉
  - 点击历史项填充搜索
  - "Clear History" 功能

- [ ] **Task 1.3** — 🔧 虚拟滚动接入 (40 min)
  - 安装 `react-virtuoso`
  - 替换 Search 页面的 `.map()` 渲染为 `<Virtuoso>`
  - 与 `useInfiniteQuery` 的 `fetchNextPage` 集成

- [ ] **Task 1.4** — 🔧 Telegram 深链接 (20 min)
  - 创建 `utils/telegramLinks.ts`
  - 结果卡片增加 "Open in Telegram" 图标链接

- [ ] **Task 1.5** — ✅ 验证 (20 min)
  - 搜索历史记录功能完整
  - 虚拟滚动性能测试（模拟 500+ 条结果）
  - Telegram 链接正确跳转
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | 搜索关键词后聚焦搜索框 | 历史下拉包含之前搜索的关键词 |
| T2 | 点击历史项 | 搜索框填充该词并触发搜索 |
| T3 | Clear History | localStorage 中历史清空 |
| T4 | 搜索结果超过 100 条时滚动 | DOM 节点数维持在 30 个以内 |
| T5 | 点击 "Open in Telegram" | 新标签打开 Telegram 链接 |
| T6 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-012：使用 react-virtuoso 而非 react-window

- **背景**：Search 结果卡片高度不固定（文本长度不一），需要支持动态高度。
- **决定**：使用 `react-virtuoso`。
- **理由**：原生支持动态高度项，且与 `useInfiniteQuery` 的 `endReached` 无缝配合。`react-window` 要求固定高度或手动测量。
- **后果**：依赖增加约 15KB (gzip)，但解决了大数据集的关键性能瓶颈。
