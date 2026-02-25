# 功能名称：无用依赖清理 & 死代码移除

> **定位**：WebUI 代码卫生 — 降低维护复杂度并减少安全审计噪音

---

## 1. 业务目标（一句话）

移除 AI Studio 遗留的 `@google/genai` 依赖与 `geminiService.ts` 死代码，清理未使用旧类型，并给 Profile 按钮提供明确的“未实现”反馈。

---

## 2. 验收标准（Given-When-Then 格式）

### AC-1：依赖移除
- **Given** `@google/genai` 已从 `webui-example/package.json` 移除
- **When** 运行 `npm install && npm run build`
- **Then** 构建零错误，`npm ls @google/genai` 不再列出该包

### AC-2：死代码移除
- **Given** `src/services/geminiService.ts` 已删除
- **When** 执行 `grep -r "gemini\|GeminiService\|@google/genai" webui-example/src/`
- **Then** 结果为空

### AC-3：旧类型清理
- **Given** `src/types/index.ts` 中未被使用的旧 `SearchResult` 接口已删除
- **When** 执行 `rg -n "SearchResult" webui-example/src`
- **Then** 仅保留 API 层真实响应类型定义（如 `src/api/search.ts`）

### AC-4：文档与示例环境变量同步
- **Given** 项目不再使用前端 Gemini 直连
- **When** 检查可审计文件（`README.md`、`CLAUDE.md`、`.env.example`）
- **Then** 不再要求设置 `GEMINI_API_KEY`

### AC-5：Profile 按钮状态明确
- **Given** BottomNav 的 Profile 按钮尚未实现完整页面
- **When** 用户点击 Profile
- **Then** 出现明确反馈（如 `Coming Soon` toast）或按钮以禁用态展示并标注 `Soon`

> 说明：`webui-example/.env.local` 为本地开发文件（被 `*.local` 忽略），不纳入 PR 强制验收。

---

## 3. 技术设计 & 非功能需求

### 3.1 依赖影响分析

#### `@google/genai`

- 当前唯一实现位于 `src/services/geminiService.ts`
- 该文件使用 `process.env.API_KEY`（Vite 前端不推荐）
- 业务主路径由后端 `/api/v1/ai/config` 管理 AI 配置，前端无需直连第三方 SDK

#### `types/index.ts` 旧类型

`types/index.ts` 的 `SearchResult` 与当前搜索 API 返回结构不一致，属于历史遗留 mock 类型。应由 `src/api/search.ts` 维护真实响应类型。

### 3.2 metadata.json 评估

`webui-example/metadata.json` 需先确认是否被构建或运行时读取：
- 若无引用，删除
- 若有引用，补充用途说明并保留

### 3.3 非功能需求

- **可审计性**：依赖树和代码引用均可机器验证
- **安全性**：减少前端不必要第三方 SDK 与潜在密钥暴露面
- **稳健性**：不把“打包体积必然下降”作为硬验收（tree-shaking 下可能无显著变化）

---

## 4. 任务拆分

- [ ] **Task 1.1** — 🔍 引用范围确认（10 min）
  - `grep -r "geminiService\|GeminiService\|@google/genai" webui-example/src/`
  - `rg -n "SearchResult" webui-example/src`
  - `rg -n "metadata.json" webui-example`

- [ ] **Task 1.2** — 🗑️ 删除死代码文件（5 min）
  - 删除 `webui-example/src/services/geminiService.ts`
  - 如 `services/` 目录为空，按需删除目录

- [ ] **Task 1.3** — 🗑️ 移除依赖（5 min）
  - `npm uninstall @google/genai`
  - 确认 `package.json` 与 `package-lock.json` 更新

- [ ] **Task 1.4** — 🔧 清理旧类型（15 min）
  - 移除 `types/index.ts` 中未使用 `SearchResult`
  - `ActivityItem/ChatItem` 仅在仍有引用时保留

- [ ] **Task 1.5** — 🔧 Profile 按钮状态处理（10 min）
  - 方案 A：点击 toast `Coming Soon`
  - 方案 B：按钮禁用态 + `Soon` 标签
  - 以“反馈明确、交互干扰最小”为准

- [ ] **Task 1.6** — 📝 文档与示例环境变量同步（10 min）
  - 更新 `README.md`、`CLAUDE.md`
  - 更新 `.env.example`（移除 Gemini 直连要求）

- [ ] **Task 1.7** — 🗑️ metadata 清理（5 min）
  - 无引用则删除 `metadata.json`

- [ ] **Task 1.8** — ✅ 验证（10 min）
  - `npm run build`
  - `npx tsc --noEmit`
  - 手动检查 Dashboard / Search / Settings 页面无回退

---

## 5. E2E 测试用例清单

| # | 测试用例 | 预期结果 |
|---|---------|---------|
| 1 | `npm run build` | 零错误 |
| 2 | `npm ls @google/genai 2>&1` | `empty` / 未安装 |
| 3 | `grep -r "gemini\|@google/genai" webui-example/src/` | 无结果 |
| 4 | `ls webui-example/src/services/geminiService.ts 2>&1` | `No such file` |
| 5 | `rg -n "SearchResult" webui-example/src` | 不再命中 `src/types/index.ts` 的旧定义 |
| 6 | `rg -n "GEMINI_API_KEY" webui-example/README.md webui-example/CLAUDE.md .env.example` | 无结果 |
| 7 | 点击 BottomNav Profile | 有明确反馈（toast 或禁用标识） |
| 8 | `rg -n "metadata.json" webui-example/src webui-example` | 无运行时引用（或有清晰说明） |

---

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-005：直接删除 `geminiService` 与 `@google/genai`

- **背景**：该服务不在当前主功能调用链中，且前端直持 API Key 不符合安全边界。
- **决定**：删除文件与依赖，不做“先保留后迁移”。
- **理由**：
  1. 当前 AI 配置走后端接口
  2. 减少供应链与审计噪音
  3. 避免误导开发者在前端直接接入密钥

### ADR-006：类型定义以 API 模块为源

- **背景**：全局旧 `SearchResult` 与真实响应结构不一致。
- **决定**：删除旧定义，类型由 `src/api/*` 维护并导出。
- **后果**：页面层按 API 类型消费，降低“文档类型”与“真实返回”偏差。

### ADR-007：本地环境文件不纳入强验收

- **背景**：`*.local` 被 gitignore 忽略，团队成员本地内容可能不同。
- **决定**：以仓库可审计文件（README/CLAUDE/.env.example）为准。
- **后果**：验收结果可复现，减少“本地文件差异”争议。
