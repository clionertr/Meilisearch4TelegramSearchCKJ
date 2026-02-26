# 功能名称：WebUI 接入运行控制与同步策略 API

## 1. 业务目标（一句话）

让用户在前端「设置」页即可完成 Telegram 运行状态控制（启动/停止）和同步策略维护（白/黑名单增删），不再依赖命令行或手工接口调用。

## 2. 验收标准（Given-When-Then 格式）

### AC-1：运行状态可见
- **Given** 用户已登录并进入设置页
- **When** 页面加载完成
- **Then** 能看到 `/api/v1/client/status` 返回的当前状态（`running/stopped/starting/stopping`）、是否 API-only、最后动作来源和最近错误信息（若有）

### AC-2：启动客户端
- **Given** 当前状态为未运行且非 API-only
- **When** 用户点击「启动同步引擎」
- **Then** 前端调用 `POST /api/v1/client/start`，按钮进入 pending 态，成功后状态刷新并显示成功提示

### AC-3：停止客户端
- **Given** 当前状态为运行中
- **When** 用户点击「停止同步引擎」
- **Then** 前端调用 `POST /api/v1/client/stop`，按钮进入 pending 态，成功后状态刷新并显示成功提示

### AC-4：API-only 保护
- **Given** 后端运行在 API-only 模式
- **When** 用户访问运行控制区
- **Then** 页面明确展示“API-only 模式不可启动 Telegram 客户端”，并禁用启动按钮

### AC-5：配置加载
- **Given** 用户已登录
- **When** 设置页加载完成
- **Then** 前端调用 `GET /api/v1/config` 并展示白名单、黑名单、owner_ids（只读）及基础搜索配置摘要

### AC-6：白名单新增
- **Given** 用户在白名单输入框输入有效整数 ID
- **When** 点击「添加到白名单」
- **Then** 前端调用 `POST /api/v1/config/whitelist`，成功后列表即时更新并显示成功提示

### AC-7：黑名单新增
- **Given** 用户在黑名单输入框输入有效整数 ID
- **When** 点击「添加到黑名单」
- **Then** 前端调用 `POST /api/v1/config/blacklist`，成功后列表即时更新并显示成功提示

### AC-8：列表移除
- **Given** 白名单或黑名单中存在某个 ID
- **When** 用户点击该 ID 的移除按钮
- **Then** 前端调用对应 DELETE 接口并刷新配置，UI 与后端数据保持一致

### AC-9：错误体验统一
- **Given** API 返回 4xx/5xx
- **When** 任一控制/配置动作失败
- **Then** 页面展示可读错误文案（优先使用后端 detail.message），并保持可恢复交互状态

## 3. 简单的技术设计 & 非功能需求

### 3.1 API 层
- 新增 `src/api/control.ts`：
  - `GET /client/status`
  - `POST /client/start`
  - `POST /client/stop`
- 复用现有 `src/api/config.ts`，不改变接口契约。

### 3.2 数据层（React Query）
- 新增 `src/hooks/queries/useControl.ts`
  - `useClientStatus()`：状态轮询（10 秒）
  - `useStartClient()`：启动 mutation，成功后失效 `['clientStatus']`
  - `useStopClient()`：停止 mutation，成功后失效 `['clientStatus']`
- 新增 `src/hooks/queries/useConfig.ts`
  - `useSystemConfig()`：读取配置
  - `useAddToWhitelist()/useRemoveFromWhitelist()`
  - `useAddToBlacklist()/useRemoveFromBlacklist()`
  - 所有成功回调统一失效 `['systemConfig']`

### 3.3 UI 层（Settings 页面）
- 新增两个功能区块：
  - `Runtime Control`：状态 badge + 启停按钮 + last_error 提示
  - `Sync Policy`：白/黑名单可编辑 chips + 输入框添加 + owner_ids 只读展示
- 交互原则：
  - 所有关键动作具备 pending 反馈
  - 输入非法 ID（非整数）立即前端拦截
  - 成功/失败反馈统一 toast

### 3.4 非功能需求
- **可用性**：每个按钮在 pending 时禁用，避免重复提交
- **一致性**：成功后必须走 query invalidation，避免局部状态与后端不一致
- **可观测性**：继续复用 axios 拦截器 telemetry（request_id 串联）
- **兼容性**：保持移动端单列布局和桌面端现有布局，不破坏现有页面结构

## 4. 任务拆分（我会拆到每个任务不超过 30-60 分钟能完成）

- [x] Task 1.1 新增运行控制 API 与 hooks（`control.ts` + `useControl.ts`）
- [x] Task 1.2 新增配置策略 hooks（`useConfig.ts`）
- [x] Task 1.3 Settings 页面接入运行控制区块（状态展示 + 启停动作 + 错误显示）
- [x] Task 1.4 Settings 页面接入策略管理区块（白/黑名单增删 + owner_ids 展示）
- [x] Task 1.5 补充中英文 i18n 文案，统一交互文案语义
- [x] Task 1.6 本地构建验证（`npm run build`）并修复类型/构建问题

## 5. E2E 测试用例清单

1. 登录后进入设置页，运行控制模块显示当前状态（含 state 文案）。
2. 在可启动状态下点击“启动同步引擎”，按钮变 loading，状态刷新为运行态。
3. 在运行态点击“停止同步引擎”，按钮变 loading，状态刷新为停止态。
4. API-only 模式下访问设置页，显示模式提示且启动按钮禁用。
5. 输入有效整数到白名单并提交，列表新增该 ID。
6. 输入有效整数到黑名单并提交，列表新增该 ID。
7. 点击白名单条目的删除按钮，条目被移除且后端返回成功。
8. 输入非法 ID（空值、非数字、小数），前端拦截并提示，不发起请求。
9. 人工注入 4xx/5xx（或断网）后执行操作，页面显示可读错误且可继续操作。
10. 执行 `npm run build` 成功通过。

## 6. 实现笔记 & 架构决策记录（ADR）

### ADR-013：将“运行控制 + 策略管理”收敛到 Settings 页面
- **背景**：当前 Settings 已是运维入口，用户心智最稳定。
- **决策**：不新增独立页面，直接在 Settings 增加可操作区块。
- **理由**：减少导航切换，降低操作成本；实现范围可控。
- **影响**：Settings 信息密度提高，需要通过分组标题与卡片层次维持可读性。

### ADR-014：配置增删采用“请求成功后失效并重拉”而非本地乐观更新
- **背景**：配置更新涉及白/黑名单去重与服务端规则校验，直接本地拼接存在偏差风险。
- **决策**：所有 mutation 成功后统一 invalidation `['systemConfig']`。
- **理由**：后端作为单一真源，前端状态不会漂移。
- **影响**：成功后会有一次轻量重拉，但换来更高一致性与更低复杂度。
