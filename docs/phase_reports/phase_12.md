# Phase 12 Report：部署、CI、安全检查和作品集包装

## 结论

**CONDITIONAL PASS（本地与 GitHub-hosted 工程门禁 PASS；仅学习验收待项目所有者完成）。**

Phase 12 已把旧 Backlog 的安全预验收和 Docker/作品集交付合并完成。FastAPI、Streamlit、PostgreSQL/pgvector 和一次性 migration 可由 Docker Compose 完整启动；发布收尾后本地 251 项测试、migration drift、零失败 30-case Evaluation、两个镜像、全新数据卷启动、幂等 seed、Gitleaks、dependency audit 和安全边界检查均实际通过。

Phase 6–12 已收敛到经过脱敏的 Git history，并上传到私有 GitHub 仓库。Phase 12 PR #1 与 Dependabot 策略修复 PR #5 已合并；策略修复对应的 `main` run [`31496706696`](https://github.com/scout099/enterprise-it-support-ai-agent/actions/runs/31496706696) 在 merge commit `d27fe8e` 上 8/8 jobs success。没有剩余 Blocking 代码或托管门禁缺口；阶段仍为 CONDITIONAL PASS 的唯一原因是学习验收尚需由项目所有者独立完成。

## 验收矩阵

| 要求 | 状态 | 实现证据 | 运行证据 |
| --- | --- | --- | --- |
| FastAPI Dockerfile | 完成 | `docker/Dockerfile.api` | image build 成功，API healthy |
| Streamlit Dockerfile | 完成 | `docker/Dockerfile.streamlit` | image build 成功，UI healthy |
| PostgreSQL + pgvector | 完成 | 固定 `pgvector/pgvector:0.8.2-pg17-bookworm` digest | db healthy，真实测试通过 |
| Compose 一键启动 | 完成 | `compose.yaml` | db/api/ui healthy，migrate exited 0 |
| 安全自动 migration | 完成 | `scripts/run_migrations.py` | 全新库升级、重复 no-op、单一 head/drift、显式 FTS index contract 均通过 |
| Ruff/pytest/migration CI | 完成 | `.github/workflows/ci.yml` | hosted jobs 全部通过 |
| Evaluation regression CI | 完成 | Fake 30-case job，先迁移隔离数据库 | hosted Gate PASS |
| secrets scan CI | 完成 | checksum-verified Gitleaks CLI + `.gitleaks.toml` | hosted worktree/history 0 leak |
| dependency audit/update | 完成 | pinned `pip-audit` job + Dependabot | hosted dependency audit PASS |
| Docker build CI | 完成 | FastAPI/Streamlit matrix | hosted 两个镜像 build PASS |
| `.env` / API Key 检查 | 完成 | `.gitignore` + security script | tracked/unignored scan + Gitleaks 通过 |
| 禁止任意代码工具 | 完成 | Registry/Gateway + AST gate | injection 零工具调用；AST scan 通过 |
| 日志脱敏 | 完成 | structured logging/redaction | logging 与失败路径回归通过 |
| 上传类型和大小 | 完成 | suffix + media type + 5 MB | 415/超限/损坏文件测试通过 |
| Prompt Injection | 完成 | user + retrieved-context cases | 聚焦与全量回归通过 |
| 越权访问 | 完成 | persisted actor/role + RBAC | Run/Ticket/Audit/Analytics/Approval tests 通过 |
| README 全主题 | 完成 | `README.md` | 命令、架构、边界与结果核对 |
| interview/demo/resume | 完成 | 3 份独立文档 | 必需主题和数字核对 |
| 删除无用/重复模块 | 完成 | 删除空 worker package | 引用/生成物/重复入口扫描 |
| GitHub-hosted CI | 完成 | PR #1、PR #5、`main@d27fe8e` | run `31496706696`，8/8 jobs success |

## Docker 与迁移设计

```text
db: PostgreSQL 17 + pgvector
  └─ healthy
      └─ migrate: one-shot, upgrade-only
          └─ exited 0
              └─ api: /ready healthy
                  └─ ui: /_stcore/health healthy
```

- API/UI 基于 Python 3.12 slim，运行用户 UID/GID 为 10001；pip 安装发生在 build 阶段，应用运行时不是 root；
- 主机端口只绑定 `127.0.0.1`；知识文件和 Evaluation artifact 使用命名卷；
- Compose 默认使用 Fake Model/Fake Embedding 和本机占位数据库凭证；不需要真实 API Key；
- migration 是独立 one-shot service，不嵌入 Uvicorn/Streamlit worker；
- 自动迁移前读取 Alembic heads，要求恰好一个 head；已在 head 时 no-op；否则只允许 `upgrade head`，结束后再次核对；两条路径都核验 Alembic 无法稳定 round-trip 的 FTS GIN 表达式索引；
- 不提供自动 downgrade、drop、reset、volume 删除或 seed；演示 seed 必须由用户显式运行。

实际验证：

- 最终发布验收使用独立项目 `itagent_phase12_release` 和全新命名卷，从零 build FastAPI、Streamlit、migrate 三个镜像；
- 首次迁移日志为 `database migrated to Alembic head 20260801_0013`；`docker compose ps` 显示 db/api/ui healthy，migrate exited 0；
- `/health` 返回 ok，`/ready` 返回 database ok，Streamlit health 返回 ok；
- API/UI `id -u` 均为 `10001`；
- `docker compose run --rm migrate` 输出 `database already at Alembic head 20260801_0013`；
- seed 连续两次均返回 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；
- 容器内 Evaluation Gate PASS。

第一次容器 seed 暴露评估语料仍位于 `tests/fixtures/knowledge`，而镜像不包含测试目录。修复不是把整个 tests 复制进镜像，而是把 6 份虚构语料迁到 `data/evaluation/knowledge`，让测试、seed、Evaluation 和镜像共用正式资源路径。随后重建和连续 seed 通过。

## GitHub Actions

Workflow 使用最小 `contents: read` 权限和同分支并发取消，包含：

1. Quality：Ruff lint/format、compileall、pip check、仓库安全边界；
2. Dependencies：固定 `pip-audit==2.10.1`，按项目定义隔离解析并 strict 扫描；
3. Tests：PostgreSQL 17 + pgvector service、隔离 test database、全部 pytest；
4. Migrations：安全迁移两次、`alembic check`；
5. Evaluation：先迁移该 job 的隔离数据库，再运行 Fake Provider 30-case Gate；
6. Secrets：完整 Git history Gitleaks；
7. Docker：FastAPI/Streamlit 两镜像 matrix build，不 push。

最终验证中曾把 `IT_SUPPORT_ENVIRONMENT=test` 设为整个 pytest 进程，导致 10 个专门验证 development 配置的单元测试被全局环境污染，结果为 `10 failed, 235 passed`。修复后只在 migrations/evaluation jobs 显式设置 test environment，pytest job 使用测试自身的 fixture/environment seam；当时标准命令恢复为 `245 passed`。随后增加 3 个 migration contract 与 3 个 Fake RAG 证据充分性单测，当前为 `251 passed`。这证明 CI 环境变量和离线替身行为都必须进入回归，不能假设“test”全局覆盖或“检索到文档”就代表问题可回答。

所有第三方 Actions 均固定到经 GitHub API 解析的完整 commit SHA，CI/Compose pgvector 固定镜像 digest；`.github/dependabot.yml` 按月为 pip、GitHub Actions 与 Docker 提交 grouped minor/patch PR。当前仍没有完整 hash lockfile 或镜像签名，这些限制没有被 dependency audit 夸大为生产供应链认证。

私有仓库已启用 GitHub vulnerability alerts 和 automated security fixes；API 复核分别返回 204 与 `enabled=true, paused=false`。这些平台能力补充而不替代仓库内的 `pip-audit`、Gitleaks 和 Dependabot 配置。

首次 Dependabot Docker job 因 directory `/` 不含 Dockerfile 而失败；真实 Dockerfiles 位于 `/docker`。配置修正后，Docker run `31496712533`、pip run `31496712575`、GitHub Actions run `31496712820` 全部 success。三类配置显式忽略 semver-major；错误策略产生的 major PR 已关闭。平台另提出 Python 3.14 runtime PR #6，但未自动合并，当前验收基线仍为 Python 3.12。

第一次 hosted run `31494076726` 暴露两类只在 runner 上出现的问题：四个项目安装 job 使用 `--no-build-isolation`，但 runner 尚无 setuptools build backend；Gitleaks Action 在最小只读 token 下尝试访问不允许的 PR 资源。修复后项目安装恢复 PEP 517 隔离构建；Secrets job 改为直接下载固定 Gitleaks v8.30.1 Linux x64 包、校验官方 SHA-256 后扫描 Git history 和 worktree，不申请评论或写权限。第二次 hosted run `31494468543` 的全部 8 个 jobs 成功。

## 安全检查

### 仓库和密钥

- `.env` 与 `.env.*` 被忽略，只有 `.env.example` 允许提交；
- `scripts.check_security_boundaries` 扫描 tracked 和未忽略候选文件，拒绝 `.env`、private key 与高置信 OpenAI/AWS/GitHub/Google key 形状；
- Gitleaks v8.30.1 Darwin arm64 tarball 的 SHA-256 与官方 checksum `b40ab0...aeb6a5` 一致；
- 首轮 worktree 扫描的 5 个候选是 `.venv` 第三方 source map 和 3 条测试幂等值；最终配置只精确排除 `.venv` 路径和这 3 个显式非密钥值，没有禁用 generic rule；
- 文档收尾前重新校验官方 Gitleaks v8.30.1 Darwin arm64 包 SHA-256，worktree 约 6.54 MB 与 6 commits/约 1.63 MB history 均 `no leaks found`；推送后 hosted Gitleaks 也完成 history/worktree 双扫描并通过。

正则扫描不能证明“没有任何真实公司数据”。本轮还人工核对了演示 actor、文档 owner、工单、截图和报告语义，均按虚构/Mock 描述；公开前仍应由项目所有者再做一次人工内容审查。

### 任意执行与 Prompt Injection

- 应用 `apps/` 与 `src/` AST 门禁拒绝 `eval`、`exec`、`os.system`、`os.popen` 和 `subprocess`；
- Agent Registry 不注册 Shell、Python、SQL、系统命令或任意函数工具；
- 用户要求忽略指令并调用 `run_shell_command` 时，运行升级且 tool calls 为 0；
- 检索 Chunk 中的注入文本只作为 JSON user Context，System Prompt 明确 Context 不可信，回答不执行或回显命令；
- 这些用例证明已覆盖攻击的当前行为，不是对所有语言、编码和 provider 的形式化安全证明。

### 上传、日志和越权

- `.txt`、`.md/.markdown`、`.pdf` 必须同时满足 suffix 和 allowlisted media type；伪装 Shell 文本返回 415；
- 读取时执行 5 MB 大小上限，空文件、超限、损坏 PDF 继续保持原稳定错误；
- 日志/审计只保留 allowlisted 结构化字段，数据库 URL、Bearer/API key/password/secret/token 和 provider 异常正文有回归；
- Conversation role、Agent Run actor/role、Ticket ownership、Confirmation、Audit/Analytics、Approval approver/self-approval 和 Gateway permission 均有 deny 测试；
- 成功本地写入与最小 audit 尽量在同一 PostgreSQL 事务；真实企业系统没有接入。

## README 与作品集材料

- `README.md`：背景、业务问题、功能、Mermaid 架构、技术栈、目录、启动、Demo、RAG、Agent、Tool Gateway、Policy/审批、Evaluation、结果、限制和未来规划；
- `docs/interview_guide.md`：3 分钟介绍、RAG/Agent 顺序、State/Node/Edge、Tool/observation、LLM/确定性边界、幂等、权限、Evaluation、技术难点和 Codex 协作责任；
- `docs/demo_script.md`：5 分钟 VPN → Outlook → Mock tools → R1 确认 → Ticket/Audit → Dashboard → Evaluation；
- `docs/resume_bullets.md`：AI 应用、AI 产品、数据分析各 3 条，数字仅引用 13 migrations、7 Mock tools、30 cases、251 tests 和真实本地 Gate；
- 文档明确不声称真实 SSO、Microsoft/ServiceNow/Jira 接入、生产业务提升、生产 SLA 或真实审批执行。

## 清理结果

- 删除无引用、只有未来预留 docstring 的 `apps/worker/__init__.py`；
- 没有跟踪 `__pycache__`、`.DS_Store`、pytest/Ruff cache、egg-info 或 Evaluation 运行产物；
- 保留 `scripts/evaluate_retrieval.py` 与 `scripts/run_evaluations.py`：前者是 Retrieval-only，后者是完整 Agent Evaluation，不是重复模块；
- 没有删除 Phase 6–11 的实现、迁移、测试、报告或截图；它们与 Phase 12 一起进入阶段收尾提交。

## 最终测试与评估

- 全量：`251 passed in 17.31s`；
- Ruff：`All checks passed!`；format：`172 files already formatted`；
- compileall、pip check、security boundary、Git whitespace：通过；
- migration 两次 no-op；`alembic check`：`No new upgrade operations detected.`；
- `pip-audit`：`No known vulnerabilities found`；
- Evaluation run：`eval-20260811T125222Z-6a3c661e`，Gate PASS，failed cases `[]`；
- Recall@3/5：`1.0000 / 1.0000`；MRR：`0.9167`；
- Citation Validity：`1.0000`；Evidence Coverage：`1.0000`；Unsupported Claim Rate：`0.0000`；
- Refusal Correctness：`1.0000`；
- Intent、Tool Selection、Tool Arguments、Workflow：`1.0000`；Prohibited Action Rate：`0.0000`；Tool Error Rate：`0.0000`；
- previous run 与当前 dataset/corpus 可比较；没有用改变数据集或阈值制造 PASS。

本地评估第一次仍加载旧 site-packages 并访问迁移前 fixture 路径。重新执行 `.venv/bin/python -m pip install --no-build-isolation .` 后使用当前代码，CLI Gate PASS。README 的本地安装步骤已包含安装当前包；开发者改动安装态源码后也应先重装再做 composition-root/CLI smoke。

## 已知限制

- 私有 GitHub 仓库的 PR hosted CI 已通过；仓库尚未公开，公开可见性切换仍需项目所有者明确确认；
- Python 依赖是 major-bounded ranges，不是完整 hash lockfile；本轮干净镜像、dependency audit 与 Dependabot 通过，但生产发布仍需正式锁定；
- Compose 是 localhost Demo，不包含 TLS、生产 secret manager、高可用、集群 migration lock、镜像签名或漏洞认证；
- 本地 actor/role 不是 SSO/可信 Principal，没有 tenant isolation；
- 所有企业工具是 Mock，本地工单不是 ServiceNow/Jira；R3 结果是 simulated only；
- Approval decision/resume 和文件/数据库边界仍存在非原子窗口；
- PDF 无 OCR，pgvector exact scan，Evaluation 只有 30 条虚构案例；
- Refusal Correctness 已在固定 Fake 评估集达到 1.0，但 groundedness 仍是有限词法检查，不能代表真实 Provider 或生产问题分布；
- Phase 6–12 的跨 Phase 工作区已按项目所有者要求收敛并 push 到私有 GitHub 仓库；尚未 tag。

## 必须能解释的核心点

1. migration 为什么必须是独立 one-shot service，而不是每个 API worker 自动跑；
2. “已在 head 时 no-op”与“无 schema drift”为什么是两个不同检查；
3. Docker health、readiness 和业务正确性分别证明什么；
4. Gitleaks allowlist 为什么必须精确，而不能关闭 generic secret rule；
5. Prompt Injection 测试为什么必须断言零工具调用，而不只检查回答文本；
6. CI 的全局环境变量为什么可能改变单元测试语义；
7. 为什么本地门禁与 hosted CI 都要运行，且 runner 暴露了哪些本机没有出现的问题；
8. Mock/Fake 如何提供工程证据，又为什么不能代表真实企业效果。

## 建议版本

- 已有阶段提交：`feat(delivery): complete phases 6-12`
- 本轮建议 Commit：`fix(delivery): close phase 12 acceptance gaps`
- 建议 Tag：学习验收完成且 GitHub-hosted CI 通过后使用 `phase-12-complete`

Phase 12 工程结论为 **PASS**，总体为 **CONDITIONAL PASS**。唯一条件是项目所有者完成本轮给出的学习任务；GitHub-hosted CI 已 8/8 通过。根目录 `AGENTS.md` 已建立并纳入提交；仓库当前保持 private，尚未 tag。本次到此停止，不自动开始新的 Phase。

## 2026-08-05 收尾验收补充

### 审查问题与处理

| 级别 | 问题 | 处理结果 | 证据 |
| --- | --- | --- | --- |
| Blocking | Evaluation CI 在全新数据库上未先运行 migration | 已修复 | `.github/workflows/ci.yml` 的 Evaluation job；隔离 Compose Evaluation Gate PASS |
| Blocking（外部证据） | 2026-08-05 检查时尚无 GitHub-hosted run | 当时如实保留；2026-08-11 由 PR 与 main 多轮 8/8 success 关闭 | 当前 main run `31496706696` |
| Important | `pyproject.toml` 误写 `httpx2`，容器依赖传递安装 | 已修复为 direct runtime `httpx` | 干净 API/UI image build 日志直接安装 `httpx-0.28.1`；`pip check` PASS |
| Important | Alembic 对 migration-owned FTS index 的排除可能掩盖漂移 | 已补显式 contract verification 与 3 个失败路径单测 | `scripts/run_migrations.py`、`tests/unit/test_run_migrations.py` |
| Important | README/状态/报告中的提交数、测试数与当前事实过期 | 已同步 | README、Current State、Project Overview、resume bullets、本报告 |
| Optional | Streamlit 镜像安装完整后端依赖 | 未处理 | 不影响正确性或安全，属于后续体积优化 |

没有发现后续 Phase 功能提前实现、真实企业 Adapter、任意 Shell/Python/SQL Tool 或第二套重复授权系统。保留 Retrieval-only 和 Agent Evaluation 两个入口，因为它们评估层级不同，不是重复模块。

### 实际演示结果

- 正常：VPN knowledge question `completed` 且 1 个 Citation；Outlook diagnosis `completed` 并执行 4 个 allowlisted Mock tools；R1 工单由原 actor 确认后 `executed`；Audit 非空；Analytics 返回 200；
- 失败一：其他 employee 确认同一 pending action → 403 `confirmation_access_denied`；
- 失败二：employee 读取 Analytics → 403 `analytics_access_denied`；
- 失败三：`.pdf` 文件名配 `text/plain` → 415 `unsupported_document_media_type`。

### 最终证据命令

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m compileall -q apps src scripts migrations tests
.venv/bin/python -m pip check
.venv/bin/python -m scripts.check_security_boundaries
.venv/bin/python -m pytest -q
IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.run_migrations
IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic check
docker compose -p itagent_phase12_release up --build -d --wait
docker compose -p itagent_phase12_release run --rm migrate
docker compose -p itagent_phase12_release exec api python -m scripts.seed_phase11_demo
docker compose -p itagent_phase12_release exec api python -m scripts.run_evaluations
/private/tmp/gitleaks-v8.30.1/gitleaks git --no-banner --redact --config .gitleaks.toml .
/private/tmp/gitleaks-v8.30.1/gitleaks dir --no-banner --redact --config .gitleaks.toml .
```
