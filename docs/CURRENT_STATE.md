# Current State

- **更新时间：** 2026-07-23
- **当前完成阶段：** Phase 5：可信 RAG 问答
- **工程结论：** PASS（本地演示 MVP；不等于生产安全认证或逐句事实蕴含）
- **阶段结论：** CONDITIONAL PASS（工程已通过；用户学习验收尚未完成）
- **数据库 Head：** `20260722_0006`
- **Git 基线：** `17255bd chore: import current project snapshot`

## 已实现

- FastAPI、统一错误、request ID、结构化日志、health/readiness；
- PostgreSQL/pgvector、Alembic 与版本化知识导入；
- Markdown、UTF-8 TXT、可提取文本 PDF、Chunking 和 Embedding Profile；
- PostgreSQL FTS、pgvector cosine retrieval、RRF、去重、top-k 与授权候选过滤；
- `SearchResult` 分离 `rrf_score`、`keyword_score`、`vector_similarity`；
- 配置化 `RelevancePolicy`：Fake Profile 只使用确定性关键词证据；真实向量阈值必须显式绑定 `<model>:<dimension>:<version>`，不匹配时配置失败关闭；
- Citation 来源绑定：模型只能选择 Context E 标签，服务器从授权 Retrieval 结果物化 title/version/section/chunk ID；
- `ModelGateway.generate_structured_response()`、Fake/OpenAI-compatible Adapter、每次 timeout、有限重试、Prompt/model/attempt/Token 元数据；
- strict `RAGModelOutput` 的全部字段均 required 且禁止额外字段；
- `RAGAnswerService`：相关性筛选、受控 JSON Context、Pydantic 校验、拒答与 Citation allowlist；
- `conversations`/`messages` 与 `TurnTrace`：succeeded/refused/failed、error stage/code、问题、query、Chunk IDs、模型/Prompt/Token、回答、延迟、request ID；
- `POST /chat/ask`、`GET /chat/conversations/{conversation_id}` 和 `python -m scripts.chat`；
- `phase-5-v1` 评测集：15 个正样本、3 个负样本，输出 Recall@3/5、闸门层 false-answer 代理指标和 abstention accuracy。

## 未实现

- 请求分类、LangGraph 诊断、工具、Policy/Audit、工单、Web UI；
- 可信身份认证、Principal/subject/tenant 绑定；
- 回答逐句蕴含评估或自动 groundedness 判定；
- 真实付费 Provider smoke。

## 验证快照

- 全量 pytest：`133 passed in 4.34s`；
- Phase 5 Blocking 聚焦回归：`60 passed in 2.39s`；
- Ruff lint：`All checks passed!`；
- Ruff format：`88 files already formatted`；
- compileall：成功；pip check：`No broken requirements found`；
- migration：test DB `0006 → 0005 → 0006` 成功，开发库和测试库均为 `20260722_0006 (head)`；
- Retrieval/abstention CLI：18 cases，Recall@3=`0.9333333333333333`、Recall@5=`1.0`、false_answer_rate=`0.0`、abstention_accuracy=`1.0`；CLI 明确输出 `false_answer_rate_scope=relevance_gate_proxy`；
- 默认 Fake 的真实 CLI 在 VPN 配置文档与 VPN 安全干扰文档并存时，按确定性关键词重合度选择配置片段并返回来源绑定 Citation；
- 非空知识库仅有 VPN 文档时询问量子打印机政策：拒答、不调用模型，但保存原始检索 Chunk IDs；
- timeout、Provider unavailable、malformed schema、Citation 越界和 retrieval failure：HTTP 安全 502/503，数据库均有 failed trace 且没有 Provider 原始异常正文。

## 已知限制与安全边界

- `user_role` 仍由请求体/query 自报，不构成可信认证或生产授权；当前 API 只能作为本地演示；
- Conversation 尚无 `subject_id/tenant_id`，不能用于多用户生产隔离；
- 真实 Embedding/Model endpoint 会接收员工查询和/或授权企业 Context，启用前必须完成数据区域、保留和组织政策确认；
- Citation 只保证来源绑定，不证明回答每句话被对应片段蕴含；
- 相关性阈值只针对当前演示 Profile/数据集；切换模型、维度、版本或语料后必须重校准并更新 Profile 绑定；
- `false_answer_rate` 是相关性闸门是否会把负样本交给模型的代理指标，不证明真实 Provider 的回答级错误率；
- 多轮历史保存但不自动进入下一轮 query/Prompt；
- Context 仍按字符上限截断首个超长 Chunk，完整 Chunk 策略尚未实施；
- Conversation GET 无分页，真实 Model/Embedding client 尚未统一 `aclose()`；
- 数据库本身不可用时，失败轨迹无法写回同一数据库，需由外部日志/监控承接；
- 根目录没有 `AGENTS.md`，没有虚构项目级 Agent 规则。

下一步必须由用户明确确认；当前任务不得自动进入 Phase 6 请求分类或后续 Agent Phase。
