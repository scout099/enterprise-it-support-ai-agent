# Current State

- **更新时间：** 2026-07-22
- **当前完成阶段：** Phase 5：可信 RAG 问答
- **工程结论：** PASS
- **数据库 Head：** `20260722_0005`

## 已实现

- FastAPI、统一错误、request ID、结构化日志、health/readiness；
- PostgreSQL/pgvector 与 Alembic；
- Markdown、UTF-8 TXT、可提取文本 PDF 的版本化导入和 Chunking；
- Fake/OpenAI-compatible Embedding Provider 与批量索引；
- `KnowledgeRetriever.search(query, top_k, filters, user_context)`；
- PostgreSQL FTS、pgvector cosine retrieval、RRF、去重和 top-k；
- document/source/status/effective/expires filters；
- public 与 role_restricted/allowed_roles 的候选查询前过滤；
- 包含 Document title/version、Section、Chunk ID 的 Citation；
- `POST /knowledge/search`；
- `phase-4-v2` 的 15 条 Retrieval 数据集、6 份目标/干扰文档及 Recall@3/Recall@5 CLI；相关性按唯一 Document UUID 判定。
- `ModelGateway.generate_structured_response()`、Fake 与 OpenAI-compatible Adapter；
- 模型单次 timeout、最多 1–5 次有限瞬时重试、configured/resolved model、Prompt 版本、attempt 和 Token 用量；
- `rag-answer-v1`：只使用企业 Context、证据不足拒答、不得伪造引用、区分知识库事实和一般建议；
- `RAGAnswerService`：授权 Retrieval、有界 JSON Context、Pydantic 输出校验、确定性 Citation allowlist；
- `conversations`/`messages` 与用户问题、query、Chunk IDs、模型/Prompt/Token、回答、延迟、request ID；
- `POST /chat/ask`、`GET /chat/conversations/{conversation_id}` 和 `python -m scripts.chat`；
- VPN、Outlook、账号、零证据、多轮、malformed 模型、引用越界和不同角色知识权限测试。

## 未实现

- 请求分类、LangGraph 诊断、工具、Policy/Audit、工单、回答质量评估、Web UI；
- 真实身份认证或企业目录角色注入。

## 验证快照

- 全量 pytest：`116 passed in 3.61s`；
- Ruff lint：`All checks passed!`；
- Ruff format：`87 files already formatted`；
- compileall：成功；
- pip check：`No broken requirements found`；
- Phase 5 聚焦测试：ModelGateway/RAG/Conversation/API/CLI/Retrieval `57 passed in 2.73s`；
- Retrieval CLI：15 cases，`Recall@3=0.8666666666666667`、`Recall@5=0.9333333333333333`；Recall@3 misses 为 `outlook-03/outlook-05`，Recall@5 miss 为 `outlook-05`；
- migration：test DB `0005 → 0004 → 0005` 成功，开发库和测试库均为 `20260722_0005 (head)`；
- 真实 CLI：VPN 问题返回 model=`fake-chat-v1`、prompt=`rag-answer-v1`、真实 Chunk UUID 和 conversation ID；
- 真实 Uvicorn/curl：chat 200、conversation trace 200、role mismatch 403、blank question 422；
- 会话读取确认保存 5 个 retrieved Chunk IDs、model provider/configured/resolved/attempt、Prompt、Token、延迟和 request ID。

## 已知限制

- `user_role` 由请求体提供，只满足当前简化接口，不构成可信认证；
- 多轮 Conversation 已保存，但历史消息不会自动进入下一轮 Retrieval query 或 Prompt；
- 默认 Fake Model 只证明受控流程；未使用真实密钥或付费 API 验证任一 OpenAI-compatible endpoint；
- 确定性代码保证 Citation 属于当前 Retrieval，但逐句证据蕴含仍需后续回答评估集；
- pgvector 使用 exact scan，尚无 HNSW/IVFFlat；
- PostgreSQL FTS 使用 `simple`，没有中文分词插件；
- Fake Embedding 的 15 条评估只证明当前六文档演示基线，不证明生产语义质量；当前 miss 已保留用于后续检索调优，而不是修改标签制造满分；
- Git 仓库仍没有初始提交，全部项目文件处于未跟踪状态；
- 根目录仍没有 `AGENTS.md`，本次没有虚构项目级 Agent 规则。

下一步必须由用户明确确认；当前任务不得自动进入 Phase 6 请求分类或后续 Agent Phase。
