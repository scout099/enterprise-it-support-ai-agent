# Enterprise IT Support AI Agent

Enterprise IT Support AI Agent 是一个面向企业内部员工的 IT 支持应用。本仓库当前完成到 **Phase 5：可信 RAG 问答**，已在版本化知识导入、授权混合检索和真实 Citation 之上实现结构化回答、无证据拒答、Conversation 轨迹、聊天 API 与 CLI。

当前尚未实现请求分类、LangGraph 诊断、工具调用、工单或 Web UI。完整 MVP 范围见 [`docs/product_scope.md`](docs/product_scope.md)，当前事实见 [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md)，Phase 5 验收见 [`docs/phase_reports/phase_5.md`](docs/phase_reports/phase_5.md)。

## 环境要求

- Python 3.12 或更高版本；
- Docker 和 Docker Compose；
- Git；
- 可访问 Python package index 的网络，用于首次安装依赖。

本项目在 Python 3.14.5 上完成 Phase 5 验证，最低兼容目标仍为 Python 3.12。

## 项目结构

```text
apps/                           应用 composition root
  api/                          FastAPI 入口
  worker/                       为后续后台任务预留，当前无业务逻辑
src/enterprise_it_support/
  interaction/                  HTTP 路由、Schema、middleware、错误处理
  platform/                     配置、logging、数据库生命周期
  knowledge/                    文档导入、Chunking、向量索引和混合检索
  conversation/                 会话、消息、聊天 API 与调用轨迹
  agent_runtime/                可信 RAG Answer Service；后续扩展诊断工作流
  tools/                        后续受控工具调用预留
  governance/                   后续权限与审计预留
  intelligence/                 可替换 Embedding 与 Model Gateway
  evaluation/                   检索 Recall 评估，后续扩展 Agent 评估
tests/                          单元测试与集成测试
migrations/                     Alembic 迁移
scripts/                        本地基础设施初始化脚本
docs/                           产品、架构、ADR、Backlog 和项目日志
```

## 安装

### 1. 创建本地配置

```bash
cp .env.example .env
```

`.env` 已被 Git 忽略。示例密码只适用于本地开发；不要把真实数据库密码或 API Key 写入仓库。

### 2. 创建虚拟环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
```

这里使用普通本地安装而不是 editable install。原因是部分 macOS/Python 3.14 环境会把 editable install 生成的 `.pth` 标为隐藏文件，导致 Python 启动时跳过源码路径。修改 `src/` 后请重新执行安装命令；Python 3.12/3.13 环境如确认 editable install 正常，也可以自行使用 `-e`。

## 启动 PostgreSQL 与 pgvector

```bash
docker compose up -d db
docker compose ps
```

Compose 会创建开发数据库和独立测试数据库。数据库数据保存在命名 volume 中，普通 `docker compose down` 不会删除数据。
PostgreSQL 端口只绑定到 `127.0.0.1`，不会直接暴露给局域网中的其他主机。测试环境还会拒绝与开发环境相同的数据库 URL。

## 运行数据库迁移

开发数据库：

```bash
.venv/bin/alembic upgrade head
```

测试数据库：

```bash
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head
```

迁移依次启用 PostgreSQL `vector` 扩展、创建知识表、增加 embedding Profile、Document visibility/roles 与 Chunk 全文 GIN 索引，并创建 conversations/messages 轨迹表。应用的 `/ready` 只有在数据库可连接并且 vector 扩展存在时才返回 ready。

## 启动 FastAPI

```bash
.venv/bin/uvicorn apps.api.main:create_app --factory --reload --no-access-log
```

默认地址：<http://127.0.0.1:8000>

可用接口：

- `GET /health`：只检查应用进程是否存活；
- `GET /ready`：检查 PostgreSQL 连接和 `vector` 扩展；
- `POST /knowledge/documents`：上传 Markdown、TXT 或 PDF；
- `GET /knowledge/documents`：列出逻辑文档和最新版本号；
- `GET /knowledge/documents/{document_id}`：读取文档及全部版本摘要；
- `GET /knowledge/documents/{document_id}/chunks`：读取最新版本的可追溯 Chunks；
- `POST /knowledge/documents/{document_id}/index`：索引 pending Chunks，可用 JSON `{"force": true}` 强制重算；
- `GET /knowledge/documents/{document_id}/index-status`：读取当前 Embedding Profile 覆盖状态；
- `POST /knowledge/search`：返回经过权限、状态和有效期过滤的混合检索证据；
- `POST /chat/ask`：检索授权知识、生成或拒答、保存轨迹并返回真实 Citation；
- `GET /chat/conversations/{conversation_id}?user_role=employee`：读取固定角色的完整多轮轨迹；
- `/docs`：FastAPI 自动生成的 OpenAPI 界面。

手动验证：

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/ready
curl -i \
  -F 'owner=Demo IT Operations' \
  -F 'source_name=Local SOP Library' \
  -F 'title=VPN Configuration SOP' \
  -F 'file=@tests/fixtures/knowledge/vpn_configuration_sop.md;type=text/markdown' \
  http://127.0.0.1:8000/knowledge/documents
```

批量索引所有 pending/stale Documents：

```bash
.venv/bin/python -m scripts.index_documents
```

执行 15 条 Retrieval 评估并显式导入三份目标文档与三份近主题干扰文档：

```bash
.venv/bin/python -m scripts.evaluate_retrieval --seed-fixtures
```

搜索请求示例：

```json
{
  "query": "VPN connection times out",
  "top_k": 5,
  "filters": {
    "source_type": "markdown"
  },
  "user_role": "employee"
}
```

`filters` 支持 `document_id`、`source_type`、`status`、`effective_at` 和 `expires_at`。默认只检索 active、当前已生效且未过期的最新 Document Version；两个时间 filter 必须带时区，并且只会进一步收紧当前有效性，不能复活已过期内容。当前 `user_role` 是 Phase 4–5 使用的简化调用上下文，不是可信认证；真实部署前必须由身份系统注入。

聊天请求示例：

```json
{
  "question": "How do I configure the company VPN?",
  "user_role": "employee",
  "conversation_id": null
}
```

简单 CLI 支持单次和交互模式：

```bash
.venv/bin/python -m scripts.chat --user-role employee --question "How do I configure VPN?"
.venv/bin/python -m scripts.chat --user-role employee
```

默认 `fake` ModelGateway 会从真实检索 Context 生成可重复的本地演示回答，不访问外部 API。真实 OpenAI-compatible 运行需要在被忽略的 `.env` 中配置 provider、model、base URL 和 API key；自动测试始终禁止真实模型。

每个 HTTP 响应都包含 `X-Request-ID`。调用方可以传入只含字母、数字、点、下划线或连字符的 `X-Request-ID`，否则系统会生成新的 UUID。

## 运行测试

确保数据库已经启动，并且开发库和测试库都执行过迁移：

```bash
.venv/bin/python -m pytest
```

测试包括：

- development/test 配置加载与数据库隔离；
- 结构化日志字段，以及键值、JSON、Bearer 和数据库 URL 凭证脱敏；
- `/health`、`/ready` 和 404、422、500 统一错误响应；
- 真实 PostgreSQL 成功连接、连接失败和 pgvector 扩展缺失检查；
- Alembic 在测试数据库上的真实迁移；
- TXT、Markdown、PDF 解析和损坏 PDF；
- Chunk 大小、重叠、段落边界和来源位置；
- 串行及并发重复导入、内容更新生成新版本；
- 三格式 API 上传、查询、空/超限/损坏/不支持文件和 404 失败响应。
- Fake Provider 稳定性、批量索引、重复跳过、force、新 Version、维度校验和 Provider 失败恢复；
- pgvector 实际向量存储、维度函数和 cosine distance 排序；
- 索引 API 与 CLI。
- PostgreSQL 全文关键词检索和 pgvector cosine semantic retrieval；
- 共同的状态、版本、有效期、Document、类型和角色权限过滤；
- RRF 混合排序、Chunk 去重、top-k 和完整 Citation；
- `/knowledge/search`、15 条查询数据集与 Recall@3/Recall@5 CLI。
- ModelGateway Fake/OpenAI-compatible 合同、超时、有限重试、JSON Schema 和 Token 元数据；
- 有证据回答、零证据/模型拒答、Context 上限、malformed 输出和 Citation 越界；
- conversations/messages migration、完整调用轨迹、多轮顺序和角色不变；
- `/chat/ask`、会话读取、VPN/Outlook/账号、角色受限知识和聊天 CLI。

数据库集成测试不会用 SQLite 或无意义 Mock 替代 PostgreSQL。

## 代码质量

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

自动格式化：

```bash
.venv/bin/ruff format .
```

## 配置说明

所有应用配置使用 `IT_SUPPORT_` 前缀：

| 环境变量 | 说明 |
| --- | --- |
| `IT_SUPPORT_ENVIRONMENT` | `development` 或 `test` |
| `IT_SUPPORT_DEBUG` | FastAPI debug 开关，本地示例默认关闭 |
| `IT_SUPPORT_LOG_LEVEL` | `DEBUG`、`INFO`、`WARNING`、`ERROR` 或 `CRITICAL` |
| `IT_SUPPORT_DATABASE_URL` | 开发数据库 SQLAlchemy URL |
| `IT_SUPPORT_TEST_DATABASE_URL` | 独立测试数据库 URL；test 环境必填 |
| `IT_SUPPORT_KNOWLEDGE_STORAGE_PATH` | 原始上传文件的本地存储根目录 |
| `IT_SUPPORT_KNOWLEDGE_MAX_FILE_SIZE_BYTES` | 单个上传文件最大字节数 |
| `IT_SUPPORT_KNOWLEDGE_CHUNK_SIZE` | 单个 Chunk 的估算 token 上限 |
| `IT_SUPPORT_KNOWLEDGE_CHUNK_OVERLAP` | 相邻 Chunk 的估算 token 重叠数 |
| `IT_SUPPORT_EMBEDDING_PROVIDER` | `fake` 或 `openai`；test 环境只能使用 fake |
| `IT_SUPPORT_EMBEDDING_MODEL` | Embedding 模型名称 |
| `IT_SUPPORT_EMBEDDING_DIMENSION` | 输出向量维度 |
| `IT_SUPPORT_EMBEDDING_VERSION` | 应用控制的索引版本 |
| `IT_SUPPORT_EMBEDDING_BATCH_SIZE` | 每次 Provider 调用的 Chunk 数量 |
| `IT_SUPPORT_EMBEDDING_BASE_URL` | OpenAI-compatible API base URL |
| `IT_SUPPORT_EMBEDDING_API_KEY` | 只放在环境变量或被忽略的 `.env` |
| `IT_SUPPORT_RETRIEVAL_EMBEDDING_TIMEOUT_SECONDS` | query embedding 超时上限，默认 10 秒 |
| `IT_SUPPORT_MODEL_PROVIDER` | `fake` 或 `openai`；test 环境只能使用 fake |
| `IT_SUPPORT_MODEL_NAME` | 配置的聊天模型名称；默认 `fake-chat-v1` |
| `IT_SUPPORT_MODEL_BASE_URL` | OpenAI-compatible Chat Completions base URL |
| `IT_SUPPORT_MODEL_API_KEY` | 只放在环境变量或被忽略的 `.env` |
| `IT_SUPPORT_MODEL_TIMEOUT_SECONDS` | 每次模型尝试的 timeout |
| `IT_SUPPORT_MODEL_MAX_ATTEMPTS` | 包含首次调用的最大尝试次数，范围 1–5 |
| `IT_SUPPORT_MODEL_MAX_OUTPUT_TOKENS` | 单次结构化回答输出上限 |
| `IT_SUPPORT_RAG_TOP_K` | 每次回答最多检索的 Chunk 数 |
| `IT_SUPPORT_RAG_MAX_CONTEXT_CHARS` | 传入模型的序列化 Context 字符上限 |

数据库 URL 使用 Pydantic `SecretStr` 保存。应用日志只输出固定字段，并对常见 `api_key`、`authorization`、`password`、`secret` 和 `token` 文本形式进行基础脱敏。

## 停止本地服务

```bash
docker compose down
```

## 当前功能范围

Phase 5 已实现：

- Phase 1 的配置、结构化日志、request ID、统一错误、健康检查和数据库基础；
- 四个知识库关系实体及 Alembic migration；
- Markdown、UTF-8 TXT 和可提取文本 PDF 的统一 `DocumentContent`；
- 可配置、保留标题/段落边界和来源位置的确定性 Chunking；
- SHA-256 内容去重、不可变版本历史和并发首次导入幂等；
- 生成式安全文件名的本地原文件保存；
- 四个知识文档 HTTP API；
- 三份完全虚构的 VPN、Outlook 和账号核心测试文档，以及三份近主题干扰文档；
- 真实 PostgreSQL 集成测试、pytest 和 Ruff 质量门禁。
- async `EmbeddingProvider` seam；
- 稳定、无外部调用的 Fake Provider 和真实 OpenAI-compatible Provider；
- pgvector 向量及模型、版本、索引时间；
- 默认幂等跳过和显式 force 重索引；
- 每批独立事务、维度验证、Provider 失败隔离和安全日志；
- 单文档索引 API、状态 API 和批量 CLI。
- `KnowledgeRetriever.search(query, top_k, filters, user_context)`；
- PostgreSQL full-text 和 pgvector exact cosine 两路候选检索；
- Reciprocal Rank Fusion、Chunk 去重和最终 top-k；
- 默认 active/当前有效/未过期/最新 Version 过滤；
- `public` 与 `role_restricted + allowed_roles` 检索前过滤；
- 包含标题、版本、Section 和 Chunk ID 的 Citation；
- Retrieval-only API 与可执行评估 CLI。
- `ModelGateway.generate_structured_response()`、Fake 与 OpenAI-compatible Adapter；
- 配置化模型、单次 timeout、有限瞬时重试、Prompt/model/Token/attempt 元数据；
- `rag-answer-v1`、有界 Context、结构化回答和确定性无证据拒答；
- 模型只选择 Context E 标签，最终 Citation 由 Retrieval `SearchResult` 物化；
- conversations/messages、完整回答轨迹、固定角色和多轮保存；
- `POST /chat/ask`、`GET /chat/conversations/{id}` 与 `scripts.chat` CLI；
- VPN、Outlook、账号和 role-restricted 知识的 Fake Model 演示测试。

重复判断基于同一 Knowledge Source、同一 Document title 和规范化文本的 SHA-256。相同内容复用已有 Version；内容变化创建新 Version 并保留历史。原始文件使用 UUID 文件名存入 `data/knowledge/raw/`，该运行目录不会提交到 Git。

Phase 5 明确不包含：

- 请求分类；
- Agent 或 LangGraph；
- 工具调用、企业系统 Adapter 或工单；
- Web UI。

已知限制：PDF 仅支持非加密、可提取文本的文件，不做 OCR；TXT/Markdown 只接受 UTF-8；向量检索为 exact scan，全文配置为 `simple` 且没有中文分词插件；角色名精确匹配，`user_role` 尚未连接可信认证；多轮历史已保存但不自动加入下一轮 Prompt；默认 Fake Model 只证明流程，真实 OpenAI-compatible endpoint 尚未做付费 smoke；服务器能保证引用来自当前 Retrieval，但逐句蕴含仍需要后续回答评估；15 条 Retrieval 数据仍是小型基线；本地文件系统和 PostgreSQL 不能组成单一原子事务。

## 开发记录

持续开发过程、真实问题和验证结果记录在 [`docs/project_journal.md`](docs/project_journal.md)。历史记录只追加，不覆盖。
