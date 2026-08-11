# Phase 5 Report：可信 RAG 问答

## 结论

**工程 PASS，阶段 CONDITIONAL PASS（本地演示 MVP）。** 严格审查发现的三个 Blocking 已闭环：非空知识库中的低相关近邻不会再自动触发模型；RAG strict Schema 的全部字段均 required；retrieval/model/validation/citation 失败均保存安全 `failed` TurnTrace。工程条件已满足，但本轮新增的学习验收尚待项目所有者完成；该结论不宣称生产认证或回答逐句蕴含。

没有开始请求分类、LangGraph、工具调用或工单。

## 验收矩阵

| 要求 | 当前实现 | 验证 |
| --- | --- | --- |
| ModelGateway | Fake/OpenAI-compatible structured generation | Gateway contract tests |
| timeout/retry/usage | 每次 timeout、1–5 attempts、失败元数据、五类 Token | success/timeout/provider/malformed tests |
| strict Schema | 所有 RAG properties required，`additionalProperties=false` | explicit schema assertion |
| 相关性拒答 | raw keyword/vector signals + profile-bound `RelevancePolicy` | 非空 VPN 库询问量子打印机 |
| 受控 Context | 只使用通过闸门的授权 Search Results | relevant + distractor context test |
| Citation | 模型只选 E 标签，服务器从 SearchResult 物化 | empty/duplicate/out-of-range validation |
| Conversation | user + assistant outcome 同事务、多轮固定本地 role | PostgreSQL Repository/API tests |
| 失败轨迹 | succeeded/refused/failed + stage/code + model/retrieval metadata | 五类 HTTP + DB parameterized tests |
| API/CLI | `POST /chat/ask`、Conversation GET、单次/交互 CLI | integration tests |
| 评测 | 15 positives + 3 negatives | Recall、gate-proxy FAR、abstention CLI |

## 关键实现

```text
validated question + local demo role
→ authorized keyword/vector Retrieval
→ raw keyword/vector signals + RRF ordering
→ RelevancePolicy
→ no relevant evidence: deterministic refusal
→ relevant bounded/controlled evidence: versioned Prompt + strict ModelGateway
→ Pydantic validation
→ E-label allowlist and server-side Citation source binding
→ succeeded/refused/failed TurnTrace transaction
→ safe HTTP/CLI output
```

关键文件：

- `src/enterprise_it_support/knowledge/retrieval.py`；
- `src/enterprise_it_support/intelligence/model_gateway.py`；
- `src/enterprise_it_support/agent_runtime/rag.py`；
- `src/enterprise_it_support/conversation/`；
- `migrations/versions/20260722_0005_add_conversations.py`；
- `migrations/versions/20260722_0006_add_turn_outcomes.py`；
- `data/evaluation/retrieval_cases.json`、`scripts/evaluate_retrieval.py`；
- ModelGateway/RAG/Conversation/API/CLI/Retrieval tests。

## 三个 Blocking 的关闭证据

### 1. 相关性闸门

- `SearchResult` 不再用单一 `score` 混淆 RRF 排名与相关性；
- RRF 只排序，raw `keyword_score` / `vector_similarity` 由策略判断；
- Fake Embedding 是哈希向量，因此测试/默认演示只使用确定性关键词信号；
- 真实向量阈值必须绑定 `<model>:<dimension>:<version>`，Profile 不一致时配置失败；
- 低相关结果不进入模型 Context，但原始检索 IDs 仍保存用于审计；
- 默认 Fake 在多个通过闸门的同主题片段中按问题关键词重合度选择证据，配置文档 + VPN 干扰文档回归已覆盖；
- `phase-5-v1` 增加三个明确负样本。

最终评测快照：18 cases；Recall@3=`0.9333333333333333`、Recall@5=`1.0`、false_answer_rate=`0.0`、abstention_accuracy=`1.0`。其中 `false_answer_rate` 明确是 relevance-gate proxy，不是付费 Provider 的回答级指标。

### 2. strict JSON Schema

- `diagnosis/evidence_ids/limitations/next_steps` 不再有可省略默认值；
- 空数组仍允许，但必须由模型明确返回；
- 测试直接比较 `required` 与 `properties` 全集，并验证禁止额外字段。

### 3. 失败 TurnTrace

- `TurnTrace.status`：`succeeded / refused / failed`；
- `error_stage`：`retrieval / model / validation / citation`；
- 保存安全 `error_code`，不保存 Provider 原始异常正文；
- Gateway failure metadata 保存实际 attempts 和可得 Token usage；
- failed response 为 SQL `NULL`，数据库约束禁止与成功回答形态混淆；
- timeout、Provider unavailable、malformed schema、Citation 越界、retrieval failure 均已通过 HTTP + PostgreSQL 参数化测试。

## 最终验证

- `.venv/bin/python -m pytest -q`：`133 passed in 4.34s`；
- Blocking 聚焦回归：`60 passed in 2.39s`；
- Ruff：`All checks passed!`，`88 files already formatted`；
- compileall：成功；pip check：无损坏依赖；
- migration：test DB `0006 → 0005 → 0006` 成功；开发/测试数据库均为 `20260722_0006 (head)`；
- 实际 CLI：宽泛 VPN 配置问题返回 `VPN Configuration SOP`、`vpn.demo.invalid` 和来源绑定 Citation；量子打印机问题拒答且模型 attempts/tokens 为 0；
- 失败专项：retrieval、timeout、Provider unavailable、malformed schema、Citation 越界共 `5 passed`，均验证 HTTP + PostgreSQL failed trace；
- 自动测试没有访问真实模型或付费 API。

## 安全边界与延后项

- `user_role` 仍由调用方自报；Conversation 无 `subject_id/tenant_id`，因此当前权限只适合本地演示；
- 启用真实 Provider 会把员工 query 和/或企业 Context 发送到配置 endpoint，必须先确认数据策略；
- Citation 保证的是来源绑定，不是逐句蕴含；
- Context 首个超长 Chunk 仍可能字符截断；Conversation GET 尚无分页；真实 SDK client 尚未统一关闭；
- 相关性阈值必须随 Embedding Profile 和代表性语料重新校准并更新显式 Profile 绑定；
- FAR 是闸门代理指标；真实回答质量和逐句蕴含仍未评估；
- 数据库不可用时无法将失败写回同一数据库，应依赖外部日志/监控。

## Git 状态

- 基线提交：`17255bd chore: import current project snapshot`；
- Phase 5 修复应按 model schema、relevance gate、failed trace、docs 的逻辑提交组织；
- 只有上述验证保持通过时才可标记 `phase-5-complete`；未经用户确认不开始 Phase 6。
