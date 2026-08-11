# 简历项目描述

以下描述只使用当前仓库可以由代码、数据集、测试和 Phase 报告证明的数字。不要把虚构 Evaluation 或本地 Dashboard 指标写成真实企业业务收益。

## AI 应用开发实习

- 基于 FastAPI、LangGraph、PostgreSQL/pgvector 构建 Enterprise IT Support AI Agent，打通知识导入、混合检索、可信 RAG、3 类故障诊断、本地工单与 Human-in-the-loop 审批，使用 13 个 Alembic revision 管理可恢复数据演进。
- 设计统一 Tool Registry/Gateway，治理 7 个只读 Mock IT 工具及本地写工具，落实严格输入/输出 Schema、RBAC、R0–R4 风险策略、timeout/retry、幂等确认与脱敏审计，并显式禁止 Shell/Python/SQL 任意执行。
- 建立 30-case Agent Evaluation 与 251 项 pytest 回归体系，覆盖 Retrieval、Citation、意图、工具参数、工作流和禁止动作；最近确认基线达到 Recall@3/5 1.0、Refusal Correctness 1.0、Citation Validity 1.0、Prohibited Action Rate 0.0。

## AI 产品实习

- 将企业 IT 支持拆分为“知识自助—显式诊断—确认建单—人工审批—反馈分析”闭环，定义知识问答、VPN、Outlook、账号、工单和高风险请求 6 类用户意图，并明确 Mock、已实现与未来生产能力边界。
- 设计 5 分钟可复现 Demo 和两页 Streamlit 产品原型，集中呈现 Citation、Agent State、Tool audit、用户确认、Ticket Number、Feedback 及 10 类后端统计指标；前端只调用 FastAPI，避免复制权限和指标逻辑。
- 把产品质量转成 30 条版本化验收案例与 4 类回归门禁，报告保留逐案例失败、真实分母和 N/A，支持 previous-run diff，使“回答看起来合理”转化为可比较的检索、生成、流程和安全指标。

## 数据分析实习

- 基于 PostgreSQL Agent Run、Step、Tool、Ticket 和 Feedback 轨迹设计 Analytics 数据口径，用后端 SQL 聚合与 pandas 投影计算工单分类、自助/转人工、平均步骤/工具/响应时间、工具成功率、满意度和失败原因等 10 类指标。
- 构建 30-case 离线评估数据集，按知识 8、VPN 6、Outlook 6、账号 5、工单 3、高风险权限 2 分层，计算 Recall@3/5、MRR、Citation Validity、Workflow Completion 和 Prohibited Action Rate，并保留每个指标的 sample count 与 N/A。
- 设计可比性与回归规则：仅在 dataset SHA、corpus fingerprint 一致时做 previous diff，Gate FAIL 保留不可变 JSON/Markdown 报告但不覆盖成功 baseline，避免数据版本漂移或失败运行污染趋势判断。

## 使用提醒

- `251 tests` 来自 2026-08-11 Phase 12 发布收尾本地完整回归；后续增删测试时必须同步更新；
- 不要写“提升工单解决率 X%”，因为 Dashboard 使用虚构 seed，不是生产前后对照；
- 不要写“接入 Microsoft/ServiceNow”，当前只有 Mock Adapter 和本地工单；
- 面试时准备解释一个数字的定义、分母、数据来源和限制，而不只背诵 Bullet。
