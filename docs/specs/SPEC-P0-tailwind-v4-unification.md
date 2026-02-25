# 功能名称：Tailwind CSS v4 配置统一

> **定位**：WebUI 构建基础设施修复 — 消除 v3/v4 共存与暗色策略漂移导致的不可预测样式行为

---

## 1. 业务目标（一句话）

删除遗留 `tailwind.config.js`，统一为 Tailwind v4 CSS-first 配置（`@theme` / `@plugin` / `@custom-variant`），并明确暗色模式为 **class-based**，确保开发与构建行为一致。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：v3 配置彻底移除
- **Given** `webui-example/tailwind.config.js` 已删除
- **When** 运行 `npm run build`
- **Then** 构建零错误，页面可正常加载，现有 className 无需改动

### AC-2：forms 插件在 v4 配置中显式启用（必做）
- **Given** `index.css` 已包含 `@plugin "@tailwindcss/forms";`
- **When** 登录页渲染 `form-input` 输入框
- **Then** 输入框仍保留 forms 插件样式（边框、聚焦环、可读性）

### AC-3：暗色模式策略固定为 class-based
- **Given** `index.css` 已定义 `@custom-variant dark (&:where(.dark, .dark *));`
- **When** `<html class="dark">` 存在并访问 Dashboard / Search / Settings
- **Then** `dark:` 变体按 `.dark` 类生效，不依赖系统 `prefers-color-scheme`

### AC-4：v3 残留语法清理完成
- **Given** 项目已迁移到 v4 CSS-first
- **When** 执行：
  - `grep -r "tailwind.config" webui-example/`
  - `grep -r "@tailwind base\|@tailwind components\|@tailwind utilities" webui-example/src/`
- **Then** 结果为空

---

## 3. 技术设计 & 非功能需求

### 3.1 当前问题

| 文件 | 现状 | 风险 |
|------|------|------|
| `tailwind.config.js` | v3 配置（`darkMode: 'class'`、`content`、`plugins`） | 与 v4 CSS-first 并存，行为歧义 |
| `postcss.config.js` | 已使用 `@tailwindcss/postcss` | 正确，无需修改 |
| `src/index.css` | 有 `@theme`，但未显式声明 forms 插件与 dark 自定义变体 | 表单样式/暗色触发策略不可控 |

**关键结论**：
1. 配置入口必须收敛到 `index.css`。
2. `@tailwindcss/forms` 不应作为“可选检查项”，而应作为迁移必做项。
3. 暗色策略必须显式声明为 class-based，避免落回 `prefers-color-scheme` 媒体查询语义。

### 3.2 方案

```mermaid
graph LR
    A[tailwind.config.js v3] -->|删除| X[×]
    B[index.css @theme] --> C[主题变量唯一来源]
    D[index.css @plugin forms] --> E[表单样式稳定]
    F[index.css @custom-variant dark] --> G[class-based dark]
    H[postcss.config.js] --> I[@tailwindcss/postcss 保留]
```

实施细节：
1. 删除 `webui-example/tailwind.config.js`
2. 在 `webui-example/src/index.css` 增加：
   - `@plugin "@tailwindcss/forms";`
   - `@custom-variant dark (&:where(.dark, .dark *));`
3. 若自动内容检测遗漏入口，再补 `@source "../index.html";`
4. 保持现有 `@theme` 颜色/字体变量不变，禁止组件侧批量重写 class

### 3.3 非功能需求

- **零行为回退**：不允许登录表单与现有暗色 UI 视觉退化
- **可维护性**：配置源头单一（`index.css`）
- **可验证性**：构建后可通过 grep 快速验证 dark/form 关键产物

---

## 4. 任务拆分

- [ ] **Task 1.1** — 📋 迁移前审计（10 min）
  - `grep -r "darkMode\|@tailwind\|tailwind.config\|form-input" webui-example/`
  - 记录 `tailwind.config.js` 中仍需保留的配置项

- [ ] **Task 1.2** — 🔧 CSS-first 配置补齐（20 min）
  - 在 `index.css` 添加 `@plugin "@tailwindcss/forms";`
  - 添加 `@custom-variant dark (&:where(.dark, .dark *));`
  - 必要时添加 `@source "../index.html";`

- [ ] **Task 1.3** — 🗑️ 删除 v3 配置（5 min）
  - 删除 `webui-example/tailwind.config.js`

- [ ] **Task 1.4** — ✅ 构建与页面验证（20 min）
  - `npm run build`
  - 访问 Login / Dashboard / Search / Settings
  - 核验 `<html class="dark">` 下 `dark:` 变体与 `form-input` 均生效

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| 1 | `npm run build` | 零错误 |
| 2 | `ls webui-example/tailwind.config.js 2>&1` | `No such file` |
| 3 | `grep -r "@plugin \"@tailwindcss/forms\"" webui-example/src/index.css` | 命中 1 条 |
| 4 | `grep -r "@custom-variant dark" webui-example/src/index.css` | 命中 1 条 |
| 5 | 打开 `/login` 检查 `form-input` | 样式正常，聚焦态可见 |
| 6 | 打开任意页面，保留 `<html class="dark">` | `dark:` 样式生效 |
| 7 | `grep -r "@tailwind base\|@tailwind components\|@tailwind utilities" webui-example/src/` | 无结果 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-001：采用 CSS-first + class-based dark 的组合

- **背景**：项目已迁移到 Tailwind v4（PostCSS 插件与 `@theme` 已在位），但仍保留 v3 JS 配置与隐式 dark/forms 逻辑。
- **决定**：
  1. 删除 `tailwind.config.js`
  2. 在 `index.css` 显式声明 `@plugin "@tailwindcss/forms"`
  3. 在 `index.css` 显式声明 `@custom-variant dark (&:where(.dark, .dark *))`
- **理由**：
  1. 消除双配置入口
  2. 避免 forms 样式在迁移后静默丢失
  3. 保证暗色模式与当前 `<html class="dark">` 策略一致
- **后果**：后续新增主题、插件、变体统一在 `index.css` 管理，不再回退 JS 配置。
