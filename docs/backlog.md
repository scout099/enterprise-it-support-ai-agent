# Enterprise IT Support AI Agent：Delivery Backlog

## 使用方式

本 Backlog 是可调整的阶段计划。2026-07-19 的 Phase 2 指令把原计划中的“核心知识模型”和“知识文档导入”合并为一个可运行的垂直切片。2026-07-22 的明确指令将可信 RAG 定为 Phase 5。2026-07-23 的明确 Phase 6 指令把请求识别与 LangGraph 基础工作流合并为一个阶段，因此后续计划重新收敛为 Phase 7–12，但 MVP 范围不变。每个 Phase 都必须通过测试、静态检查、文档更新和独立验收后才能进入下一阶段。

共同完成条件：核心逻辑有单元测试，关键流程使用真实依赖做集成测试；不删除或跳过测试；不提交密钥；每个明确步骤追加 `docs/project_journal.md`；完成后停止等待用户指令。

## Phase 1：工程骨架与质量基线

### 目标

建立最小、可运行、可测试的 Python/FastAPI 工程。

### 输入

- Phase 0 产品范围、架构和 ADR；
- 空的业务代码仓库。

### 输出

- 配置、结构化日志、request ID 和统一错误；
- FastAPI health/readiness；
- PostgreSQL/pgvector、Alembic、pytest 和 Ruff 基础。

### 验收标准

- Compose、FastAPI、迁移、测试和 Ruff 可运行；
- 开发库与测试库隔离；
- 尚未实现知识、RAG、Agent 或工具业务。

## Phase 2：知识库数据模型与文档解析

### 目标

完成 Markdown、TXT、PDF 的版本化导入、边界感知切分、去重、持久化和只读查询，不调用任何模型。

### 输入

- Phase 1 工程与数据库基础；
- 三种虚构 IT 知识文档；
- Document、Version、Chunk 和 Duplicate Import 的领域定义。

### 输出

- `knowledge_sources`、`documents`、`document_versions`、`document_chunks` 和 migration；
- 统一 `DocumentContent` parser seam；
- 可配置且可追溯的 Chunking；
- 版本化 Ingestion Service、Repository、本地原文件存储；
- 四个知识文档 API 和失败响应；
- 三格式、重复、新版本、并发和 API 测试。

### 验收标准

- 三种格式均可上传并保存到 PostgreSQL；
- 相同 Document 的相同规范化内容复用 Version，变化内容创建新 Version并保留历史；
- 每个 Chunk 可追溯到 Version、Document、文件名和行号或页码；
- migration、pytest 和 Ruff 全部通过；
- 不包含 Embedding、向量检索、LLM 或 Agent。

## Phase 3：Embedding 与 pgvector 向量索引

### 目标

把已导入 Chunk 转换为向量并持久化到 pgvector，建立可替换 Provider、幂等重索引和失败隔离能力；本阶段不提供最终检索接口。

### 输入

- Phase 2 的不可变 Chunk；
- 可配置的 Embedding Adapter；
- Embedding 模型、维度、版本与批大小配置。

### 输出

- 可替换的 Fake 与 OpenAI-compatible Embedding Provider；
- 向量生成、保存、重建和 Profile 版本记录；
- 单文档索引 API、状态 API、批量 CLI 与失败隔离；
- pgvector 存储、维度函数和距离排序的底层集成验证。

### 验收标准

- 测试不调用真实外部 API，Provider 可替换；
- 重复索引不产生重复数据，文档更新只索引新 Chunks；
- 单批失败不回滚其他批次，维度错误不会入库；
- pytest、Ruff 和真实 pgvector 存储/距离运算验证通过；
- 不包含最终 Knowledge Retrieval 或 RAG 回答。

## Phase 4：混合检索与来源引用（Retrieval only）

### 目标

从 PostgreSQL/pgvector 返回经过权限过滤、混合排序且可引用的证据；本阶段不生成自然语言回答。

### 输入

- Phase 3 的 Chunk 向量与来源元数据；
- 人工标注的基础检索问题集；
- Document 状态、有效期与简化角色权限字段。

### 输出

- `KnowledgeRetriever.search(query, top_k, filters, user_context)`；
- PostgreSQL full-text、pgvector semantic retrieval 与 RRF；
- 检索前权限/状态/时间过滤和完整 Citation；
- Retrieval API、15 条评估集、Recall@3/Recall@5 CLI。

### 验收标准

- 检索默认只返回 active、已生效、未过期的最新可用版本；
- 无权限角色不能检索 role-restricted Document；
- VPN、Outlook、账号示例问题能命中对应文档且返回完整 Citation；
- Recall CLI 可执行；不调用聊天模型或生成回答。

原 Backlog 曾把 Retrieval 与 RAG 合并在本 Phase。2026-07-22 的执行指令明确把 Phase 4 限定为 Retrieval-only；随后项目所有者明确授权 Phase 5 实现回答生成、拒答、Prompt 和引用验证。

## Phase 5：可信 RAG 问答

### 目标

基于 Phase 4 Retrieval 提供第一个可演示、可追踪且不会自由伪造企业规则的带引用回答 MVP。

### 输入

- Phase 4 `KnowledgeRetriever`、Citation 与权限过滤；
- VPN、Outlook、账号虚构知识和当前 FastAPI/PostgreSQL 基础。

### 输出

- ModelGateway、Fake/OpenAI-compatible Adapter、超时/有限重试和调用元数据；
- 有界 Context、结构化回答、无证据拒答和确定性 Citation；
- conversations/messages、聊天 API、会话读取 API 和 CLI。
- raw keyword/vector 相关性闸门，以及 succeeded/refused/failed Turn trace。

### 验收标准

- VPN、Outlook、账号问题可返回真实 Retrieval Citation；
- 无证据、malformed 输出和 Citation 越界安全结束；
- 非空知识库无关问题拒答；失败 HTTP 保持安全且数据库存在失败轨迹；
- 多轮、角色权限、模型/Prompt/Token/延迟/request ID 可持久化；
- 测试不依赖真实模型 API。

## Phase 6：LangGraph Agent Runtime 与意图路由

### 目标

把可信 RAG 接入显式状态图，结构化识别知识问答、三类诊断、工单和不支持请求，并安全处理低置信度。

### 输入

- Phase 4 Retrieval、Phase 5 RAG 与 ModelGateway；
- 六类意图、风险、澄清、结束条件和升级规则。

### 输出

- `AgentState`、结构化分类 Schema、Prompt、版本和确定性路由；
- LangGraph intake、分类、澄清、RAG、三类诊断占位、升级和 finalize 节点；
- PostgreSQL checkpoint、`agent_runs`、`agent_steps`、最大节点、重试和超时；
- Agent 执行与轨迹读取 API。

### 验收标准

- 六类意图均可到达，低置信度只进入 clarification；
- 状态转换和节点失败可追踪，checkpoint 可恢复；
- 达到节点、重试或超时限制时安全结束；
- 原有 RAG Citation 保持正常；
- 不执行工具、外部命令、工单或任何写操作。

## Phase 7：Tool Registry、Policy、只读 Mock 工具与审计

### 目标

建立唯一受控工具路径，并为三类诊断加入只读 Mock 查询。

### 输入

- Phase 6 Agent Runtime；
- Mock 场景、演示用户和权限规则。

### 输出

- Tool Registry、输入输出 Schema、Policy、Tool Gateway；
- 只读 Mock Adapter 和工具调用审计。

### 验收标准

- 未注册、非法参数和越权调用被拒绝并审计；
- Agent 不能绕过 Gateway；
- LLM 没有 Shell、Python、SQL 或系统命令工具。

## Phase 8：本地 IT 工单、确认与审计

### 目标

把未解决诊断升级为本地结构化工单；R1 写操作必须确认，R3 只登记审批，并关联完整上下文与脱敏审计。

### 输入

- Phase 6 诊断路由结果与 Phase 7 审计结果；
- 本地工单字段和状态规则；
- R0/R1/R3 风险、确认、幂等和审计规则。

### 输出

- tickets/comments/pending confirmations/audit events 模型与 Repository；
- R0 status、R1 create/comment 和 R3 approval-only；
- Agent respond/confirm、Ticket/Audit 读取 API；
- 工单与 Agent Run、tool execution 和 audit event 关联。

### 验收标准

- 工单包含诊断摘要、已尝试步骤和 Run ID；
- 用户确认前不执行，确认时 Gateway 重新校验；
- 重试/重复确认不重复创建，失败不返回虚假工单号；
- 所有写入有脱敏审计，密码/Token/完整敏感正文不进入 audit；
- 不连接真实企业工单平台。

## Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批

### 目标

在不接入真实 SSO、Entra ID 或目录写入的前提下，实现简化但完整的本地企业治理流程。

### 输入

- Phase 6 Agent Run/checkpoint 与 Phase 8 R3 approval-only 占位；
- users/roles/permissions、本地风险与审批规则；
- “申请加入财务系统管理员组”模拟场景。

### 输出

- users/roles/permissions/user_roles/role_permissions；
- R0–R4 确定性 Policy Engine；
- approval_requests/approval_decisions；
- approver API、Agent interrupt/resume 和模拟执行结果。

### 验收标准

- 模型不能决定最终授权；
- R3 必须暂停等待授权人，R4 永远拒绝；
- 非 approver 和重复决定被拒绝；
- 批准/拒绝恢复原 Agent Run，已完成节点不重复；
- 审批、决定、恢复和模拟结果具有完整审计。

## Phase 10：基础 Agent 评估系统

### 目标

建立可重复的离线评估闭环，比较检索、回答、分类、工具、诊断和治理版本。

### 输入

- Phase 3–9 的输出和轨迹；
- 版本化人工核验数据集。

### 输出

- 30-case 严格 Evaluation Dataset、Case observation、Run metadata 和确定性指标；
- JSON 原始结果、Markdown 报告、类别统计、失败原因、previous-run diff 和回归门禁；
- 默认 Fake Provider 完整运行，以及与规则分开的可选 advisory Judge。

### 验收标准

- 同一数据集与配置可重复比较；
- 确定性指标与模型评分分开；
- 报告不只给平均分，包含逐案例失败和真实分母；
- 安全或关键质量门禁失败时 CLI 返回非零；
- Judge 记录模型/Prompt 版本、明确不是绝对真值，真实 Judge 仍需人工校准。

## Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard

### 目标

提供能演示完整 MVP 的简单 Streamlit UI 和 IT 工单数据分析能力，不扩展为 Next.js 或独立前端产品。

### 输入

- Phase 4–10 的问答、诊断、工具、工单、审批和评估能力；
- PostgreSQL 中的 Agent Run、Step、Tool、Ticket 与 Audit 轨迹。

### 输出

- IT Support Chat：模拟身份、多轮对话、状态、Citation、工具审计、确认/取消、Ticket Number 和 resolved/unresolved Feedback；
- Analytics Dashboard：工单/问题分布、自助/转人工、步骤/工具/响应时间、工具成功、满意度、失败原因和最近评估；
- `feedback` 数据表、反馈 API、后端 SQL/pandas 统计 API；
- 幂等固定虚构 seed、页面截图位置和 README 演示流程。

### 验收标准

- 用户能通过 UI 完成知识问答、诊断、R1 确认/取消、创建工单和反馈；
- Citation、工具调用和审计信息清晰展示；
- Dashboard 能体现工单数据分析能力，所有业务指标由后端计算；
- UI 只调用 FastAPI，不直接访问数据库、Adapter 或本地 Evaluation artifact；
- 固定 Mock 数据可完整演示。

## Phase 12：部署、CI、安全检查和作品集包装

### 目标

把安全预验收、可复现部署、自动化质量门禁和公开作品集材料收敛为最终交付阶段。

### 输入

- Phase 1–11 的完整应用；
- 安全清单、失败注入场景和端到端案例；
- 全新环境启动、CI 和作品集要求。

### 输出

- FastAPI/Streamlit 非 root 镜像、PostgreSQL/pgvector Compose 与安全 migration；
- Ruff、pytest、migration、Evaluation、Gitleaks 和 Docker build GitHub Actions；
- 上传、Prompt Injection、越权、敏感日志和任意执行安全回归；
- README、架构、5 分钟 Demo、面试指南、三方向简历 Bullet 与 Phase 报告。

### 验收标准

- 全新环境按 README 启动 db/migration/API/UI，重复 migration 不产生危险副作用；
- 无工具绕过、真实密钥、真实公司数据或未审计写操作；
- 关键失败路径安全结束，测试与 Evaluation Gate 通过；
- 文档明确区分已实现、Mock、验证证据和未来扩展；
- GitHub-hosted CI 在提交/推送后作为最终外部门禁确认。

旧 Backlog 曾把 Docker/作品集安排为 Phase 13。项目所有者在 2026-08-05 明确要求把部署、CI、安全检查与作品集包装统一作为 Phase 12 执行，因此 Phase 13 已合并，不再作为独立阶段。
