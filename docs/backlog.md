# Enterprise IT Support AI Agent：Delivery Backlog

## 使用方式

本 Backlog 是可调整的阶段计划。2026-07-19 的 Phase 2 指令把原计划中的“核心知识模型”和“知识文档导入”合并为一个可运行的垂直切片。2026-07-22 的明确指令将可信 RAG 定为 Phase 5，因此原请求识别及其后阶段顺延为 Phase 6–13，但 MVP 范围不变。每个 Phase 都必须通过测试、静态检查、文档更新和独立验收后才能进入下一阶段。

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

### 验收标准

- VPN、Outlook、账号问题可返回真实 Retrieval Citation；
- 无证据、malformed 输出和 Citation 越界安全结束；
- 多轮、角色权限、模型/Prompt/Token/延迟/request ID 可持久化；
- 测试不依赖真实模型 API。

## Phase 6：VPN、Outlook、账号请求识别

### 目标

识别三类 MVP IT 请求及 Other，并安全处理低置信度。

### 输入

- Phase 5 RAG 与 ModelGateway；
- 中英文、歧义和非 IT 标注集。

### 输出

- 分类 Schema、Prompt、版本和置信度规则；
- 分类评估与错误分析。

### 验收标准

- 四类都可到达，低置信度进入 Other；
- 非法模型输出不会造成未处理异常；
- 分类模块不调用工具或创建工单。

## Phase 7：LangGraph 基础诊断工作流

### 目标

把 VPN、Outlook、账号诊断建模为显式、可测试的状态流程。

### 输入

- Phase 4 Retrieval、Phase 5 RAG 与 Phase 6 分类；
- 三类诊断清单、结束条件和升级规则。

### 输出

- Agent Run/Step 状态、三类诊断图；
- 澄清、检索、建议、升级、最大步骤和错误状态。

### 验收标准

- 状态转换可追踪，信息不足时只问必要问题；
- 达到限制或依赖失败时安全结束；
- 不执行任何外部或通用命令。

## Phase 8：Tool Registry、Policy、只读 Mock 工具与审计

### 目标

建立唯一受控工具路径，并为三类诊断加入只读 Mock 查询。

### 输入

- Phase 7 Agent Runtime；
- Mock 场景、演示用户和权限规则。

### 输出

- Tool Registry、输入输出 Schema、Policy、Tool Gateway；
- 只读 Mock Adapter 和工具调用审计。

### 验收标准

- 未注册、非法参数和越权调用被拒绝并审计；
- Agent 不能绕过 Gateway；
- LLM 没有 Shell、Python、SQL 或系统命令工具。

## Phase 9：本地 IT 工单

### 目标

把未解决诊断升级为本地结构化工单并关联完整上下文。

### 输入

- Phase 7 诊断结果与 Phase 8 审计结果；
- 本地工单字段和状态规则。

### 输出

- 工单模型、Repository、创建/读取接口；
- 工单与 Agent Run、引用和审计关联。

### 验收标准

- 工单包含诊断摘要、已尝试步骤和 Run ID；
- 重试不重复创建，失败不返回虚假工单号；
- 不连接真实企业工单平台。

## Phase 10：基础 Agent 评估系统

### 目标

建立可重复的离线评估闭环，比较检索、回答、分类、工具和诊断版本。

### 输入

- Phase 3–9 的输出和轨迹；
- 版本化人工核验数据集。

### 输出

- Evaluation Dataset、Case、Run 和指标；
- 逐案例结果、失败原因和聚合报告。

### 验收标准

- 同一数据集与配置可重复比较；
- 确定性指标与模型评分分开；
- 报告不只给平均分，Judge 经过人工校准。

## Phase 11：简单 Web 使用界面

### 目标

提供能演示完整 MVP 的简单 Web UI，不扩展为独立前端产品。

### 输入

- Phase 2 文档导入；
- Phase 4–10 的问答、诊断、工具、工单和评估能力。

### 输出

- 对话、澄清、引用、诊断步骤、工具结果和工单展示；
- 文档上传、导入状态和基础反馈入口。

### 验收标准

- 用户能完成端到端路径；
- UI 区分知识证据、工具事实和模型建议；
- UI 不直接访问数据库或 Adapter。

## Phase 12：安全、可靠性与端到端预验收

### 目标

在打包前集中验证权限、审计、故障恢复、数据保留和关键用户旅程。

### 输入

- Phase 1–11 的完整应用；
- 安全清单、失败注入场景和端到端案例。

### 输出

- 权限与审计复核；
- 故障、恢复、超时和重试测试；
- 端到端预验收报告与必要修复。

### 验收标准

- 无工具绕过、密钥泄漏或未审计写操作；
- 关键失败路径安全结束；
- 已知限制与运行手册和代码一致。

## Phase 13：Docker 化、最终验收与作品集文档

### 目标

提供可复现的本地演示环境，完成全链路验收和面试材料。

### 输入

- Phase 1–12 的已验收功能；
- 全新环境启动要求与产品成功标准。

### 输出

- 应用镜像与最终 Docker Compose；
- 迁移、示例知识和演示数据初始化；
- 端到端验收脚本、README、架构说明和演示文档。

### 验收标准

- 全新环境按 README 可启动；
- MVP 全链路、测试和静态检查通过；
- 仓库和镜像无真实密钥；
- 文档明确区分已实现、Mock 和未来扩展。
