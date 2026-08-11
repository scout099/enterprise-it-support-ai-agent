# Enterprise IT Support AI Agent 面试指南

本文以当前仓库代码、测试和 Phase 报告为准。回答时应明确区分：已实现的本地作品集能力、完全虚构的 Mock 数据，以及生产环境仍需补齐的能力。

## 3 分钟项目介绍

我做的是一个 Enterprise IT Support AI Agent，不是把大模型套在聊天框上的普通问答 Demo。它解决三个业务问题：企业知识分散、故障诊断不一致，以及自动化操作缺少权限和审计。

第一层是可信 RAG。系统把 Markdown、TXT 和 PDF 做版本化解析与 Chunking，存入 PostgreSQL；检索同时使用全文搜索和 pgvector，再用 RRF 融合。权限、文档状态和有效期在排名前过滤。模型收到的是有界、明确标记为不可信数据的 Context，只能选择当前证据的 E 标签，最终 Citation 由服务器从真实 Chunk 物化。没有足够证据时系统确定性拒答。

第二层是 LangGraph Agent。它把知识问答、VPN、Outlook、账号诊断、工单和不支持请求建模为显式 State、Node、Edge。诊断调用 7 个只读 Mock 工具，所有调用都经过 Tool Registry、严格 Schema、权限 Policy、timeout/retry 和审计 Gateway。模型不能执行 Shell、Python 或 SQL，也不能自己决定授权。

第三层是治理和评估。低风险写操作要原用户确认，高风险请求要 RBAC approver 审批，R4 永远拒绝；写操作使用幂等键防止重复建单。系统持久化 Agent Run、Step、Tool、Ticket、Approval 和 Audit。30 条离线案例同时评估检索、Citation、意图、工具、工作流和禁止动作，关键退化会让命令和 CI 返回非零。

项目默认使用 Fake Model、Fake Embedding 和虚构数据，可以通过 Docker Compose 启动 FastAPI、Streamlit 和 pgvector。它仍不是生产系统：没有真实 SSO、tenant、企业 Adapter 和生产数据治理。我把这些限制写进 README，而不是把 Mock 能力包装成真实企业集成。

## 为什么不是普通聊天机器人

普通聊天机器人通常以“生成一段合理文本”为终点。这个项目的成功条件是可证明的系统行为：

- 答案证据必须经过权限过滤并可追溯到具体 Chunk；
- 模型输出必须通过结构化 Schema 和 Citation 校验；
- 诊断步骤、风险、权限和状态转换由确定性代码控制；
- 每个工具调用、确认、审批和写入有持久化轨迹；
- 质量由固定数据集和回归门禁衡量，而不是只看一次 Demo 是否流畅。

因此核心不是“Prompt 写得多好”，而是把不可信的模型放进有边界、可观察、可失败关闭的软件系统。

## 为什么先做 RAG 再做 Agent

RAG 和 Agent 的错误来源不同。RAG 要先证明：知识能正确导入、授权过滤、检索、拒答和引用；Agent 再解决多步骤状态、工具和治理。如果一开始同时加入 LangGraph、工具和 RAG，答案错误时很难判断是检索、生成、路由还是工具的问题。

先建立 RAG 基线还有两个好处：Agent 的知识分支可以复用已验证的 Service；Evaluation 可以分别观察 Retrieval、Generation 和 Workflow，而不是只给一个模糊总分。

## LangGraph 的 State、Node、Edge

- **State**：一次 Agent Run 的显式、可 checkpoint 数据，包括用户请求、身份上下文、意图、风险、证据、工具 observation、当前节点、计数、错误和最终响应。它不保存 chain-of-thought。
- **Node**：一个有边界的工作步骤，例如分类、检索、VPN 服务检查、申请审批或 finalize。每个 Node 有超时和可观察结果。
- **Edge**：根据 State 中的确定性字段选择下一个 Node，例如低置信度去澄清、服务中断去升级、R3 去等待审批。

这样做的价值是路径可测试、可恢复、可审计，也能限制循环次数和副作用重试。

## Tool Calling 流程

1. Agent 工作流选择一个已注册的工具名和参数；
2. Registry 解析版本化 Tool Definition；
3. Gateway 用严格 Pydantic Schema 校验输入；
4. Policy 根据服务器持有的 role/permission、risk 和 confirmation 判断；
5. Adapter 在有限 timeout/retry 内执行；
6. 输出再次通过严格 Schema，异常被清洗；
7. 得到结构化 observation，并写 Tool Execution audit；
8. 确定性路由读取 observation 决定下一步。

未知工具、额外参数、权限不足、超时和非法输出都会失败关闭并审计。

## observation 是什么

Observation 是 Tool Adapter 返回、经过 Schema 验证和清洗后的有界事实。例如：

```json
{
  "service": "vpn",
  "status": "operational",
  "region": "global"
}
```

它不是模型的隐藏推理，不是原始系统日志，也不是一段可以继续发号施令的 Prompt。Agent Node 只读取约定字段来路由，避免工具输出通过自然语言注入新的可执行动作。

## LLM 与确定性系统的边界

LLM 适合：语义分类、基于给定证据组织语言、生成短的受约束摘要。

确定性系统必须负责：认证和授权、文档过滤、相关性阈值、Citation 物化、Tool allowlist、Schema、风险决策、确认/审批、幂等、数据库事务、状态转换、审计和 Evaluation gate。

判断原则是：如果一个错误会造成越权、重复写入、审计缺口或对外部系统产生副作用，就不能只相信模型输出。

## 为什么需要幂等

网络超时后，调用方不知道第一次请求是否已经成功。如果直接重试，可能创建两个 Ticket、两条 Comment 或重复提交审批。幂等键让“同一个业务动作”的重试返回原结果。

但唯一键还不够。系统还要验证 actor、role、risk、动作和参数指纹完全一致；否则攻击者可能拿别人的 key 重放不同动作。并发时还要结合数据库锁或唯一约束，不能只在内存里先查再写。

## 为什么需要权限过滤

如果先检索敏感文档、再在 UI 隐藏，内容已经进入模型 Context、日志或 trace，数据泄漏已经发生。因此权限必须在 PostgreSQL 候选检索和排名前执行。

当前项目用简化 role 演示这个规则，但 role 仍来自请求，不是生产可信身份。真正部署时必须由 SSO/Principal 注入 actor、tenant 和权限，Repository 查询也要带 tenant/user scope。

## Agent 如何评估

项目把评估分成四层：

- Retrieval：Recall@3/5、MRR；
- Generation：Citation Validity、Evidence Coverage、Unsupported Claim Rate、Refusal Correctness；
- Agent：Intent、Tool Selection、Tool Argument、Workflow Completion；
- Safety/System：Prohibited Action Rate、Tool Error Rate、steps、latency、token。

30 条版本化虚构案例固定期望意图、文档、工具、最终状态和禁止动作。报告保留逐案例失败和真实分母；Gate PASS 不等于每条案例完美。安全指标退化、关键阈值失败或任一 HTTP case error 都返回非零。可选 LLM Judge 只作辅助，不能覆盖确定性安全门禁。

## 项目最大的技术难点

最难的不是调用模型 API，而是跨边界保持一致性：

1. **Grounding**：RRF 排序、相关性闸门、模型输出和最终 Citation 必须是不同职责；“有引用”不等于“答案被证据支持”。
2. **副作用一致性**：确认、幂等业务写入和审计要尽量在同一事务，不能出现 Ticket 已创建但 audit 丢失。
3. **可恢复审批**：Approval decision 和 LangGraph resume 跨事务，需要不可变决定、checkpoint、恢复标记和并发锁来缩小崩溃窗口。
4. **评估语义**：每个指标必须说明分母、N/A、数据版本和可比条件，不能用一个平均分掩盖安全失败。

面试时应主动说明仍存在的限制：Approval decision/resume 尚非真正原子，需要生产级 outbox/reconciliation。

## 使用 Codex 辅助时，我实际负责了什么

推荐据实回答：

我使用 Codex 做代码检索、实现草案、测试补全、文档同步和重复验证，但项目责任没有外包给工具。我负责定义业务问题和 Phase 范围，决定哪些能力必须是确定性代码，审查权限、幂等、审计和 Mock/真实边界，选择验收标准，并根据代码、PostgreSQL 测试和运行结果决定是否通过。

我没有把生成代码直接当成完成结果。每个阶段都要求查看 Git diff、运行真实 PostgreSQL/pgvector integration、复现失败路径、修正文档漂移，并在不能解释或不能证明时停止。Codex 提高了实现和检索速度；架构取舍、风险接受、最终验证和面试解释仍由我负责。

只保留你本人确实做过、能展开解释的部分。如果你没有独立修改过某段代码，可以说你负责需求、审查和验证，而不要声称逐行手写。

## 快速追问题

### 为什么不让模型直接生成 SQL？

SQL 会绕过 Repository 的参数化、tenant/role scope、事务和审计，并把 Prompt Injection 变成数据操作。当前模型没有 SQL Tool，Analytics SQL 由后端固定查询实现。

### 为什么 Citation 由服务器生成？

模型只知道 E 标签。如果允许模型自由写文档名或 Chunk ID，它可以伪造来源；服务器根据本次授权 Retrieval 结果物化 Citation，保证 source binding。

### 为什么失败也要保存 trace？

只保存成功会造成 survivorship bias，无法统计 timeout、拒答和验证失败，也无法调查一次请求为什么没有完成。失败 trace 只保存安全 error code/stage，不保存 provider 敏感详情。

### 为什么 Mock 工具仍有价值？

Mock Adapter 隔离外部系统，却保留 Registry、Schema、Policy、timeout、observation、audit 和状态图这些生产式边界。它证明的是 Agent 工程能力，不是假装完成真实企业集成。
