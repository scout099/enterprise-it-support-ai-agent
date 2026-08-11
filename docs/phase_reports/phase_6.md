# Phase 6 Report：LangGraph Agent Runtime 与意图路由

## 结论

**工程 PASS，总体 CONDITIONAL PASS（本地演示 MVP）。** Phase 5 的可信 RAG 已接入显式 LangGraph 请求流；六类结构化意图、低置信度澄清、三类诊断占位、工单未开放、安全升级、执行上限、PostgreSQL checkpoint 与 Agent Run/Step 轨迹均形成代码和测试闭环。进入下一阶段前，项目所有者仍需完成本报告对应的学习验收。

本阶段没有实现真实诊断、工具、命令、工单写入或其他企业系统操作。

## 验收矩阵

| 要求 | 实现证据 | 验证 |
| --- | --- | --- |
| 完整 AgentState | `agent_runtime/state.py` 的显式 checkpoint-safe TypedDict | initial state 与 checkpoint tests |
| 七个指定节点 | graph builder 注册 intake/classify/clarify/retrieve/compose/escalate/finalize | 路由与 HTTP step trace |
| 六类意图 | strict `IntentClassification` + `AgentIntent` | 六类参数化路由 |
| 短 reasoning summary | 模型字段 required/单行/最长 300；原文不保存/不展示，代码生成固定决策说明 | Schema、multiline rejection、原文不跨边界 test |
| 低置信度澄清 | 确定性 confidence threshold | 不检索的 clarification test |
| 知识问答 RAG | retrieve node + `RAGAnswerService.answer_from_results()` | 真实 PostgreSQL Citation API test |
| 三类诊断占位 | 三个独立 placeholder node | VPN/Outlook/account route tests |
| 工单未开放 | `ticket_unavailable` | 无写操作 HTTP test |
| unsupported 安全升级 | `escalate_to_human`；high risk 强制升级 | escalation tests |
| 节点/重试/超时上限 | 节点尝试硬预算、recursion limit、node/total timeout、retry allowlist | exception、node/total timeout、retry budget、compose no-retry tests |
| checkpoint 恢复 | official `AsyncPostgresSaver` + run ID thread | 跨 saver 实例 restore test |
| Agent Run/Step | migration 0007 + Repository | PostgreSQL persistence/schema tests |
| 完整节点可见 | POST/GET Agent Run 返回有序 Steps | HTTP readback test |
| RAG 不回归 | 原 Chat API/CLI/RAG tests 保留；compose 复用原服务且不做 graph retry | 全量 164 tests |

## 最终请求流

```text
POST /agent/runs
→ intake
→ strict classify_intent
→ deterministic confidence / risk / intent routing
   → request_clarification
   → retrieve_knowledge → compose_answer through trusted RAG
   → vpn / outlook / account diagnosis placeholder
   → ticket_unavailable
   → escalate_to_human
→ finalize
→ agent_runs latest state + ordered agent_steps
→ LangGraph PostgreSQL checkpoint
```

每个节点尝试都受单节点 timeout 和统一节点预算保护；只有无写副作用的分类与检索允许有限 graph retry。整个 graph 同时受总 timeout 与 recursion limit 保护。错误只保存稳定 code 和安全文案，日志只增加异常类型而不保存异常正文。

## 关键实现

- `src/enterprise_it_support/agent_runtime/state.py`：state、intent/risk/status 枚举、strict classification；
- `src/enterprise_it_support/agent_runtime/runtime.py`：LangGraph、节点、路由与执行边界；
- `src/enterprise_it_support/agent_runtime/models.py`、`persistence.py`：Run/Step 业务持久化；
- `src/enterprise_it_support/agent_runtime/routes.py`、`schemas.py`：执行与轨迹读取 API；
- `src/enterprise_it_support/agent_runtime/rag.py`：从 graph 已检索证据继续可信生成；
- `migrations/versions/20260723_0007_add_agent_runs.py`；
- `apps/api/main.py`：PostgreSQL checkpointer lifecycle；
- `apps/dependencies.py`：按严格 Schema 分派确定性 Fake classification/RAG。

## 关键决策

1. **LangGraph checkpoint 与业务审计分离。** 官方 saver 管理 checkpoint 内部表；项目 migration 管理稳定的 `agent_runs/agent_steps` 产品数据。
2. **模型分类、代码路由。** 模型只提供 strict Schema；阈值、high-risk、路径和结束条件由确定性代码执行。
3. **复用 RAG，不复制安全规则。** retrieve 与 compose 节点分离，但 compose 仍使用 Phase 5 的 relevance、structured answer、Citation allowlist 和 Conversation trace；由于 compose 会持久化 Turn，graph 不自动重试该节点。
4. **错误不暴露 Provider 正文。** Step/Run 只保存稳定 error code 与安全固定说明。
5. **数据库故障不破坏 liveness。** checkpoint 初始化失败时应用仍能启动 `/health`，Agent 不可用；readiness 继续报告数据库状态。

## 验证结果

- 开发前基线：`133 passed in 4.35s`；
- 收尾最终全量 pytest：`164 passed in 6.60s`；
- Blocking/Important 聚焦回归：`27 passed in 1.07s`；
- Agent graph + 原 RAG 聚焦：`23 passed in 0.68s`；
- PostgreSQL Run/Step + checkpoint + migration：`3 passed in 0.38s`；
- Agent HTTP 分支：`7 passed, 38 deselected in 1.33s`；
- checkpoint 启动降级回归：`6 passed in 0.57s`；
- Ruff lint：`All checks passed!`；
- Ruff format：`98 files already formatted`；
- compileall：成功；
- pip check：`No broken requirements found`；
- `git diff --check`：通过；
- migration：test DB `0007 → 0006 → 0007` 成功；开发库与测试库均为 `20260723_0007 (head)`；
- 普通 wheel 安装成功；
- 真实 composition root smoke：
  - VPN failure wording → `vpn_diagnosis` → completed；
  - ambiguous request → clarification；
  - high-risk unsupported → safe escalation；
  - 三条路径的 `tool_results` 均为空。

## 验证中发现并关闭的问题

### 0. 收尾审查 Blocking 与 Important

收尾双轴审查发现两个 Blocking：通用 retry 会重复执行有 Conversation 写副作用的 compose；内部 retry 不消耗 LangGraph recursion limit，`max_nodes` 不是节点尝试硬上限。修复后 retry 使用显式 allowlist，compose 单次执行，所有 attempt 消耗统一预算。必要 Important 同步关闭：最终失败 Step 保存完整 failed snapshot；节点 timeout 有独立 code；node/total timeout 均有行为测试；checkpoint psycopg 故障返回安全 503；模型 reasoning summary 原文不持久化/不返回；恢复为 running 清空旧 completed_at；异常日志不记录正文。聚焦验证与最终全量结果见上节。

### 1. Checkpoint 不应成为 liveness 前置条件

首次全量回归有 6 个 health/error 测试失败。原因是这些测试刻意使用不可连接的数据库 URL，新 lifespan 却在应用启动时强制建立 checkpoint 连接。修复后 checkpoint 初始化按依赖能力降级：应用可启动，Agent 不可用，数据库状态仍由 `/ready` 表达。专项 `6 passed`，随后全量转绿。

### 2. 普通 wheel 需要重新安装

首次真实 smoke 因当前虚拟环境仍是旧普通安装而无法导入新增模块；pytest 的 `pythonpath` 掩盖了这一 packaging 状态。按 README 使用 `pip install . --no-build-isolation` 重新安装当前 wheel 后，同一 smoke 三条路径全部成功。

### 3. Tool results 与分类元数据分离

分类调用元数据最初暂存在 `tool_results`，容易让“没有调用工具”的轨迹产生误解。最终 state 使用独立 `classification_metadata`，`tool_results` 保持空列表。

## 安全边界与延后项

- 当前 `user_role` 自报，无可信 Principal、subject 或 tenant；
- diagnosis、ticket 和 escalation 只返回说明，不连接任何工具或写系统；
- 默认 Fake 分类是演示规则，不是分类质量评估；
- checkpoint 和 Step snapshots 包含用户请求与授权证据；生产前需定义租户、保留、加密和删除策略；
- PostgreSQL saver 当前是单连接本地 lifecycle，不代表高并发部署；
- 真实 Provider 未调用；员工查询/Context 的外部数据政策仍需另行授权；
- Citation 仍只保证来源绑定，不证明逐句蕴含。
- checkpoint 已验证跨 saver 实例恢复完整 state；本 Phase 没有承诺或演示“任意中断点自动续跑”，不得把状态恢复夸大为完整工作流续跑认证。

## 学习与面试检查点

以下问题不附答案：

1. `AgentState` 为什么需要完整初始值，而节点只返回局部 update？
2. 为什么模型负责分类，但 confidence、risk 和下一节点由确定性代码决定？
3. 低置信度与 high-risk 同时出现时，当前路由优先级是什么？这样设计的取舍是什么？
4. LangGraph checkpoint 与 `agent_runs/agent_steps` 分别解决什么问题，为什么不应只保留其中一个？
5. 节点尝试硬预算、`recursion_limit`、单节点 timeout、总 timeout 和 retry 各阻止哪类失控？
6. 为什么 `compose_answer` 不能使用 graph 通用重试？它与幂等性有什么关系？
7. 节点异常如何同时满足“用户不看到内部错误”和“运维仍可诊断”？
8. 知识分支如何保证 Agent 化后仍沿用 Phase 5 的相关性闸门和 Citation 来源绑定？
9. “恢复 checkpoint state”和“从任意中断点自动续跑”有什么区别？本阶段实际证明了哪一个？
10. 把当前本地演示用于企业生产前，身份、租户、数据保留和 Provider 数据边界还缺什么？

独立练习（30–60 分钟，不提供完整答案）：实现一个不依赖 LangGraph/数据库的纯函数路由器，输入结构化 classification 与阈值，输出下一节点和一条代码生成的安全决策说明。为六类 intent、低置信度、high-risk、边界 confidence 和非法 intent 编写参数化测试；要求模型原始 reasoning 文本不能出现在输出中。完成后用 5 分钟解释路由优先级和为什么该函数应保持无副作用。

## 建议 Git 信息

- 建议 Commit：`feat(agent): complete bounded langgraph intent runtime`
- 建议 Tag：完成学习验收后使用 `phase-6-complete`

Phase 6 工程验收通过，总体为 CONDITIONAL PASS。完成学习验收且经项目所有者确认前，不开始 Phase 7 Tool Registry、Policy 或工具执行。
