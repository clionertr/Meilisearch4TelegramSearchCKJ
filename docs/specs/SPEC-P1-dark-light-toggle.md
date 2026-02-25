# 功能名称：暗色/亮色模式切换

> **定位**：WebUI 外观增强 — 让用户自主选择主题，不再强制锁定 `<html class="dark">`

---

## 1. 业务目标（一句话）

实现 Settings 页面的暗色/亮色模式切换控件，持久化用户偏好到 localStorage，并支持第三选项"跟随系统"。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：切换可用
- **Given** Settings 页面存在主题切换控件
- **When** 用户从 Dark 切换到 Light
- **Then** `<html>` 移除 `dark` class，页面立即切换为亮色配色

### AC-2：偏好持久化
- **Given** 用户选择 Light 模式
- **When** 关闭浏览器后重新打开
- **Then** 仍为 Light 模式（从 `localStorage` 读取）

### AC-3：跟随系统
- **Given** 用户选择 "System" 选项
- **When** 操作系统偏好为暗色
- **Then** 页面为暗色；系统切换为亮色后页面响应切换

### AC-4：初始化无闪烁
- **Given** 用户偏好为 Light，但默认 HTML 有 `dark` class
- **When** 页面加载
- **Then** 在 React hydration 前通过内联 `<script>` 移除 `dark` class，避免闪烁 (FOUC)

---

## 3. 技术设计 & 非功能需求

### 3.1 主题 Hook

```typescript
// hooks/useTheme.ts
type Theme = 'dark' | 'light' | 'system';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem('theme') as Theme) || 'system'
  );

  useEffect(() => {
    const root = document.documentElement;
    const isDark = theme === 'dark' ||
      (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    root.classList.toggle('dark', isDark);
    localStorage.setItem('theme', theme);
  }, [theme]);

  return { theme, setTheme };
}
```

### 3.2 防闪烁内联脚本

在 `index.html` `<head>` 中：

```html
<script>
  (function() {
    var t = localStorage.getItem('theme');
    var dark = t === 'dark' || (!t || t === 'system') &&
      matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.classList.toggle('dark', dark);
  })();
</script>
```

### 3.3 UI 控件

Settings 页新增 "Appearance" 区域，三选一按钮组：
- ☀️ Light
- 🌙 Dark
- 💻 System

### 3.4 依赖前置

> [!IMPORTANT]
> 本 SPEC 依赖 `SPEC-P0-tailwind-v4-unification` 完成。暗色模式必须为 class-based 策略（`@custom-variant dark`），否则切换不生效。

### 3.5 非功能需求

- **无闪烁**：使用 `<head>` 内联脚本保证首帧正确
- **响应式**：`system` 选项监听 `prefers-color-scheme` 变化事件
- **兼容**：AIConfig 页面的强制暗色逻辑需移除，改为跟随全局主题

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 useTheme Hook (20 min)
  - 实现 `useTheme.ts`
  - localStorage 读写 + `classList.toggle` 逻辑
  - `system` 模式监听 `matchMedia` 变化

- [ ] **Task 1.2** — 🔧 防闪烁脚本 (10 min)
  - 在 `index.html` `<head>` 添加内联 `<script>`
  - 移除原有 `<html class="dark">` 硬编码

- [ ] **Task 1.3** — 🔧 Settings 页 UI 控件 (25 min)
  - 新增 "Appearance" 区域
  - 三选一按钮组（Light / Dark / System）
  - 匹配现有设计语言

- [ ] **Task 1.4** — 🔧 AIConfig 页适配 (15 min)
  - 移除 AIConfig 的强制暗色样式
  - 改为跟随全局主题变量

- [ ] **Task 1.5** — ✅ 验证 (15 min)
  - Dark → Light → System 切换流畅
  - 持久化生效
  - 无 FOUC 闪烁
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Settings 页切换到 Light | 全局切换为亮色，所有页面生效 |
| T2 | 切换后刷新页面 | 主题保持不变 |
| T3 | 选择 System + 系统暗色偏好 | 页面为暗色 |
| T4 | System 模式 + 系统切换为亮色 | 页面实时跟随切换 |
| T5 | 首次加载（无 localStorage 记录） | 默认 System 行为 |
| T6 | AIConfig 页在 Light 模式 | 正确展示亮色样式 |
| T7 | `npm run build` | 零错误 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-010：三选项模式（Dark / Light / System）而非二选

- **背景**：当前硬编码 `<html class="dark">`，用户无选择权。
- **决定**：提供三选项，默认 "System"。
- **理由**：
  1. 用户可能在日间使用亮色模式阅读搜索结果
  2. "System" 选项零配置跟随 OS，满足多数用户
  3. 与主流应用（Twitter, Discord）UX 模式一致
- **后果**：需维护亮色主题下的变量与对比度，但暗色变量统一后此开销可控。
