# Phase 4 Report：混合检索与来源引用

## 结论

**PASS。** Phase 4 的 Retrieval-only 范围已完成。本阶段没有聊天模型调用、Prompt 或自然语言回答生成。

## 范围证据

| 要求 | 实现证据 | 验证 |
| --- | --- | --- |
| 统一接口 | `KnowledgeRetriever.search(query, top_k, filters, user_context)` | 单元与集成测试 |
| 关键词检索 | PostgreSQL FTS + `ts_rank_cd` | VPN keyword integration |
| 向量检索 | pgvector cosine distance + Profile 过滤 | exact Chunk nearest-neighbor integration |
| 混合排序/去重 | RRF(k=60)、Chunk ID dedupe、top-k | 纯融合测试与 API test |
| filters | document/source/status/effective/expires | database integration |
| 权限 | visibility + allowed_roles 进入两路共同 candidate subquery | employee denied/helpdesk allowed |
| Citation | title/version/section/chunk ID | API 与 integration assertions |
| API | `POST /knowledge/search` | VPN/Outlook/account、validation、empty list |
| 评估 | 15 cases、UUID 标签、3 份目标 + 3 份干扰语料、Recall CLI | Recall@3=0.8667；Recall@5=0.9333 |

## 数据流

```text
validated query + role + filters
→ query embedding
→ authorized latest-valid-version subquery
→ PostgreSQL FTS candidates + pgvector candidates
→ Reciprocal Rank Fusion
→ Chunk deduplication
→ top-k SearchResult + Citation
```

权限、Document 状态、有效期和最新 Version 选择都发生在候选 SQL 中。系统不会先检索受限内容再在 HTTP 或生成阶段删除。

## 关键文件

- `src/enterprise_it_support/knowledge/retrieval.py`；
- `src/enterprise_it_support/knowledge/search_routes.py`；
- `src/enterprise_it_support/knowledge/search_schemas.py`；
- `migrations/versions/20260722_0004_add_retrieval_permissions.py`；
- `src/enterprise_it_support/evaluation/retrieval.py`；
- `scripts/evaluate_retrieval.py`；
- `data/evaluation/retrieval_cases.json`；
- Retrieval unit/integration/API tests。

## 真实验证

- `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260719_0003`；
- `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；
- `.venv/bin/python -m pytest -q` → 最终 `92 passed in 2.93s`；
- `.venv/bin/ruff check .` → `All checks passed!`；
- `.venv/bin/ruff format --check .` → `72 files already formatted`；
- `.venv/bin/python -m compileall -q apps src migrations scripts` → 成功；
- `.venv/bin/python -m pip check` → `No broken requirements found`；
- 失败路径专项 pytest → `11 passed in 0.65s`；
- FTS `EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)` → `Bitmap Index Scan on ix_document_chunks_fts`；
- `IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.evaluate_retrieval --seed-fixtures` → 15 cases，Recall@3=`0.8666666666666667`，Recall@5=`0.9333333333333333`；
- 此前 Phase 4 验收的真实 Uvicorn/curl 仍记录为搜索 200、非法 top_k 422、空 user_role 422；本轮新增的 503/时间失败路径由专项 API tests 验证。

本轮修改后按项目普通安装约定重新安装本地 wheel，原 CLI 命令直接通过；没有增加 `sys.path` workaround。

## 严格审查修复闭环

- 无效/零 query 与 stored embedding 不再进入 cosine 排序，避免 PostgreSQL `NaN` 被转换成高相似度；
- keyword SQL 与 migration 的 FTS expression 完全一致，并由真实 EXPLAIN 证明 GIN index 可用；
- Provider error、timeout、错误维度、非有限值和数据库查询失败统一进入 Retrieval unavailable；HTTP 返回不泄漏下游细节的 503；
- 当前有效性始终强制执行；时间 filters 必须带时区且只能进一步收紧；新增已过期、未来截止和多版本 future-effective tests；
- 评估从 title 判定改为 source/title 唯一解析后的 Document UUID 判定，并加入三份近主题干扰语料。增强后不再宣称 1.0，保留真实 misses 作为基线。

## 安全审查

审查提出的 Important 1–4 与评估可信度问题均已修复，没有遗留 Blocking：查询和 filters 由 Pydantic/枚举/UUID/aware datetime 限制；SQLAlchemy 参数化用户输入；role-restricted 条件被两路检索共同复用；响应不含 raw file path、Embedding、allowed_roles 或 Provider 内部错误。

残余风险：`user_role` 是调用方自报字段，不能视为生产身份；角色精确匹配没有租户维度；真实 Embedding Provider 会接收用户 query。它们已记录为当前限制，后续必须由可信认证与企业数据策略解决。

## 已知限制与延后项

- exact vector scan，没有 ANN；
- `simple` FTS，没有中文分词；
- 15 条单目标 Document 评估不包含 MRR/nDCG 或生产语料；当前 `outlook-05` 在 top-5 miss；
- 无 RAG、回答生成、拒答、Prompt 或引用生成验证；
- 没有开始下一 Phase。

## 建议版本标识

- Commit：`feat(knowledge): add authorized hybrid retrieval`
- Tag：`phase-4-complete`
