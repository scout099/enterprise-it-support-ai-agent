# Current State

- **更新时间：** 2026-08-05
- **当前完成阶段：** Phase 12：部署、CI、安全检查和作品集包装
- **阶段结论：** CONDITIONAL PASS（本地工程门禁 PASS；GitHub-hosted CI 需在提交/推送后确认）
- **数据库 Head：** `20260801_0013`
- **Git 状态：** Phase 6–12 与根目录工作规则已收敛到 `feat(delivery): complete phases 6-12` 阶段提交；提交后工作区 clean

## 当前可运行能力

- FastAPI + PostgreSQL/pgvector 模块化单体，覆盖版本化知识导入、混合检索、可信 RAG、LangGraph Agent、7 个只读 Mock 工具、本地工单、RBAC、R0–R4、Human-in-the-loop 模拟审批、30-case Evaluation、Streamlit Chat/Dashboard；
- Tool 调用统一经过 Registry、严格 Schema、权限/风险 Policy、timeout/retry、幂等与脱敏审计；应用不存在 Shell、Python、SQL、`eval`、`exec`、`subprocess` 任意执行入口；
- Markdown/TXT/PDF 上传同时校验 suffix、allowlisted media type 和 5 MB 大小上限；检索内容与用户输入均视为不可信数据；
- Docker Compose 按 `db healthy → migrate exited 0 → api healthy → ui healthy` 启动；API/UI 使用 UID 10001 非 root，端口只绑定 localhost；
- 自动迁移要求单一 Alembic head，只执行 `upgrade head`，数据库已在 head 时 no-op，不执行 downgrade、drop、reset 或 seed；
- GitHub Actions 包含 Ruff、pytest + 真实 pgvector、migration 重复 no-op + drift、30-case Evaluation、Gitleaks 和两个 Docker build；
- README、5 分钟 Demo、面试指南、三方向简历 Bullet 与 Phase 12 报告已完成。

## Phase 12 验证快照

- 标准全量测试：`.venv/bin/python -m pytest -q` → `245 passed in 17.98s`；数据库语义使用真实隔离 PostgreSQL/pgvector；
- Ruff → `All checks passed!`；format → `170 files already formatted`；compileall、pip check、security boundary、Git whitespace 均通过；
- migration：开发/测试库均已在 `20260801_0013`；安全入口连续执行两次均 no-op；`alembic check` → `No new upgrade operations detected.`；
- Evaluation：`eval-20260805T141357Z-046e52d7`，Gate PASS；Recall@3/5 `1.0/1.0`、MRR `0.8333`、Citation Validity `1.0`、Evidence Coverage `1.0`、Unsupported Claim Rate `0.0`、Intent/Tool/Workflow `1.0`、Prohibited Action Rate `0.0`；`knowledge-07/08` 仍为拒答准确性失败，Refusal Correctness `0.7778`；
- previous-run diff 因 `knowledge_corpus_fingerprint_changed` 明确为不可比较，没有把 MRR 差异伪装成回归或改进；
- Docker：FastAPI、Streamlit、migration 镜像实际 build 成功；Compose 中 db/api/ui healthy、migrate exited 0；`/health`、`/ready`、Streamlit `/_stcore/health` 均通过；
- 容器内 seed 连续两次均返回 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；容器内 30-case Evaluation Gate PASS；
- Gitleaks v8.30.1 官方包 SHA-256 校验通过；精确排除本地 `.venv` 和三条显式非密钥测试幂等值后，最终工作区约 6.17 MB 与 3 个 Git commits 均 `no leaks found`；仓库安全脚本也通过；
- Prompt Injection 聚焦测试、上传 MIME/大小测试和越权/审批/审计聚焦集均通过；完整行为由 245 项全量回归覆盖。

## 已知限制与未完成外部验证

- GitHub Actions workflow 已静态解析，所有对应命令和镜像在本机通过；但当前没有提交或 push，未产生 GitHub-hosted workflow run，因此不能声称远端 CI 已绿；
- 当前依赖使用受 major version 约束而非完整 lockfile；本轮 Python 3.12 镜像从干净环境解析、构建和 smoke 通过，但长期可复现发布仍应引入受控依赖更新流程；
- 没有生产 SSO、可信 Principal、tenant isolation、真实企业 Adapter、secret manager、TLS、高可用、供应链签名或漏洞认证；本地 actor/role 仍是 Demo 输入；
- R3 只产生模拟结果；Approval decision 与 graph resume 仍非单一事务；本地文件与 PostgreSQL 也不是单一原子事务；
- PDF 不做 OCR；pgvector 当前 exact scan；30 条虚构 Evaluation 和词法 groundedness 不代表生产分布或 SLA；
- Streamlit 是同步本地 Demo，Dashboard 没有大规模性能、缓存、预聚合和生产数据生命周期验证；
- 根目录 `AGENTS.md` 已建立，固定 repo-first 接手、Phase 范围、确定性安全边界、真实 PostgreSQL 验证、文档闭环和 Git hygiene 规则。

## 阶段停止点

Phase 12 的仓库内实现、本地验收和 Phase 6–12 阶段提交已完成，没有剩余 Blocking 代码缺口。唯一条件是 push 后观察 GitHub-hosted CI；本次不擅自 push 或 tag。未经项目所有者确认，不自动开始新的 Phase 或生产集成。
