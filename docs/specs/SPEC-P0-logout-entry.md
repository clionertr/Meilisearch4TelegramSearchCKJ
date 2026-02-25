# 功能名称：退出登录入口

> **定位**：WebUI 功能缺陷修复 — 用户当前无法退出登录，存在安全风险

---

## 1. 业务目标（一句话）

在 Settings 页面增加明确的退出登录入口，调用后端 `POST /api/v1/auth/logout` 并清除本地 token，确保用户可安全结束会话。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：退出入口可见
- **Given** 用户已登录并处于 Settings 页面
- **When** 滚动到页面底部
- **Then** 可看见 "Logout" 按钮，样式醒目（红色文字或红色边框按钮）

### AC-2：退出流程完整
- **Given** 用户点击 Logout 按钮
- **When** 弹出二次确认（如有 SPEC-P2-confirmation-dialog 则使用，否则用 `confirm()`）
- **Then** 确认后：
  1. 调用 `POST /api/v1/auth/logout`
  2. 清除 `localStorage` 中的 token
  3. 重定向到 `/login` 页

### AC-3：退出后不可访回
- **Given** 用户已退出
- **When** 手动输入 `/dashboard` URL
- **Then** 路由守卫拦截，重定向到 `/login`

---

## 3. 技术设计 & 非功能需求

### 3.1 实现位置

在 `Settings.tsx` 底部增加 Logout 按钮区域：

```tsx
<button
  onClick={handleLogout}
  className="w-full text-red-500 border border-red-300 rounded-xl py-3"
>
  <span className="material-symbols-outlined">logout</span>
  Logout
</button>
```

### 3.2 Logout 逻辑

```typescript
// api/auth.ts — 已有 logout 方法
export const logout = () => api.post('/auth/logout');

// Settings.tsx
const handleLogout = async () => {
  if (!confirm('Are you sure you want to logout?')) return;
  await logout();
  localStorage.removeItem('auth_token');
  navigate('/login');
};
```

### 3.3 非功能需求

- **安全性**：退出后立即清除所有凭据
- **降级**：即使后端 `/logout` 失败，仍清除本地 token 并跳转

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔧 Settings 页增加 Logout 按钮 (20 min)
  - 在 Settings 页面底部 BottomNav 上方添加 Logout 按钮
  - 样式：红色文字 + 边框，匹配暗色主题

- [ ] **Task 1.2** — 🔧 Logout 逻辑实现 (15 min)
  - 调用 `POST /api/v1/auth/logout`
  - 清除 `localStorage` token
  - 导航到 `/login`
  - 错误降级：后端失败也清除本地凭据

- [ ] **Task 1.3** — ✅ 验证 (10 min)
  - 退出后无法通过 URL 直接访问受保护页面
  - `npm run build` 零错误

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| T1 | Settings 页面可见 Logout 按钮 | 按钮存在于页面底部 |
| T2 | 点击 Logout → 确认 | 跳转到 `/login`，token 已清除 |
| T3 | 点击 Logout → 取消 | 留在 Settings 页，token 保留 |
| T4 | Logout 后访问 `/dashboard` | 被重定向到 `/login` |
| T5 | 后端 `/logout` 返回 500 | 仍然清除本地 token 并跳转 |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-008：Logout 按钮放置在 Settings 页而非 Profile 页

- **背景**：Profile 页当前不存在（gap analysis 中标记为 ❌），且短期内不计划实现。
- **决定**：将 Logout 入口放在 Settings 页面底部。
- **理由**：Settings 是唯一的账户管理相关页面，用户直觉上会在此寻找退出入口。
- **后果**：若未来实现 Profile 页，可同时在 Profile 增加退出入口。
