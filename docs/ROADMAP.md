# Roadmap

规范阶段细节位于 `docs/backlog.md`。本文件只提供当前状态索引，不复制全部 Backlog。

| Phase | 状态 | 结果 |
| --- | --- | --- |
| 0 | PASS | MVP 范围、模块化单体架构、ADR 与 Backlog |
| 1 | PASS | FastAPI、配置、logging、PostgreSQL/pgvector 基础 |
| 2 | PASS | 版本化知识导入、解析、Chunking 与文档 API |
| 3 | PASS | Embedding Provider、pgvector 持久化、索引 API/CLI |
| 4 | PASS | Retrieval-only：全文、向量、RRF、权限、Citation、Recall CLI |
| 5 | CONDITIONAL PASS（工程已通过，学习待验收） | 可信 RAG：ModelGateway、相关性拒答、Citation 来源绑定、完整 TurnTrace、Chat API/CLI |
| 6 | PASS | LangGraph：六类意图、澄清、RAG/诊断占位/升级路由、checkpoint、Agent Run/Step |
| 7 | CONDITIONAL PASS（工程已通过，学习待验收） | VPN/Outlook/账号显式诊断图、Tool Registry/Gateway/Policy、七个 Mock 只读工具与 tool audit |
| 8 | CONDITIONAL PASS（工程已通过，学习待验收） | 本地 tickets/comments、R0/R1/R3、pending confirmation、幂等写入与脱敏 audit |
| 9 | CONDITIONAL PASS（工程已通过，学习待验收） | 本地 RBAC、R0–R4 确定性 Policy、R3 人工审批、可恢复 checkpoint resume 与模拟执行 |
| 10 | CONDITIONAL PASS（工程已通过，学习待验收） | 30-case Agent 评估、确定性四层指标、Fake 全运行、报告/差异与安全回归门禁 |
| 11 | CONDITIONAL PASS（工程已通过，学习待验收） | FastAPI-only Streamlit Chat/Dashboard、Feedback、SQL/pandas 统计与幂等演示 seed |
| 12 | CONDITIONAL PASS（本地工程门禁通过，远端 CI 待首次运行） | Docker/Compose、安全 migration、GitHub Actions、安全回归、README 与作品集材料 |

Phase 4 原计划中的自然语言 RAG 回答先按 2026-07-22 指令移出，随后项目所有者明确授权为 Phase 5。2026-07-23 的明确指令把请求识别与 LangGraph 基础 Runtime 合并为 Phase 6，并另行明确授权 Phase 7 只读诊断与 Mock 工具。2026-07-24 先授权 Phase 8 本地工单、低风险写入、用户确认和审计，随后明确把 Phase 9 从旧 Backlog 的离线评估改为 RBAC、风险策略与 Human-in-the-loop 模拟审批。离线评估已于 Phase 10 实现；Phase 11 按 2026-08-01 指令使用 Streamlit，并增加后端 Feedback 和 Analytics。2026-08-05 的明确指令把旧 Backlog 的安全预验收和 Docker/作品集打包合并为最终 Phase 12，因此不再另设 Phase 13。未经项目所有者确认，不自动开始新的 Phase。
