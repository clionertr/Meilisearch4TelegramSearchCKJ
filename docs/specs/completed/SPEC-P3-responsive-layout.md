# 功能名称：响应式布局（平板/桌面适配）

> **定位**：WebUI 长期演进 — 从"仅移动端可用"升级为"多端友好"

---

## 1. 业务目标（一句话）

突破 `max-w-md` 的移动端限制，实现响应式布局（sm / md / lg / xl 断点），平板端双栏、桌面端三栏，底部导航在桌面端转为侧边栏。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：平板端双栏
- **Given** 屏幕宽度 768px - 1024px
- **When** 访问 Dashboard
- **Then** 侧边栏（导航）+ 内容区双栏布局，内容不再压缩在窄条中

### AC-2：桌面端三栏
- **Given** 屏幕宽度 > 1280px
- **When** 访问 Search 页
- **Then** 左侧导航 + 中间搜索结果 + 右侧详情面板（可选）

### AC-3：导航适配
- **Given** 屏幕宽度 > 768px
- **When** 任意页面
- **Then** 底部导航隐藏，替换为左侧边栏导航

### AC-4：移动端无退化
- **Given** 屏幕宽度 < 640px
- **When** 访问任意页面
- **Then** 布局与当前移动端一致（不退化）

---

## 3. 技术设计 & 非功能需求

### 3.1 断点策略

| 断点 | 宽度 | 布局 |
|------|------|------|
| `sm` | < 640px | 移动端单栏 + BottomNav |
| `md` | 640px - 1024px | 平板端双栏（侧边栏 + 内容） |
| `lg` | 1024px - 1280px | 桌面端双栏（加宽） |
| `xl` | > 1280px | 桌面端三栏（可选详情面板） |

### 3.2 Layout 组件

```tsx
// components/Layout.tsx
export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="flex min-h-screen">
      {/* 桌面侧边栏，移动端隐藏 */}
      <aside className="hidden md:flex md:w-64 flex-col border-r">
        <SideNav />
      </aside>
      
      {/* 主内容区 */}
      <main className="flex-1 max-w-4xl mx-auto px-4">
        {children}
      </main>
      
      {/* 移动端底部导航，桌面隐藏 */}
      <div className="md:hidden">
        <BottomNav />
      </div>
    </div>
  );
}
```

### 3.3 非功能需求

- **渐进增强**：移动端优先，桌面端增强
- **一致性**：AIConfig 的 `max-w-[430px]` 硬编码移除，统一跟随容器策略
- **可维护性**：布局逻辑集中在 `Layout` 组件，页面组件不直接处理响应式容器

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📋 响应式审计 (20 min)
  - 遍历所有 `max-w-md` 和硬编码宽度
  - 列出需要修改的文件

- [ ] **Task 1.2** — 🔧 SideNav 组件 (40 min)
  - 创建 `components/SideNav.tsx`
  - 与 BottomNav 共享导航项
  - 桌面可见，移动隐藏

- [ ] **Task 1.3** — 🔧 AppLayout 容器组件 (30 min)
  - 创建 `components/Layout.tsx`
  - 断点布局切换

- [ ] **Task 1.4** — 🔧 各页面容器适配 (60 min)
  - 移除 `max-w-md` 限制
  - 适配表格/列表/卡片在宽屏下的布局

- [ ] **Task 1.5** — 🔧 BottomNav 条件显示 (10 min)
  - 桌面端隐藏 BottomNav
  - `pb-24` 等安全区仅在移动端保留

- [ ] **Task 1.6** — ✅ 验证 (30 min)
  - Chrome DevTools 各断点验证
  - 移动端不退化
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | 360px 宽度 | 移动端单栏 + BottomNav |
| T2 | 768px 宽度 | 侧边栏 + 内容区双栏 |
| T3 | 1280px 宽度 | 内容区加宽 |
| T4 | 桌面端 BottomNav | 不可见 |
| T5 | 平板端 SideNav | 可见且导航正常 |
| T6 | AIConfig 页 — 全宽 | 不被 `430px` 限制 |
| T7 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-016：移动优先渐进增强，而非桌面先行

- **背景**：当前仅有移动端布局，且大部分用户通过手机使用 Telegram。
- **决定**：保持移动端优先策略，桌面端作为增强。
- **理由**：
  1. 现有代码基于移动端设计，渐进增强成本最低
  2. 避免桌面优先导致移动端退化风险
  3. Tailwind 默认移动优先（`md:` `lg:` 向上覆盖）
- **后果**：桌面端体验为增量改进，不影响当前移动端用户。
