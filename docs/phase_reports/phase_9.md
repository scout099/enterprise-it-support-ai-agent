# Phase 9 Report：RBAC、风险策略与 Human-in-the-loop 模拟审批

## 结论

**CONDITIONAL PASS（工程 PASS；学习验收待完成）。** 本阶段在 Phase 8 的 R3 approval-only 占位之上实现了本地 RBAC、R0–R4 确定性 Policy Engine、Approval Request/Decision、approver API、LangGraph interrupt 与同 Agent Run 恢复。指定场景“申请加入财务系统管理员组”在缺少业务理由时要求补充上下文；理由完整时创建审批并暂停；批准或拒绝后恢复原 run。批准只返回本地 `simulated_success`，不连接或修改任何真实权限系统。

2026-08-01 收尾独立审查共发现并修复两个 Blocking：Decision 已提交而 Runtime 恢复失败时原实现无法重试；admin seed 也持有审批权限，与“非 approver 不能审批”不一致。当前用 PostgreSQL advisory lock 串行化同一 Approval 的 decide/resume，用 `resumed_at` 标记恢复完成；未完成恢复的相同不可变决定可以重试，正常完成后的重复审批仍返回 409。seed 中只有 approver 角色持有 `approval:read/decide`。权限拒绝、恢复失败和恢复成功均有脱敏 audit。

模型不参与最终授权。高风险识别、user/role/permission 解析、风险判断、审批权限、状态转换和恢复分支全部由代码与 PostgreSQL 约束决定。

## 验收矩阵

| 原始要求 | 状态 | 实现证据 | 测试证据 |
| --- | --- | --- | --- |
| users/roles/permissions/user_roles | 完成 | governance models、migration 0010 | migration columns + seed assertions |
| employee/helpdesk/engineer/admin/approver | 完成 | migration 固定本地角色与 demo identity | roles 集合精确断言 |
| Policy 七类输入 | 完成 | `PolicyInput` | Policy unit |
| Policy 仅五种输出 | 完成 | `PolicyDecision` StrEnum | R0–R4 parametrized unit |
| R0–R4 | 完成 | `RiskLevel` + pure `PolicyEngine` | R4 绝对拒绝；R0–R3 matrix |
| 识别财务管理员组请求 | 完成 | `_is_finance_admin_request()` | HTTP integration |
| 收集业务理由 | 完成 | `business_justification` + `need_more_context` | missing reason 无 approval |
| 创建 approval_request | 完成 | Repository + `approval_requests` | pending queue/readback |
| 暂停 Agent | 完成 | `waiting_approval` + LangGraph `interrupt()` | run status/steps |
| approver 批准或拒绝 | 完成 | 三个 approvals API + DB RBAC | approve/reject 200 |
| 保存 decision | 完成 | `approval_decisions` unique per request | response + duplicate 409 |
| 恢复 Agent | 完成 | `Command(resume=...)` + same thread ID + `resumed_at` | same run completed，marker 已写 |
| Decision 后恢复故障可恢复 | 完成 | advisory lock + immutable decision match | injected Runtime failure 503，same decision retry 200 |
| 只模拟成功 | 完成 | `complete_simulated_execution()` | false external-system flag |
| 非 approver 不能审批 | 完成 | DB permission lookup + migration 0012 | employee/admin 403，approver 200 |
| 拒绝正确结束 | 完成 | reject branch | no simulated result |
| 重复审批无效 | 完成 | row lock + status + unique decision | 409 stable code |
| 已完成节点不重复 | 完成 | create 与 await 分离 | exact six-node sequence/count |
| 完整审批和审计轨迹 | 完成 | Approval、Decision、AgentStep、AuditEvent | pending/deny/decision/resume failure/resume success/simulation audit |

## 数据模型

### RBAC

- `users`：本地 external ID、显示名、active 状态；
- `roles`：employee、helpdesk、engineer、admin、approver；
- `permissions`：请求财务管理员组、读取审批、决定审批；
- `user_roles`：用户与角色多对多；
- `role_permissions`：角色与权限多对多。

### Approval

- `approval_requests`：
  - requester；
  - action/tool/target；
  - R0–R4 risk；
  - business justification 与最小 request context；
  - Policy decision 和 lifecycle；
  - idempotency key；
  - source Agent Run 与 checkpoint node；
  - optional simulated result；
  - `resumed_at`：已保存决定成功恢复原 Run 的完成标记；
- `approval_decisions`：
  - 一个 request 最多一条；
  - approver；
  - approve/reject；
  - optional rationale；
  - decision time。

Pending Confirmation 与 Approval Request 已明确分离：前者是原 actor 对 R1 提案的确认；后者是独立授权人对 R3 请求的批准或拒绝。

## Policy Engine

输入：

- user；
- role；
- action；
- tool；
- target_resource；
- risk_level；
- request_context。

唯一输出：

- `allow`；
- `deny`；
- `require_confirmation`；
- `require_approval`；
- `need_more_context`。

确定性规则：

- inactive user、role 未分配、permission 缺失或未知 action/tool/target → deny；
- R4 → deny，任何角色都不能覆盖；
- R2/R3 缺少必要业务上下文 → need more context；
- R0 → allow；
- R1/R2 → require confirmation；
- R3 → require approval。

## 请求与恢复流程

```text
POST /agent/respond
→ deterministic high-risk recognition
→ local User + Role + Permission lookup
→ Policy Engine
→ missing justification: needs_clarification / no approval
→ require_approval:
   create approval_request + audit
   save Agent Step
   LangGraph interrupt at await_human_approval
   Agent Run = waiting_approval

GET /approvals/pending
→ actor ID
→ database RBAC approval:read
→ bounded pending list

POST /approvals/{id}/approve|reject
→ database RBAC approval:decide
→ PostgreSQL advisory lock serializes this Approval attempt
→ row lock request
→ reject requester self-approval
→ insert unique approval_decision
→ Command(resume=decision) on same thread/run
→ reject: safe completed result
→ approve: simulated_success only
→ validate same Run/Approval/decision and terminal state
→ save resumed_at + resume audit
→ append Agent Steps and Audit Events

decision 已写但 resume 失败
→ return stable 503 + failed resume audit
→ same approver + same decision + same rationale may retry
→ changed approver/rationale or already resumed → 409
```

## Checkpoint 不重复证据

首次执行并暂停后只有：

1. `intake`
2. `evaluate_governance_policy`
3. `create_approval_request`

恢复批准后追加：

4. `await_human_approval`
5. `simulate_approved_action`
6. `finalize`

拒绝时第五步为 `finish_rejected_action`。集成测试断言前三个节点各出现一次，因此审批恢复不会重新识别请求、重复 Policy 计算或创建第二条 Approval Request。

LangGraph 的 `__interrupt__` 是框架控制数据，不写入业务 Agent Run JSONB；代码显式投影 AgentState allowlist 字段，checkpoint 控制信息由 AsyncPostgresSaver 独立保存。

## API

- `GET /approvals/pending`
  - query：actor ID、bounded limit/offset；
  - 仅数据库权限 `approval:read`；
- `POST /approvals/{id}/approve`
  - body：actor ID、optional rationale；
  - 保存 approve 决定并恢复原 run；受控恢复失败返回 503；
- `POST /approvals/{id}/reject`
  - body：actor ID、optional rationale；
  - 保存 reject 决定并恢复原 run。

决定 API 不接受 role 字段，避免调用方通过 `user_role=approver` 提升权限。actor ID 仍是本地演示身份选择器，不代表生产认证。

## 关键实现

- `src/enterprise_it_support/governance/domain.py`
- `src/enterprise_it_support/governance/models.py`
- `src/enterprise_it_support/governance/policy.py`
- `src/enterprise_it_support/governance/persistence.py`
- `src/enterprise_it_support/governance/service.py`
- `src/enterprise_it_support/governance/routes.py`
- `src/enterprise_it_support/governance/schemas.py`
- `src/enterprise_it_support/agent_runtime/runtime.py`
- `src/enterprise_it_support/agent_runtime/state.py`
- `migrations/versions/20260724_0010_add_rbac_and_approvals.py`
- `migrations/versions/20260801_0011_add_approval_resume_marker.py`
- `migrations/versions/20260801_0012_restrict_approval_to_approver.py`

## 验证结果

- 收尾修复红灯：workflow `3 failed in 1.54s`；
- 最终 governance workflow + migration schema：`4 passed in 1.34s`；
- Phase 9/受影响回归：`81 passed in 4.12s`；
- 最终全量：`211 passed in 11.39s`；
- test DB corrective migrations：`0011 → 0010 → 0011` 与 `0012 → 0011 → 0012`；
- development/test DB：`20260801_0012 (head)`；
- Ruff：`All checks passed!` / `134 files already formatted`；
- compileall、pip check、Git whitespace：通过；
- 普通 wheel build/install：通过；
- 正式 composition-root 演示：missing context 200/无 approval，proposal waiting，admin 403，approver 200，same run completed，Approval executed/resumed，simulated success，external modified false，六节点无重复，duplicate 409。

实际命令：

```text
.venv/bin/python -m pytest tests/unit/governance tests/integration/governance tests/unit/agent_runtime tests/integration/agent_runtime tests/unit/tools tests/integration/tools tests/integration/service_desk tests/integration/api/test_service_desk.py tests/integration/knowledge/test_migrations.py -q
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260724_0010
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260801_0011
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head
.venv/bin/python -m pip install --no-build-isolation .
.venv/bin/python /private/tmp/phase9_closeout_demo.py
```

最后一条使用只存在于演示期间的临时 launcher，运行后已删除；它调用正式 `create_app()` composition root 和隔离 PostgreSQL test DB。

## 收尾代码审查

- **Blocking（已修复）：** Decision commit 后 resume 失败不可恢复；现在以 advisory lock、immutable decision match、checkpoint 与 `resumed_at` 闭环。
- **Blocking（已修复）：** admin seed 曾持有 approval permissions；corrective migration 0012 使 employee/helpdesk/engineer/admin 均无法审批，只有 approver 可以。
- **Important（已修复）：** 非 approver/self-approval 拒绝无 audit；现在写 `not_executed:access_denied`。
- **Important（已修复）：** resume 完成缺少明确标记和审计；现在保存 `resumed_at` 以及 failed/completed resume event。
- **Important（已修复）：** 缺少恢复失败、批准完整 audit、恢复身份/内容不可篡改回归；已加入 PostgreSQL integration assertions。
- **过度设计：** 未发现 Blocking/Important；advisory lock 与 marker 直接服务于当前 Phase 的恢复验收，不是提前建设分布式工作流。
- **提前实现后续功能：** 未发现 Phase 10 evaluation、UI、SSO、外部 IAM 或真实 Adapter。
- **硬编码/重复：** demo seed UUID、五个固定角色和场景短语是原始范围要求；Agent 粗粒度风险与 Governance R0–R4 使用两个同名 `RiskLevel`，面试时必须说明边界，但本轮不做跨 Phase 重构。
- **错误处理：** 403/404/409/503 均为稳定公共错误；Runtime 异常和 rationale 正文不对外泄漏或写入 audit。
- **剩余安全边界：** actor ID 仍可由调用方选择，不能视为生产认证；这是“本 Phase 不接真实 SSO/Entra ID”的明确限制，不在本轮擅自修复。

## 安全审查

- 没有 SSO、Entra ID、LDAP、Microsoft Graph 或真实目录 Adapter；
- 没有 ServiceNow/Jira；
- 没有 subprocess、Shell、Python/SQL/system command、eval/exec；
- 没有真实密码、Token、API key 或企业账号；
- 财务管理员组 action 没有注册为 Agent 可任意调用的真实 Tool；
- 批准只能写本地模拟结果；
- 模型没有收到或返回最终授权决定；
- Approval API 从数据库解析 permission，不信任 body/query 中的 role；
- self-approval、非 approver、重复审批和 R4 均被确定性拒绝。
- 同一 Approval 的决定/恢复尝试数据库串行化；完成后 duplicate、换 approver 和改 rationale 均无效。
- 拒绝尝试和恢复失败只记录最小 audit，不保存业务理由正文、rationale 正文或异常正文。

## 已知限制

- actor ID 是本地请求字段，不是可信认证主体；
- demo users/roles/permissions 是 migration seed，不是企业身份同步；
- 高风险识别只覆盖本阶段指定演示短语；
- 没有多级审批、委派、会签、通知、超时和到期撤销；
- Decision 与 graph resume 仍跨两个事务，但中间故障可由相同不可变决定和 checkpoint 恢复；没有后台 reconciliation worker；
- 没有生产级审批数据加密、保留或删除策略；
- 批准后不执行真实权限变更。

## 五个必须理解的核心概念

1. **Policy Decision 不等于 Approval Decision：** Policy 代码决定是否需要人；approver 决定具体请求批准或拒绝。
2. **Confirmation 不等于 Approval：** R1 是原 actor 确认自己的低风险写入；R3 是另一个授权主体批准高风险请求。
3. **Checkpoint 不等于业务审计：** AsyncPostgresSaver 负责恢复位置；Agent Step、Approval 和 Audit Event 负责可解释业务证据。
4. **幂等不只靠 unique constraint：** unique decision 防第二个决定，row lock 保护状态转换，advisory lock 串行化跨事务 resume，`resumed_at` 标记完成。
5. **批准不等于真实执行：** 本阶段只证明治理控制流，结果明确标记模拟；actor ID 仍不是生产认证主体。

## 十道面试问题

1. 为什么 Policy Decision 和 Approval Decision 必须分开？
2. 为什么 Approval Request 不能继续复用 Pending Confirmation 表？
3. R0–R4 分别怎样映射到五种 Policy 输出？
4. 为什么 R4 即使 admin 或 approver 也必须拒绝？
5. 为什么创建审批和等待审批要拆成两个 LangGraph 节点？
6. `interrupt()` 返回的控制元数据为什么不能直接保存到业务 JSONB？
7. 如何证明恢复后没有重复执行 intake、Policy 和 create approval？
8. row lock、unique decision、advisory lock 和 `resumed_at` 分别解决什么问题？
9. 为什么审批 API 不接受 `user_role`，但 actor ID 仍不能视为生产身份？
10. 当前可重试方案与 outbox/reconciliation worker 相比还缺少什么生产能力？

## 独立练习

用 30–60 分钟实现一个独立的小型 `ApprovalResumeCoordinator`，使用内存 fake repository/runtime，不修改本仓库生产代码：

- 输入 approval ID、actor、decision、rationale；
- 首次决定后让 fake runtime 注入一次失败；
- 仅允许相同不可变决定恢复一次；
- 不同 actor、不同 rationale、完成后 duplicate 均拒绝；
- 断言已完成的三个前置 step 没有重复；
- 输出至少五个测试，并用 5–8 句话解释 unique、lock、checkpoint 和 completion marker 的不同职责。

不要复制当前 Repository；练习目标是自己重新推导状态机和不变量。

## 三个最容易“做出来但讲不清楚”的位置

1. **四种并发/幂等机制的分工：** unique、row lock、advisory lock、`resumed_at` 不是重复保险，各自覆盖不同时间窗口。
2. **三类持久化证据：** LangGraph checkpoint 用于恢复，Agent Steps 用于节点轨迹，Approval/Audit 用于授权与治理事实；缺一不能互相替代。
3. **身份边界：** 数据库解析 role/permission 防止自报 role 提权，但请求里的 actor ID 未经认证，因此只能叫本地 RBAC 模拟，不能声称生产授权安全。

## 建议版本

- Commit：`fix(governance): make human approval resume recoverable`
- Tag：`phase-9-engineering-pass`

Phase 9 工程结论为 **PASS**，没有剩余 Blocking 或必要 Important；总体为 **CONDITIONAL PASS**。项目所有者独立回答上述 10 题并完成练习后，才建议改用 `phase-9-complete`。本次到此停止，不自动开始 Phase 10。
