# Project Overview

Enterprise IT Support AI Agent 是一个模块化单体 FastAPI 项目，目标是构建可评估、可审计、可扩展的企业 IT 支持 MVP。

当前主数据流：

```text
Markdown/TXT/PDF
→ parse + version + chunk
→ embedding + pgvector
→ authorized keyword/vector retrieval
→ RRF + citation
→ bounded Context + structured ModelGateway
→ validated grounded answer or deterministic refusal
→ conversation/message trace
```

当前完成到 Phase 5，已提供第一个带真实引用、无证据拒答和完整调用轨迹的企业 IT 知识问答 MVP。模块边界、完整愿景和架构理由分别见：

- `docs/CURRENT_STATE.md`：当前可运行事实；
- `docs/ROADMAP.md`：阶段状态与后续边界；
- `docs/architecture/mvp_architecture.md`：模块与请求数据流；
- `docs/product_scope.md`：MVP 范围；
- `docs/project_journal.md`：追加式真实开发记录。

项目坚持：权限在确定性代码中执行；测试使用隔离 PostgreSQL/pgvector 与 Fake Provider；模型只能选择当前 Context 的证据标签，最终引用由服务器从真实 Retrieval Chunk 物化；真实企业系统通过未来受控 Adapter 接入。
