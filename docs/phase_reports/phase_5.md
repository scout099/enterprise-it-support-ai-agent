# Phase 5 Report：可信 RAG 问答

## 结论

**PASS。** Phase 5 已交付第一个可演示的企业 IT 可信 RAG MVP：VPN、Outlook 和账号问题可从授权知识生成结构化回答并展示真实 Chunk 引用；无证据时确定性拒答；Conversation 与模型调用轨迹保存到 PostgreSQL。没有开始请求分类、LangGraph、工具或工单。

## 范围证据

| 要求 | 实现证据 | 验证 |
| --- | --- | --- |
| ModelGateway | `generate_structured_response()`、Fake/OpenAI-compatible | gateway unit tests |
| timeout/retry | 每次 timeout、1–5 attempts、瞬时错误退避 | timeout/retry tests |
| 调用元数据 | provider、configured/resolved model、Prompt、attempt、五类 Token | unit + Repository/API |
| RAG 流程 | Retrieval → Context → model → validation → answer | RAG unit/API/CLI |
| 结构化回答 | 7 个业务字段与 Pydantic Schema | unit/API response |
| Prompt 约束 | 只用 Context、拒答、禁止伪造、事实/建议标签 | Prompt assertions |
| Citation 来源 | E 标签 allowlist → `SearchResult.citation` 物化 | 越界 test + API trace |
| Conversation | `conversations`/`messages`、完整 turn transaction | migration/Repository |
| 轨迹字段 | question/query/chunks/model/prompt/answer/latency/tokens/request ID | GET conversation |
| API | `POST /chat/ask`、`GET /chat/conversations/{id}` | HTTP integration/curl |
| 关键案例 | 充分证据、零证据、malformed、多轮、角色权限、Fake | pytest |
| CLI | 单次与交互式 `scripts.chat` | integration + real run |

## 数据流

```text
validated question + fixed local role
→ authorized KnowledgeRetriever
→ top-k SearchResult
→ bounded untrusted JSON Context with E labels
→ versioned Prompt + ModelGateway JSON Schema
→ Pydantic validation
→ answerable/refusal decision
→ E-label allowlist
→ server-side Citation materialization from SearchResult
→ atomic user + assistant Message save
→ HTTP/CLI structured answer
```

模型不能提供 document title/version/chunk ID 作为最终引用。它只能选择当前 Context 中的 `E1..En`；服务器拒绝空、重复或越界标签，并从对应的授权 Retrieval 结果创建 Citation。

## 关键文件

- `src/enterprise_it_support/intelligence/model_gateway.py`；
- `src/enterprise_it_support/agent_runtime/rag.py`；
- `src/enterprise_it_support/conversation/`；
- `migrations/versions/20260722_0005_add_conversations.py`；
- `apps/dependencies.py`、`apps/api/main.py`；
- `scripts/chat.py`；
- ModelGateway、RAG、Conversation、API、CLI tests。

## 关键设计决定

- Provider SDK retry 关闭，由应用显式控制 attempts，避免叠加重试；只重试 timeout、连接、限流和 5xx，Schema/认证/请求错误立即失败。
- 无 Retrieval 结果不调用模型；模型返回 `answerable=false` 时丢弃其自由文本并使用服务器固定拒答。
- Context 按实际 JSON 序列化长度限制，超长首个片段通过二分截断；知识片段被明确标记为不可信数据。
- Conversation 固定一个本地 role；继续会话或读取会话时角色不匹配返回 403。
- 一轮 user + assistant Message 在同一事务写入；assistant Message 保存完整模型与检索轨迹。
- 默认 Fake Model 复用真实 Retrieval，只回显受控知识片段用于无外部成本演示；真实模型名称始终来自配置。

## 真实验证

- test migration `20260722_0005 → 20260722_0004 → 20260722_0005`：成功；
- 开发库、测试库：`20260722_0005 (head)`；
- `.venv/bin/python -m pytest -q`：`116 passed in 3.61s`；
- Phase 5 聚焦 pytest：`57 passed in 2.73s`；
- `.venv/bin/ruff check .`：`All checks passed!`；
- `.venv/bin/ruff format --check .`：`87 files already formatted`；
- compileall：成功；pip check：`No broken requirements found`；git diff check：通过；
- 真实 CLI：VPN 回答返回 conversation ID、`fake-chat-v1`、`rag-answer-v1`、30 tokens 和真实 Chunk UUID；
- 真实 Uvicorn/curl：chat 200、trace GET 200、wrong role 403、blank question 422；
- GET trace 证明 assistant Message 保存 retrieval query、5 个 Chunk IDs、provider/configured/resolved model、attempt、Prompt、Token、latency 和 request ID。

## 安全与失败路径

- test 环境从 Settings 层禁止真实 Model Provider；测试未调用真实模型 API；
- API 不返回 Prompt 内容、Context、密钥、raw file path 或 Provider 异常正文；
- malformed structured output 与 Citation 越界返回安全 502；模型/检索/数据库不可用返回安全 503；
- role-restricted 文档仍在两路 Retrieval 候选 SQL 前过滤；employee 拒答、helpdesk 可回答的真实数据库案例通过；
- 同一 Conversation 不允许从 employee 切换为 helpdesk。

## 已知限制与延后项

- `user_role` 仍由调用方自报，不是生产认证；
- 多轮历史保存但不进入下一轮 Prompt/query；
- 默认 Fake Model 不是语言质量证明；真实 OpenAI-compatible endpoint 未做付费 smoke；
- 引用来源合法已确定性保证，但回答逐句是否完全被证据蕴含尚无版本化回答评估集；
- 模型失败 attempt 尚未持久化独立 Run/Step；本阶段只保存成功回答和确定性拒答；
- exact vector、`simple` FTS 和 Phase 4 小型 Recall 数据集限制保持不变。

## 学习与面试要点

- 为什么 Citation ID 必须由服务器从 Retrieval 结果生成，而不能信任模型自由输出；
- 为什么“无证据不调用模型”和“模型拒答时丢弃自由文本”是两层防线；
- 为什么 configured/resolved model、attempts 和 Token 需要一起保存；
- 为什么 Conversation role 固定仍不能替代真实认证；
- 为什么 116 个测试通过不能证明回答质量，需要单独回答评估集。

## 建议版本标识

- Commit：`feat(chat): add grounded RAG answers with citations`
- Tag：`phase-5-complete`
