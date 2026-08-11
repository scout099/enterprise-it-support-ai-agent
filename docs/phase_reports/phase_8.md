# Phase 8 Report：本地工单、低风险写操作、用户确认与审计

## 结论

**CONDITIONAL PASS：工程通过，学习验收待完成。** 本阶段在本地 PostgreSQL 中实现 Service Desk，不连接 ServiceNow/Jira。Agent 对直接工单请求或 `escalated/failed` 诊断生成 R1 pending confirmation；用户确认后，Tool Gateway 再次校验 actor、role、action、参数、风险、状态和 idempotency key，才执行工单创建或评论。R0 状态查询自动执行；密码重置和权限修改属于 R3，只登记审批申请，没有执行 Adapter。

收尾独立审查发现的 Blocking 和必要 Important 均已修复，没有剩余工程 Blocking。进入 Phase 9 前，项目所有者仍需独立回答本报告的 10 道面试题，并完成 30–60 分钟练习。

## 验收矩阵

| 原始要求/验收项 | 状态 | 文件证据 | 测试或运行证据 |
| --- | --- | --- | --- |
| 五个实体 | 完成 | `models.py`、migration 0009、既有 `tools/models.py` | migration schema test；`0009 → 0008 → 0009` |
| Ticket 全部指定字段 | 完成 | `Ticket` ORM、`CreateTicketInput`、`TicketResponse` | migration column assertions；API Ticket GET |
| 三个工具 | 完成 | `service_desk/tools.py` Registry definitions | Service/API integration；直接 Gateway 拒绝测试 |
| R0 status 自动执行 | 完成 | `get_ticket_status()`、R0 definition | owner 200、other employee 403、audit failure 稳定错误 |
| R1 create/comment 必须确认 | 完成 | `_propose_r1()`、`confirm()`、confirmation validator | 确认前 Ticket/Comment=0；Gateway 无 confirmation 不写入 |
| R3 password/permission 只审批 | 完成 | `_high_risk_action()`、`create_approval_request()`；无 R3 Adapter | 两类 API proposal 为 approval-required，confirm 409 |
| proposal → pending → confirm → revalidate → result | 完成 | Service、Pending Repository、Gateway | wrong actor、state/参数/ID 重校验、正式 composition smoke |
| 写操作 idempotency key | 完成 | advisory lock、fingerprint、unique constraints | same-key replay/conflict、duplicate respond/confirm、same ticket |
| 审计字段完整 | 完成 | `AuditEvent`、`ToolExecution` | actor/action/target/summary/policy/result/request ID/created_at 断言 |
| 审计不保存密码/Token/完整正文 | 完成 | Gateway input/output projection、Repository summaries | title/description/diagnosis/Bearer/exception secret 回归 |
| 所有写入有审计 | 完成 | pending+proposal audit 同事务；Ticket/Comment+成功双审计同事务 | proposal audit failure 回滚 pending；Gateway store failure 仍保留原子成功审计 |
| 权限不足 | 完成（本地 Policy） | RolePermissionPolicy、resource ownership、统一 audit permission map | guest proposal deny、wrong actor confirm、foreign Ticket deny、Audit GET deny |
| 工具失败 | 完成 | Gateway stable failure、pending failed | failing Adapter：Ticket=0、safe tool/domain audit |
| Agent 无法解决后建议工单 | 完成 | `_plan_action()` 检查 escalated/failed | `agent_max_tool_calls=1`：escalated → create-ticket pending |
| 工单携带完整诊断上下文 | 完成（关联式） | bounded `diagnosis_summary` + `source_agent_run_id`/Conversation ID | API/正式 smoke 验证非空 summary 与 Run 关联；完整 node/tool trace 留在 Agent Run |
| 四个指定 API | 完成 | `service_desk/routes.py` | API integration tests + installed composition smoke |

设计差异说明：完整诊断轨迹没有复制进 Ticket 单行，而是保存有界摘要并通过 `source_agent_run_id` 关联原始 Run/Step/Tool trace；这是数据最小化选择，不是缺失。权限验收只证明本地确定性 Policy，`actor_id`/`user_role` 仍是自报身份，不代表生产认证。

## 数据模型

### tickets

- UUID `id` 与人可读 `IT-YYYYMMDD-NNNNNN` ticket number；
- title、description、category、priority、status；
- requester、assignee；
- source Conversation、source Agent Run；
- diagnosis summary；
- unique create idempotency key；
- created/updated timestamps。

### ticket_comments

- Ticket FK、author、body、unique idempotency key、created timestamp。

### pending_confirmations

- actor/role、action、R1/R3、lifecycle status；
- 执行所需参数、脱敏参数摘要、影响说明；
- idempotency key、material request fingerprint；
- source Run/Conversation、result、安全 error 和时间。

### audit_events

- actor、action、target；
- bounded parameters summary；
- allow/deny/confirmation-required/approval-required；
- execution result、request ID、created timestamp。

### tool_executions

Phase 7 表继续使用，并增加 actor、pending confirmation 和 idempotency 关联。`run_id` 对独立 R0 Ticket GET 可为空；成功 Ticket/Comment 的工具审计与业务行同事务保存。

## 风险与确认路径

```text
POST /agent/respond
→ existing bounded Agent Runtime
→ deterministic action planner
→ Gateway schema + role validation
→ save R1 pending confirmation / R3 approval
→ return action + parameters + impact

POST /agent/confirm
→ lock pending row + actor ownership
→ Gateway revalidates action/parameters/risk/idempotency
→ local PostgreSQL Adapter
→ Ticket/Comment + audit_event + tool_execution in one transaction
→ pending executed/failed
→ return persisted result
```

R0 `get_ticket_status` 不生成 confirmation，但仍经过 Registry、Schema、Role Policy、resource ownership、Gateway 和 audit。

## API

- `POST /agent/respond`
  - input：message、actor ID、local role、idempotency key、optional Conversation/Ticket；
  - output：完整 Agent Run + optional pending confirmation。
- `POST /agent/confirm`
  - 仅 pending 原 actor/role 可确认；
  - duplicate confirm 返回同一 persisted result。
- `GET /tickets/{ticket_number}`
  - employee 只能读取自己的 Ticket；IT support 可读取授权资源。
- `GET /audit/events`
  - limit/offset 有界；
  - 仅 `it_support`/`project_maintainer`。

旧 `/agent/runs`、知识、RAG 和诊断 API 保持兼容。

## 关键实现

- `src/enterprise_it_support/service_desk/domain.py`
- `src/enterprise_it_support/service_desk/models.py`
- `src/enterprise_it_support/service_desk/persistence.py`
- `src/enterprise_it_support/service_desk/tools.py`
- `src/enterprise_it_support/service_desk/service.py`
- `src/enterprise_it_support/service_desk/schemas.py`
- `src/enterprise_it_support/service_desk/routes.py`
- `src/enterprise_it_support/tools/gateway.py`
- `migrations/versions/20260724_0009_add_local_service_desk.py`

## 验证结果

- 修改前 Phase 7 基线：`186 passed in 9.35s`；
- Phase 8 功能/失败聚焦：`19 passed in 1.43s`；
- 原子审计专项：`6 passed in 0.50s`；
- 首轮全量：`194 passed in 9.10s`；
- 原子审计和重复 respond 修复后最终全量：`195 passed in 9.20s`；
- 收尾红灯：`3 failed, 9 passed in 1.98s`；
- Blocking/Important 修复后聚焦：`12 passed in 1.81s`；
- Phase 8/Tool Gateway 全部相关测试：`24 passed in 1.78s`；
- 收尾修复后最终全量：`198 passed in 10.05s`；
- test DB migration：`0009 → 0008 → 0009`；
- development/test DB：`20260724_0009 (head)`；
- Ruff：`All checks passed!`，`120 files already formatted`；
- compileall、pip check、Git whitespace：通过；
- 普通 wheel build/install：通过。
- 安装态 composition-root smoke：诊断 escalated → proposal 200/pending → confirm 200 → Ticket GET 200；错误 actor confirm 403；`modify_permissions` R3 confirm 409；重复 confirm 返回同一 Ticket；Audit GET 200。

使用的最终命令：

```bash
.venv/bin/pytest tests/unit/tools tests/integration/tools \
  tests/integration/service_desk tests/integration/api/test_service_desk.py \
  tests/integration/knowledge/test_migrations.py -q
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m compileall -q src apps tests
.venv/bin/python -m pip check
git diff --check
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260723_0008
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head
.venv/bin/python -m pip install --no-build-isolation .
```

## 安全审查

- 未发现 ServiceNow/Jira、subprocess、Shell、Python/SQL/system command、eval/exec 或真实账号修改；
- R3 action 没有 Registry Adapter，不能通过 confirm 执行；
- resource ownership 在 Adapter 内再次检查，不能只靠 role grant；
- confirmation owner 不能由 IT support 隐式代替；
- input/output audit projection 都不复制自由文本；Credential-shaped values 额外脱敏；
- Ticket/Comment 成功写入与两类成功 audit 同事务，关闭“业务已提交、审计尚未写入”的窗口；
- Provider/Adapter exception 正文不保存到 API、pending、tool audit 或 domain audit。

## 收尾代码审查

### 已修复

1. **Blocking：proposal audit 非原子。** 旧流程先提交 pending，再写 audit；现在 Repository 在一个事务里创建/复用 pending 并追加 proposal audit，audit 写失败时 pending 一并回滚。
2. **Important：跨 actor R3 replay。** 现在 replay 同时比较 actor、role、risk 和 material fingerprint，不再返回其他 actor 的 pending。
3. **Important：R0 audit failure 的错误合同。** 现在转换为稳定 `tool_audit_unavailable`，HTTP 返回安全 503，而不是未处理 500。
4. **Important：权限规则重复。** Audit API 复用 `service_desk_permissions()` 的 `audit:read`，不再维护独立角色集合。
5. **Important：错误字符串模糊匹配。** Ticket GET 使用 `ServiceDeskExecutionError.code` 精确映射 403/404/503。
6. **Important：缺失安全回归。** 已增加 Gateway 无 confirmation、proposal audit rollback、跨 actor R3、permission R3、audit `created_at` 和 R0 audit failure 测试。

### 未发现

- 没有 ServiceNow/Jira、真实企业写 Adapter、Shell/Python/SQL/system command；
- 没有 Phase 9 评估、Web UI 或生产部署提前实现；
- 双审计并非重复设计：ToolExecution 记录一次工具调用，AuditEvent 记录业务/政策事实；
- 没有剩余工程 Blocking 或必要 Important。

### 未处理 Optional

- confirmation executing 状态的 lease/recovery；
- Ticket comments 分页；
- 更细的模块拆分和通用审批引擎；
- 可信认证/tenant 接入。这是生产前必要能力，但不属于 Phase 8 原始范围。

## 限制

- actor/role 自报，不是生产认证或 tenant isolation；
- R3 approval 没有审批人、审批流、通知或执行器；
- pending confirmation 必须保存业务参数；生产前仍需保留、加密、删除策略；
- 脱敏无法识别任意编码/混淆秘密；
- 单 PostgreSQL 整体故障无法写回自身；
- action planner 是本地确定性演示规则；
- 不包含 Phase 9 评估、Web UI 或生产部署。

## 学习验收

### 完整数据流

```text
employee request
→ POST /agent/respond + idempotency_key
→ bounded Agent Runtime persists Run/Steps/tool observations
→ deterministic planner selects no action / R1 / R3
→ Registry lookup + strict input schema + Role Policy
→ one transaction: pending_confirmation + sanitized proposal audit
→ response returns action, parameters summary, impact and confirmation ID
→ POST /agent/confirm by original actor/role
→ row lock changes pending → executing
→ Gateway repeats Registry/schema/permission/confirmation checks
→ R1 PostgreSQL Adapter executes
→ one transaction: Ticket/Comment + domain audit + tool execution audit
→ pending → executed with persisted result
→ duplicate confirm returns original result without a second business row

R0:
GET Ticket → Gateway/Policy/resource ownership → read → tool audit + domain audit

R3:
request → approval_required row + audit → no registered Adapter → confirm returns 409
```

### 五个必须理解的核心概念

1. **Proposal 与 execution 分离：** Agent 可以建议动作，但只有持久化 confirmation 和执行时重校验才能授权写入。
2. **分层幂等：** request fingerprint 检查“同 key 是否同动作”，advisory lock 串行化竞争，unique constraint 是数据库最终防线，duplicate confirm replay 返回原结果。
3. **Policy 与 resource authorization 不同：** role permission 只说明能否调用某类工具；Ticket ownership 还要在 Adapter 访问具体资源时检查。
4. **原子业务写入与审计：** 成功 Ticket/Comment 不能先提交、再“尽力”写审计；它们必须与成功 audit 在同一事务。
5. **业务结果与 audit projection 分离：** 授权用户可得到完整业务响应，持久化审计只保留必要摘要、稳定错误和脱敏字段。

### 十道面试问题（不附答案）

1. 为什么 `create_ticket` 不能由 Agent Runtime 直接调用 Repository？
2. R0、R1、R3 在本项目中分别代表什么，为什么没有 R2？
3. pending confirmation 中为什么同时需要 parameters、parameters summary 和 request fingerprint？
4. 如果只有唯一约束，没有 advisory lock，并发创建会发生什么？
5. duplicate `/agent/confirm` 为什么不会创建第二张 Ticket？
6. RolePermissionPolicy 已经允许 employee 创建工单，为什么 Adapter 还要检查 requester/owner？
7. 为什么 ToolExecution 和 AuditEvent 不能合并成一张表？
8. 如果 Ticket 已经提交，但成功审计写入失败，系统应该返回成功还是失败？本项目如何避免这个两难？
9. 为什么 audit 中不能直接保存完整 tool input/output？怎样同时保证可追溯性？
10. 当前 `actor_id`/`user_role` 自报会造成哪些攻击面？接入可信身份后，哪些接口和数据查询必须改变？

### 30–60 分钟独立编程练习（不附完整答案）

实现一个最小的 `close_ticket` 练习分支，但不要接入正式 Registry 或 API：

- 定义输入：ticket number、resolution summary、idempotency key；
- 写出 R1 proposal 和 confirmation 状态转换的伪代码或独立测试 double；
- 设计至少四个测试：未确认不关闭、wrong actor 拒绝、重复确认只关闭一次、audit 写失败时 Ticket 状态不变化；
- 明确哪一层做 role permission，哪一层做 Ticket ownership；
- 画出需要同事务提交的数据库行；
- 最后用 5 分钟口头解释：为什么 retry 不等于 idempotency。

完成标准：不要求把练习代码合入当前 Phase；应能独立写出测试和接口草图，并解释每个防线解决的具体失败模式。

### 最容易“做出来但讲不清楚”的三个位置

1. **四层幂等各自职责：** fingerprint、advisory lock、unique constraint、confirmation replay 不是四种同义实现。
2. **两类 audit 与原子边界：** proposal audit、domain audit、tool audit 的事实含义和事务位置不同。
3. **执行时重新授权：** proposal 时校验不能替代 confirm 时的 actor/role/action/parameters/status 全量重校验。

## 建议提交

- Commit：`fix(service-desk): close phase 8 confirmation audit gaps`
- Tag：`phase-8-complete`

当前为 **CONDITIONAL PASS**。项目所有者完成上述 10 道问题和独立练习，并明确确认后，才可进入 Phase 9。
