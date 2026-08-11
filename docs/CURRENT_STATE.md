# Current State

- **更新时间：** 2026-08-11
- **当前完成阶段：** Phase 12：部署、CI、安全检查和作品集包装
- **阶段结论：** CONDITIONAL PASS（本地与 GitHub-hosted 工程门禁 PASS；仅学习验收待项目所有者完成）
- **数据库 Head：** `20260801_0013`
- **Git 状态：** Public GitHub 仓库已建立；Phase 12 PR #1、Dependabot 策略修复 PR #5 与最终证据 PR #7 已合并到 `main`

## 当前可运行能力

- FastAPI + PostgreSQL/pgvector 模块化单体，覆盖版本化知识导入、混合检索、可信 RAG、LangGraph Agent、7 个只读 Mock 工具、本地工单、RBAC、R0–R4、Human-in-the-loop 模拟审批、30-case Evaluation、Streamlit Chat/Dashboard；
- Tool 调用统一经过 Registry、严格 Schema、权限/风险 Policy、timeout/retry、幂等与脱敏审计；应用不存在 Shell、Python、SQL、`eval`、`exec`、`subprocess` 任意执行入口；
- Markdown/TXT/PDF 上传同时校验 suffix、allowlisted media type 和 5 MB 大小上限；检索内容与用户输入均视为不可信数据；
- Docker Compose 按 `db healthy → migrate exited 0 → api healthy → ui healthy` 启动；API/UI 使用 UID 10001 非 root，端口只绑定 localhost；
- 自动迁移要求单一 Alembic head，只执行 `upgrade head`，数据库已在 head 时 no-op，并在两条路径核验 migration-owned FTS GIN 表达式索引；不执行 downgrade、drop、reset 或 seed；
- GitHub Actions 包含 Ruff、pytest + 真实 pgvector、migration 重复 no-op + drift、30-case Evaluation、Gitleaks、`pip-audit` 和两个 Docker build；所有第三方 Actions 固定完整 SHA，pgvector 固定 digest，Dependabot 按月提出受控更新；
- Public GitHub 仓库已启用 vulnerability alerts 与 automated security fixes；平台返回 alerts endpoint 204，security fixes `enabled=true`、`paused=false`；
- README、5 分钟 Demo、面试指南、三方向简历 Bullet 与 Phase 12 报告已完成。

## Phase 12 验证快照

- 标准全量测试：`.venv/bin/python -m pytest -q` → `251 passed in 17.31s`；数据库语义使用真实隔离 PostgreSQL/pgvector；
- Ruff → `All checks passed!`；format → `172 files already formatted`；compileall、pip check、security boundary、Git whitespace 均通过；`pip-audit` → `No known vulnerabilities found`；
- migration：开发/测试库均已在 `20260801_0013`；安全入口连续执行两次均 no-op；`alembic check` → `No new upgrade operations detected.`；
- Evaluation：`eval-20260811T125222Z-6a3c661e`，Gate PASS 且 failed cases `[]`；Recall@3/5 `1.0/1.0`、MRR `0.9167`、Citation Validity `1.0`、Evidence Coverage `1.0`、Unsupported Claim Rate `0.0`、Refusal Correctness `1.0`、Intent/Tool/Workflow `1.0`、Prohibited Action Rate `0.0`；
- previous-run 与当前 dataset/corpus 可比较；Fake RAG 现要求具体事项词由证据支持，并用 3 个单元测试和完整 Evaluation 回归覆盖，仍不外推到真实 Provider；
- Docker：FastAPI、Streamlit、migration 镜像在隔离项目中从零 build；全新数据卷首次迁移成功，db/api/ui healthy、migrate exited 0，重复 migration 明确 no-op；
- 容器内 seed 连续两次均返回 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；容器内 30-case Evaluation Gate PASS；
- Gitleaks v8.30.1 官方包 SHA-256 `b40ab0…aeb6a5` 校验通过；精确 allowlist 后，最终工作区约 6.53 MB 与当前完整 Git history 均 `no leaks found`；仓库安全脚本也通过；
- Prompt Injection 聚焦测试、上传 MIME/大小测试和越权/审批/审计聚焦集均通过；完整行为由 251 项全量回归覆盖；
- 实际 HTTP 演示通过 VPN Citation、Outlook 四个 Mock Tool、R1 确认建单、Audit 和 Dashboard；失败场景验证错误 actor 确认 403、employee 读取 Analytics 403、伪装 PDF 上传 415。
- Dependabot 策略修复合并后的 `main` run [`31496706696`](https://github.com/scout099/enterprise-it-support-ai-agent/actions/runs/31496706696) 在 merge commit `d27fe8e` 上 success；Python dependency audit、migration、Gitleaks、Evaluation、Ruff/package、pytest + PostgreSQL/pgvector、FastAPI build、Streamlit build 共 8/8 jobs 通过；pip、GitHub Actions、Docker 三类 Dependabot hosted updates 也全部 success。

## 已知限制

- GitHub 仓库已按项目所有者明确授权切换为 Public；公开前的 Gitleaks、仓库安全脚本、虚构数据人工核对和最终 hosted CI 均已通过；
- Dependabot 产生的 Python 3.14 runtime 更新 PR #6 保持开放且未自动合并；它是后续独立评审项，不改变当前 Python 3.12 已验收基线；
- 当前依赖使用受 major version 约束而非完整 hash lockfile；本轮 Python 3.12 镜像从干净环境解析、构建和 smoke 通过，并由 pinned audit tool + Dependabot 管理当前风险，但生产可复现发布仍需正式锁定策略；
- 没有生产 SSO、可信 Principal、tenant isolation、真实企业 Adapter、secret manager、TLS、高可用、供应链签名或漏洞认证；本地 actor/role 仍是 Demo 输入；
- R3 只产生模拟结果；Approval decision 与 graph resume 仍非单一事务；本地文件与 PostgreSQL 也不是单一原子事务；
- PDF 不做 OCR；pgvector 当前 exact scan；30 条虚构 Evaluation 和词法 groundedness 不代表生产分布或 SLA；
- Streamlit 是同步本地 Demo，Dashboard 没有大规模性能、缓存、预聚合和生产数据生命周期验证；
- 根目录 `AGENTS.md` 已建立，固定 repo-first 接手、Phase 范围、确定性安全边界、真实 PostgreSQL 验证、文档闭环和 Git hygiene 规则。

## 阶段停止点

Phase 12 没有剩余已知 Blocking 工程缺口，本地与 GitHub-hosted 工程门禁均已通过，Public 作品集仓库已就绪。阶段保持 CONDITIONAL PASS 的唯一原因是项目所有者尚需独立完成本报告给出的学习任务；完成后才建议打 Tag。本次不开始新的 Phase。
