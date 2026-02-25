# 功能名称：页面过渡动画

> **定位**：WebUI 交互增强 — 让页面切换从"硬切"升级为流畅过渡，提升感知品质

---

## 1. 业务目标（一句话）

为路由切换添加淡入/滑动过渡动画，为列表项添加入场 stagger 动画，消除当前全部"硬切"的割裂感。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：路由过渡动画
- **Given** 用户从 Dashboard 切换到 Search
- **When** 路由变化
- **Then** 旧页面淡出 + 新页面淡入（或水平滑动），过渡时长 200-300ms

### AC-2：列表入场动画
- **Given** Dashboard ActivityList 数据加载完成
- **When** 列表项渲染
- **Then** 各项依次入场（stagger delay 50ms），带淡入 + 微上移效果

### AC-3：尊重用户偏好
- **Given** 用户系统设置 `prefers-reduced-motion: reduce`
- **When** 页面切换
- **Then** 跳过所有动画，直接渲染

---

## 3. 技术设计 & 非功能需求

### 3.1 方案选型

| 方案 | 优点 | 缺点 |
|------|------|------|
| `framer-motion` | 功能强大、API 优雅、社区大 | 体积较大(~30KB gzip) |
| CSS `@view-transition` | 原生零依赖 | 浏览器兼容有限、不支持 stagger |
| CSS `@keyframes` + React 手动管理 | 零依赖 | 复杂度高、难维护 |

**推荐**: `framer-motion`，因已是 React 生态标准选择，且后续可复用 `AnimatePresence` 实现 modal/sheet 动画。

### 3.2 路由过渡封装

```tsx
// components/PageTransition.tsx
import { motion, AnimatePresence } from 'framer-motion';

const variants = {
  enter: { opacity: 0, x: 20 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 },
};

export function PageTransition({ children }: PropsWithChildren) {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div key={location.pathname}
        variants={variants}
        initial="enter" animate="center" exit="exit"
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
```

### 3.3 非功能需求

- **性能**：动画使用 `transform` + `opacity`（GPU 加速），不触发 layout
- **可访问性**：检测 `prefers-reduced-motion` 并禁用动画
- **不阻塞**：过渡期间页面可交互，不 block 用户操作

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📦 安装 framer-motion (10 min)
  - 安装依赖
  - 验证与现有 Vite / React 版本兼容

- [ ] **Task 1.2** — 🔧 PageTransition 组件 (30 min)
  - 创建 `components/PageTransition.tsx`
  - 在 `App.tsx` 路由层包裹

- [ ] **Task 1.3** — 🔧 列表入场动画 (30 min)
  - Dashboard ActivityList 添加 stagger 动画
  - Search 结果列表添加 stagger 动画
  - SyncedChats 列表添加 stagger 动画

- [ ] **Task 1.4** — 🔧 reduced-motion 适配 (10 min)
  - 检测 `prefers-reduced-motion`
  - 条件禁用所有 framer-motion 动画

- [ ] **Task 1.5** — ✅ 验证 (15 min)
  - 各路由切换流畅
  - 列表入场自然
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Dashboard → Search 切换 | 淡入/滑动过渡动画 |
| T2 | Search → Settings 切换 | 过渡动画一致 |
| T3 | Dashboard ActivityList 加载 | 列表项 stagger 入场 |
| T4 | 设置 `prefers-reduced-motion: reduce` | 无动画，直接渲染 |
| T5 | 快速连续切换 3 个 tab | 动画不堆叠/卡顿 |
| T6 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-011：选用 framer-motion 而非 CSS-only

- **背景**：项目需要路由过渡 + 列表 stagger + 未来 modal/sheet 动画。
- **决定**：引入 `framer-motion`。
- **理由**：
  1. `AnimatePresence` 完美支持路由 exit 动画（CSS 无法做到）
  2. Stagger 动画声明式 API 远比手动管理 CSS delay 简洁
  3. 后续 modal / bottom sheet / 确认对话框可复用
- **后果**：bundle 增加约 30KB (gzip)，可通过 tree-shaking + 代码分割减轻影响。
