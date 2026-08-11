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
→ unresolved diagnosis or ticket request
→ pending confirmation / R3 approval request
→ human decision / checkpoint resume
→ rejected end or simulated execution
→ confirmed local ticket + audit
→ user feedback
→ bounded backend SQL/pandas analytics
→ FastAPI-only Streamlit Chat / Dashboard
```

当前完成到 Phase 12：在 Phase 1–11 的完整业务闭环上补齐 FastAPI/Streamlit 非 root 镜像、PostgreSQL/pgvector Compose、安全单次 migration、GitHub Actions、secret/任意执行门禁、Prompt Injection 与上传/越权回归，以及公开作品集所需 README、Demo、面试和简历材料。Streamlit 仍只通过 HTTP 调用 FastAPI；默认 Fake Provider 和固定虚构 seed 让完整演示不依赖真实企业账户或付费 API。

交付路径为：`Docker Compose → db healthy → one-shot migration → API ready → UI healthy`。CI 对应检查 Ruff、真实 PostgreSQL/pgvector pytest、migration drift、30-case Evaluation、Gitleaks、Python dependency audit 和两个 Docker build；第三方 Actions 与 pgvector 镜像使用不可变 SHA/digest，Dependabot 提供受控更新。本地 251 项测试、两个镜像、全新数据卷 Compose 健康检查、幂等 seed、零失败 Evaluation Gate、依赖漏洞扫描与工作区/Git 历史 secret scan 已通过；GitHub-hosted workflow 仍需在 push 后首次确认。

- `docs/CURRENT_STATE.md`：当前可运行事实；
- `docs/ROADMAP.md`：阶段状态与后续边界；
- `docs/architecture/mvp_architecture.md`：模块与请求数据流；
- `docs/product_scope.md`：MVP 范围；
- `docs/project_journal.md`：追加式真实开发记录。

项目坚持：权限在确定性代码中执行；测试使用隔离 PostgreSQL/pgvector 与 Fake Provider；模型只能选择当前 Context 的证据标签，最终引用由服务器从真实 Retrieval Chunk 物化；真实企业系统通过未来受控 Adapter 接入。
