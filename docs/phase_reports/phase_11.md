# Phase 11 Report：Streamlit 用户界面与 IT 工单数据分析 Dashboard

## 结论

**CONDITIONAL PASS（工程 PASS；学习验收待完成）。** 本阶段使用 Streamlit 提供 IT Support Chat 和 Analytics Dashboard，没有开发 Next.js 或独立前端产品。UI 只调用 FastAPI；数据库查询、反馈约束、确认状态机、权限、统计口径和 Evaluation artifact 读取全部保留在后端。

固定虚构 seed 和 Fake Provider 可以完整演示知识问答、三类诊断、R1 确认/取消、创建本地工单、用户反馈和 Dashboard。没有连接真实企业系统、执行真实权限变更或增加任意命令工具。

## 验收矩阵

| 要求 | 状态 | 实现证据 | 验证证据 |
| --- | --- | --- | --- |
| 输入问题、模拟身份和多轮对话 | 完成 | `apps/ui/chat_page.py` | AppTest + 实际浏览器 VPN 流程 |
| 展示 Agent 状态 | 完成 | final state + steps summary | completed / vpn_diagnosis / 10 steps |
| 展示 Citation | 完成 | response `final_response.citations` projection | UI state unit + 实际浏览器知识问答 |
| 展示工具和审计 | 完成 | Tool Execution table + node trace；确认后重新读取 Run | confirm HTTP 演示刷新后包含 `create_ticket` |
| 待确认、确认和取消 | 完成 | `/agent/confirm`、`/agent/cancel` | owner/replay/wrong actor/state integration |
| 展示 Ticket Number | 完成 | confirmation result projection | HTTP 创建 `IT-20260801-000001` |
| resolved/unresolved Feedback | 完成 | `feedback` 表、`POST /feedback` | success/replay/conflict/access tests |
| 全部 Dashboard 指标 | 完成 | `/analytics/summary` | 真实 PostgreSQL 聚合 integration |
| UI 不访问数据库 | 完成 | HTTP-only client | forbidden import/SQL scan + client unit |
| UI 不复制业务逻辑 | 完成 | Policy/metric/state 在后端 | code review + API contract |
| seed Mock 数据 | 完成 | `scripts.seed_phase11_demo` | 连续执行两次精确计数不变 |
| 简洁图表 | 完成 | Streamlit metric/bar chart/dataframe | 实际浏览器截图 |
| README 截图和流程 | 完成 | README Phase 11 sections | 两张实际 PNG |

## 架构与职责边界

```text
Streamlit Chat / Dashboard
  → ITSupportAPIClient (HTTP only)
  → FastAPI request schemas + authorization
  → Agent / Service Desk / Feedback / Analytics services
  → PostgreSQL agent_runs / steps / tools / tickets / feedback
  → bounded SQL aggregates
  → pandas label/sort/type projection
  → AnalyticsSummaryResponse
  → Streamlit presentation-only charts

Evaluation immutable JSON
  → backend AnalyticsService only
  → bounded recent-evaluation projection
  → FastAPI response
  → Streamlit table
```

Streamlit 可以把后端已返回的 `label/count` 转成 DataFrame 供图表组件显示，但不能自行决定“什么是自助解决”“什么是转人工”，也不能导入数据库或直接读 Evaluation 文件。

## IT Support Chat

页面提供：

- sidebar 模拟 actor ID 和 employee/it_support/project_maintainer/guest 角色；切换身份会重置本地会话状态；
- session 中维护 Conversation ID 和页面消息，实现多轮对话；
- 展示 final status、intent、Agent Step 数和 Tool Execution 数；
- 展开显示最终回答实际引用的 Citation、工具名称/状态/risk/side effect/attempt/latency/error 和 Agent node trace；
- 展示 pending action 的脱敏参数摘要和 impact summary；
- 原 actor 可确认或取消，执行成功后显示 Ticket Number；
- 最后一个 Agent Run 可以提交 resolved/unresolved、1–5 satisfaction 和可选 comment。

UI 不展示模型私有 reasoning；它只展示服务器持久化的确定性 route summary、状态、Citation 和审计字段。

## Feedback 合同

`feedback` 以 Agent Run 为业务主键：

- `agent_run_id` 唯一，避免重复反馈抬高统计分母；
- `idempotency_key` 唯一，完全相同请求可安全 replay；
- actor/role 从 Run persisted user context 校验，不接受对他人 Run 的反馈；
- 可选 Ticket 必须属于 actor，且 `source_agent_run_id` 与 Feedback Run 相同；
- satisfaction 只允许 1–5；comment 可选且有长度上限；
- 已保存 Feedback 不允许修改，变化值 replay 返回 409。

当前不可编辑是个人项目的明确简化。生产设计需要另行决定追加式修改历史、删除权、PII 和保留周期。

## 取消确认

Phase 8 已有 pending/executed/failed；Phase 11 增加 cancelled 终态：

- 只有原 actor/role 可取消；
- 只有 pending 可首次取消；
- 同一 actor 对 cancelled 再次调用是幂等 replay；
- cancelled 后 confirm 返回 409；
- 成功状态更新与 allow audit 在一个数据库事务；
- access/state denial 也写 deny audit，但不泄露参数正文。

## Dashboard 统计口径

| 指标 | 后端定义 | 分母/样本 |
| --- | --- | --- |
| Ticket 分类 | 时间窗内 Ticket category 计数 | Tickets |
| VPN/Outlook/账号数量 | 时间窗内 Agent intent 计数 | Agent Runs |
| 自助解决率 | resolved Feedback 且 Run 无来源 Ticket | 全部 Feedback |
| 转人工率 | escalated Run 或 Run 有来源 Ticket | 全部 Agent Runs |
| 平均 Agent 步骤 | 每 Run step count，零 Step 保留 | Agent Runs |
| 平均工具调用 | 每 Run tool count，零 Tool 保留 | Agent Runs |
| 平均响应时间 | `completed_at - started_at` | 已完成时间存在的 Runs |
| 工具成功率 | succeeded Tool Executions | Tool Executions |
| 用户满意度 | 非空 1–5 rating 平均与分布 | 有 rating 的 Feedback |
| 高频失败原因 | Run 与 Tool 的非空结构化 error code 合并计数 | failed Runs + failed Tools |
| 最近评估 | immutable Evaluation JSON 摘要 | 有效且去重的 artifacts |

Ticket/Feedback 使用各自 `created_at`；Agent 指标使用 `agent_runs.started_at`；Tool 全局成功率使用 `tool_executions.started_at`。无适用样本返回 `value=null, sample_count=0`，不把“没有数据”显示为 0%。

Analytics endpoint 只允许拥有 `audit:read` 的本地支持角色。当前 actor ID 仍是本地模拟输入，不是可信 authentication；权限声明只适用于本地演示。

## 演示 seed

`python -m scripts.seed_phase11_demo` 要求 Fake Embedding 配置，先幂等导入和索引 6 份虚构知识，再使用固定 namespace UUID 和 `ON CONFLICT DO NOTHING` 写：

- 6 Agent Runs；
- 23 Agent Steps；
- 6 Tool Executions；
- 4 Tickets；
- 4 Feedback。

数据覆盖 VPN、Outlook、账号、工单请求、escalated、failed、成功工具、timeout、resolved/unresolved 和不同满意度。脚本不删除或覆盖已有数据，不调用 FastAPI、LLM、真实 Embedding、Gateway 或外部 Adapter；Fake Embedding 只用于虚构知识索引。它只是本地开发 fixture，不是业务写入捷径。

## 真实演示结果

开发数据库升级到 `20260801_0013` 后，seed 返回预期精确计数。启动真实 FastAPI 与 Streamlit 后：

- HTTP VPN 请求：status `completed`，5 次 Tool Execution；
- HTTP 工单请求：产生 pending confirmation；原 actor 确认后 status `executed`；
- 创建本地 Ticket `IT-20260801-000001`；
- unresolved/3 分 Feedback 保存成功；
- Analytics 返回成功并包含 seed 与实时演示轨迹；
- 浏览器 Chat 页面显示 `completed`、`vpn_diagnosis`、10 Steps 和 5 Tools；
- 浏览器 Dashboard 显示统计卡片、四组简洁条形图和最近 Evaluation 表。

本次独立收尾再次执行：知识问答为 `completed` 且只展示最终回答采用的 1 条 Citation；工单确认后为 `executed`，Ticket 为 `IT-20260801-000002`，刷新后的工具审计包含 `create_ticket`。两个 fail-closed 场景分别为 wrong actor cancel → 403 `confirmation_access_denied`，employee analytics → 403 `analytics_access_denied`。本轮浏览器自动化没有可靠触发 Dashboard radio 切换，因此只把 Chat 记为本轮浏览器复验；Dashboard 由既有实际截图、本轮 0-exception AppTest、Analytics HTTP 和 PostgreSQL integration 共同验收。

截图：

- `docs/screenshots/phase11-chat.png`；
- `docs/screenshots/phase11-dashboard.png`。

## 测试与验证

- 修改前全量：首次因 sandbox 禁止 localhost PostgreSQL 为 `6 failed, 138 passed, 88 errors`；获准访问同一隔离库后 `232 passed in 16.19s`；
- migration/Feedback/Analytics/cancel 聚焦：`6 passed in 2.17s`；
- Phase 11 组合聚焦：`11 passed in 2.38s`；
- UI client：`4 passed in 0.01s`；
- seed 幂等 integration：`1 passed in 0.33s`；
- 最后取消事务和自助口径修正：`5 passed in 2.26s`；
- 独立收尾必要回归：`14 passed in 2.79s`；
- 标准命令最终全量：`242 passed in 17.70s`；沙箱内首跑因 localhost PostgreSQL `Operation not permitted` 为 `7 failed, 144 passed, 91 errors`，获准访问同一隔离库后原命令通过；
- Streamlit AppTest：两页 0 exception；FastAPI unavailable 安全错误已验证；
- 开发数据库：`20260801_0013 (head)`；migration 往返 `0013 → 0012 → 0013` 已通过；
- Ruff `All checks passed!`；format `169 files already formatted`；compileall、pip check、Git whitespace 通过；开发/测试数据库均为 `20260801_0013 (head)`。

数据库语义测试使用真实隔离 PostgreSQL/pgvector，没有用 SQLite 或无意义 mock 替代。

## 代码入口

- `apps/ui/streamlit_app.py`
- `apps/ui/client.py`
- `apps/ui/chat_page.py`
- `apps/ui/dashboard_page.py`
- `src/enterprise_it_support/analytics/models.py`
- `src/enterprise_it_support/analytics/persistence.py`
- `src/enterprise_it_support/analytics/service.py`
- `src/enterprise_it_support/analytics/routes.py`
- `src/enterprise_it_support/service_desk/persistence.py`
- `src/enterprise_it_support/service_desk/service.py`
- `migrations/versions/20260801_0013_add_feedback_analytics.py`
- `scripts/seed_phase11_demo.py`
- `tests/integration/api/test_analytics.py`
- `tests/integration/analytics/test_seed.py`
- `tests/unit/ui/test_api_client.py`

## 安全审查

- UI 不含数据库 URL、ORM、SQL、Repository 或文件读取；
- Analytics 权限由后端确定性 permission map 执行；
- Feedback 绑定 persisted actor/role 和来源 Run/Ticket；
- cancel ownership 和状态由后端锁行检查，成功 audit 原子提交；
- 工单仍必须经过 R1 confirmation；UI 没有绕过 Gateway；
- R3 行为仍是 simulated only，UI 不自动审批；
- seed 全部虚构、幂等、无删除、无外部调用；
- 没有新增 Shell、subprocess、eval/exec、任意 SQL Agent tool 或真实企业 Adapter；
- 页面只展示脱敏摘要、结构化 error code 和既有 audit，不展示模型私有 reasoning。

## 独立收尾代码审查

- **Blocking：** 两轴审查没有发现 Blocking，也没有发现过度设计、Phase 12 提前实现、真实企业 Adapter、任意命令工具或安全边界绕过。
- **已修复 Important：** UI 原先把所有 retrieved candidates 当 Citation 展示，现只显示 `final_response.citations`；确认后重新读取 Run，使 `create_ticket` Tool Execution 可见；身份切换、新请求和取消会清理陈旧 pending/Ticket 状态并给出明确结果。
- **已修复 Important：** Run cohort 的平均 Steps/Tools 现在只按 Run `started_at` 选样本，再连接该 Run 的全部 child events，避免跨窗口 child timestamp 被错误丢弃；全局 Tool 成功率仍按 Tool event time，两个时间轴含义不同且已测试。
- **已修复 Important：** Feedback 同时对全局 idempotency key 和 Run 获取有序 advisory locks，避免不同 Run 并发复用同一 key 时唯一约束泄漏为 503。
- **已修复 Important：** 新增取消 allow/deny audit、空 Dashboard、损坏 Evaluation、Ticket 404/403、全局 idempotency 冲突、时间边界和 UI 状态单元测试；seed 现在提供可检索知识。
- **未处理 Optional：** 没有增加生产 SSO、tenant analytics、缓存/预聚合、浏览器 E2E 框架、流式 UI、Feedback 编辑/删除或复杂设计系统；它们不属于 Phase 11。

## 已知限制

- 本地模拟 actor/role 不是可信身份；生产前必须由 SSO/Principal 注入；
- Streamlit 同步请求没有 token streaming、后台 job、生产 session 或横向扩展验证；
- Dashboard 无 tenant isolation、缓存、预聚合或大数据量性能测试；
- 最近 Evaluation 来自本地 artifact，不是数据库或远程 artifact store；
- Feedback 不可编辑，comment 尚无生产级数据保留/删除/PII 工作流；
- 自助解决率依赖用户提交 Feedback，存在 response bias；
- 转人工率把已创建本地 Ticket 视为人工路径代理，不代表真实坐席已经处理；
- 平均响应时间是本地端到端 Run 时间，不是生产 SLA；
- 页面截图是一次本地 seed/实时演示快照，数值会随新增演示运行变化；
- Phase 10 的 Fake Provider、虚构数据集和 groundedness 局限仍存在。

## 五个必须理解的核心概念

1. **UI/API 分层：** “UI 不写 SQL”还不够；它也不能复制 Policy、状态机和指标定义，否则不同客户端会得到不同业务结果。
2. **事件分母决定指标含义：** 自助解决率用 Feedback 作分母，转人工率用 Agent Run 作分母；两者不能放在同一个未说明的分母上。
3. **零和无样本不同：** 0% 表示有样本但没有成功，`null/sample_count=0` 表示根本没有可评价数据。
4. **幂等不只是唯一键：** replay 必须验证 actor、role、Run、Ticket 和 payload 完全相同；否则唯一键会掩盖跨用户冲突。
5. **Dashboard 是投影，不是事实源：** PostgreSQL 业务轨迹和 Evaluation artifact 是事实源，Analytics API 是有界只读投影，Streamlit 只是最后一层呈现。

## 十道面试问题

1. 为什么 Streamlit 不能直接连接 PostgreSQL，即使这是个人项目？
2. 为什么 Feedback 同时需要 `agent_run_id` 唯一约束和 `idempotency_key`？
3. 如何防止用户给别人的 Agent Run 或 Ticket 提交反馈？
4. 为什么成功取消状态和 allow audit 应在同一个事务？
5. 自助解决率为什么以 Feedback 为分母，它会产生什么 selection bias？
6. “escalated 或有 Ticket”作为转人工代理有哪些误差？
7. 平均工具调用为什么要把零工具 Run 保留在分母？
8. 为什么无样本指标应返回 `null + sample_count`，而不是 0？
9. pandas 在后端和 UI 中分别可以承担什么，哪些属于业务逻辑复制？
10. 如果数据量从几百增长到一亿条，如何演进当前 SQL、索引、缓存和预聚合，同时保持 API contract？

## 独立练习

用 30–60 分钟增加一个只读的“按日趋势”后端 contract，不修改现有页面业务：

- 定义最近 7/30 天每天的 runs、tickets、feedback 数；
- 缺失日期必须补 0，但整个时间窗无业务样本的率指标仍为 N/A；
- SQL 必须在后端，UI 只画后端返回的 date/value；
- employee 读取返回 403；
- 写真实 PostgreSQL 测试覆盖跨日、边界时区、缺失日期、空窗口和权限；
- 解释为什么趋势的日期边界必须明确时区，以及为什么不能由浏览器本地时间隐式决定。

## 三个最容易“做出来但讲不清楚”的位置

1. **两个时间轴：** Run、Tool、Ticket、Feedback 有不同时间列；必须说明各指标按哪个事件进入窗口。
2. **自助与转人工不是互补率：** 它们分母不同，Feedback 可能缺失，因此不能期待二者相加等于 100%。
3. **seed 的特权边界：** seed 可以直接写本地数据库是因为它是受控 fixture；UI/Agent 仍只能走 FastAPI/Gateway，不能把 fixture 路径变成生产旁路。

## 建议版本

- Commit：`fix(ui): close phase 11 acceptance gaps`
- Tag：学习验收后建议 `phase-11-complete`

Phase 11 工程结论为 **PASS**，没有剩余 Blocking 或必要 Important；总体为 **CONDITIONAL PASS**。本次到此停止，不自动开始 Phase 12。
