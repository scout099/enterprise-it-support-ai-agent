# Phase 12 Report：部署、CI、安全检查和作品集包装

## 结论

**CONDITIONAL PASS（本地工程门禁 PASS；GitHub-hosted CI 需在提交/推送后确认）。**

Phase 12 已把旧 Backlog 的安全预验收和 Docker/作品集交付合并完成。FastAPI、Streamlit、PostgreSQL/pgvector 和一次性 migration 可由 Docker Compose 完整启动；本地 245 项测试、migration drift、30-case Evaluation、两个镜像、健康检查、幂等 seed、Gitleaks 和安全边界检查均实际通过。

Phase 6–12 已收敛到本地阶段提交，但当前没有 push，因而没有 GitHub-hosted workflow run。仓库内 CI 配置和每个对应命令已在本机验证，但不能把这种证据写成“远端 CI 已绿”。除这个外部门禁外，没有剩余 Blocking 代码缺口。

## 验收矩阵

| 要求 | 状态 | 实现证据 | 运行证据 |
| --- | --- | --- | --- |
| FastAPI Dockerfile | 完成 | `docker/Dockerfile.api` | image build 成功，API healthy |
| Streamlit Dockerfile | 完成 | `docker/Dockerfile.streamlit` | image build 成功，UI healthy |
| PostgreSQL + pgvector | 完成 | `pgvector/pgvector:0.8.2-pg17-bookworm` | db healthy，真实测试通过 |
| Compose 一键启动 | 完成 | `compose.yaml` | db/api/ui healthy，migrate exited 0 |
| 安全自动 migration | 完成 | `scripts/run_migrations.py` | 连续执行两次均 no-op；单一 head/drift 通过 |
| Ruff/pytest/migration CI | 完成 | `.github/workflows/ci.yml` | 对应本地命令通过 |
| Evaluation regression CI | 完成 | Fake 30-case job | Gate PASS |
| secrets scan CI | 完成 | Gitleaks Action + `.gitleaks.toml` | worktree/history 均 0 leak |
| Docker build CI | 完成 | FastAPI/Streamlit matrix | 两个镜像本机构建成功 |
| `.env` / API Key 检查 | 完成 | `.gitignore` + security script | tracked/unignored scan + Gitleaks 通过 |
| 禁止任意代码工具 | 完成 | Registry/Gateway + AST gate | injection 零工具调用；AST scan 通过 |
| 日志脱敏 | 完成 | structured logging/redaction | logging 与失败路径回归通过 |
| 上传类型和大小 | 完成 | suffix + media type + 5 MB | 415/超限/损坏文件测试通过 |
| Prompt Injection | 完成 | user + retrieved-context cases | 聚焦与全量回归通过 |
| 越权访问 | 完成 | persisted actor/role + RBAC | Run/Ticket/Audit/Analytics/Approval tests 通过 |
| README 全主题 | 完成 | `README.md` | 命令、架构、边界与结果核对 |
| interview/demo/resume | 完成 | 3 份独立文档 | 必需主题和数字核对 |
| 删除无用/重复模块 | 完成 | 删除空 worker package | 引用/生成物/重复入口扫描 |
| GitHub-hosted CI | 待外部确认 | workflow 已就绪 | 未 commit/push，无远端 run |

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
- 自动迁移前读取 Alembic heads，要求恰好一个 head；已在 head 时直接退出；否则只允许 `upgrade head`，结束后再次核对；
- 不提供自动 downgrade、drop、reset、volume 删除或 seed；演示 seed 必须由用户显式运行。

实际验证：

- FastAPI、Streamlit、migrate 三个本地镜像均 build 成功；
- `docker compose ps -a`：db/api/ui healthy，migrate exited 0；
- `/health` 返回 ok，`/ready` 返回 database ok，Streamlit health 返回 ok；
- API/UI `id -u` 均为 `10001`；
- `docker compose run --rm migrate` 输出 `database already at Alembic head 20260801_0013`；
- seed 连续两次均返回 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；
- 容器内 Evaluation Gate PASS。

第一次容器 seed 暴露评估语料仍位于 `tests/fixtures/knowledge`，而镜像不包含测试目录。修复不是把整个 tests 复制进镜像，而是把 6 份虚构语料迁到 `data/evaluation/knowledge`，让测试、seed、Evaluation 和镜像共用正式资源路径。随后重建和连续 seed 通过。

## GitHub Actions

Workflow 使用最小 `contents: read` 权限和同分支并发取消，包含：

1. Quality：Ruff lint/format、compileall、pip check、仓库安全边界；
2. Tests：PostgreSQL 17 + pgvector service、隔离 test database、全部 pytest；
3. Migrations：安全迁移两次、`alembic check`；
4. Evaluation：Fake Provider 30-case Gate；
5. Secrets：完整 Git history Gitleaks；
6. Docker：FastAPI/Streamlit 两镜像 matrix build，不 push。

最终验证中曾把 `IT_SUPPORT_ENVIRONMENT=test` 设为整个 pytest 进程，导致 10 个专门验证 development 配置的单元测试被全局环境污染，结果为 `10 failed, 235 passed`。修复后只在 migrations/evaluation jobs 显式设置 test environment，pytest job 使用测试自身的 fixture/environment seam；标准命令恢复为 `245 passed`。这证明 CI 环境变量也属于待测试配置，不能假设“test”全局覆盖总是安全。

Workflow YAML 已解析；本地没有 `actionlint` 或 `act`，且尚未 push，因此 GitHub runner 的 action schema 与供应链下载仍需首次 hosted run 最终确认。

## 安全检查

### 仓库和密钥

- `.env` 与 `.env.*` 被忽略，只有 `.env.example` 允许提交；
- `scripts.check_security_boundaries` 扫描 tracked 和未忽略候选文件，拒绝 `.env`、private key 与高置信 OpenAI/AWS/GitHub/Google key 形状；
- Gitleaks v8.30.1 Darwin arm64 tarball 的 SHA-256 与官方 checksum `b40ab0...aeb6a5` 一致；
- 首轮 worktree 扫描的 5 个候选是 `.venv` 第三方 source map 和 3 条测试幂等值；最终配置只精确排除 `.venv` 路径和这 3 个显式非密钥值，没有禁用 generic rule；
- 最终文档同步后的 worktree 扫描约 6.17 MB、3 个 Git commits 扫描约 637 KB，均 `no leaks found`。

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
- `docs/resume_bullets.md`：AI 应用、AI 产品、数据分析各 3 条，数字仅引用 13 migrations、7 Mock tools、30 cases、245 tests 和真实本地 Gate；
- 文档明确不声称真实 SSO、Microsoft/ServiceNow/Jira 接入、生产业务提升、生产 SLA 或真实审批执行。

## 清理结果

- 删除无引用、只有未来预留 docstring 的 `apps/worker/__init__.py`；
- 没有跟踪 `__pycache__`、`.DS_Store`、pytest/Ruff cache、egg-info 或 Evaluation 运行产物；
- 保留 `scripts/evaluate_retrieval.py` 与 `scripts/run_evaluations.py`：前者是 Retrieval-only，后者是完整 Agent Evaluation，不是重复模块；
- 没有删除 Phase 6–11 的实现、迁移、测试、报告或截图；它们与 Phase 12 一起进入阶段收尾提交。

## 最终测试与评估

- 全量：`245 passed in 17.98s`；
- Ruff：`All checks passed!`；format：`170 files already formatted`；
- compileall、pip check、security boundary、Git whitespace：通过；
- migration 两次 no-op；`alembic check`：`No new upgrade operations detected.`；
- Evaluation run：`eval-20260805T141357Z-046e52d7`，Gate PASS；
- Recall@3/5：`1.0000 / 1.0000`；MRR：`0.8333`；
- Citation Validity：`1.0000`；Evidence Coverage：`1.0000`；Unsupported Claim Rate：`0.0000`；
- Refusal Correctness：`0.7778`，失败 `knowledge-07`、`knowledge-08`；
- Intent、Tool Selection、Tool Arguments、Workflow：`1.0000`；Prohibited Action Rate：`0.0000`；Tool Error Rate：`0.0000`；
- previous run 因 `knowledge_corpus_fingerprint_changed` 为 not comparable；没有报告虚假 delta。

本地评估第一次仍加载旧 site-packages 并访问迁移前 fixture 路径。重新执行 `.venv/bin/python -m pip install --no-build-isolation .` 后使用当前代码，CLI Gate PASS。README 的本地安装步骤已包含安装当前包；开发者改动安装态源码后也应先重装再做 composition-root/CLI smoke。

## 已知限制

- GitHub-hosted CI 未运行；只有提交/推送后才能确认 runner/action 行为；
- Python 依赖是 major-bounded ranges，不是完整 lockfile；本轮 Python 3.12 干净镜像构建成功，但长期发布仍需受控更新；
- Compose 是 localhost Demo，不包含 TLS、生产 secret manager、高可用、集群 migration lock、镜像签名或漏洞认证；
- 本地 actor/role 不是 SSO/可信 Principal，没有 tenant isolation；
- 所有企业工具是 Mock，本地工单不是 ServiceNow/Jira；R3 结果是 simulated only；
- Approval decision/resume 和文件/数据库边界仍存在非原子窗口；
- PDF 无 OCR，pgvector exact scan，Evaluation 只有 30 条虚构案例；
- Refusal Correctness 不是 1.0，groundedness 仍是有限词法检查；
- Phase 6–12 的跨 Phase 工作区已按项目所有者要求收敛为一个本地阶段提交；尚未 push 或 tag。

## 必须能解释的核心点

1. migration 为什么必须是独立 one-shot service，而不是每个 API worker 自动跑；
2. “已在 head 时 no-op”与“无 schema drift”为什么是两个不同检查；
3. Docker health、readiness 和业务正确性分别证明什么；
4. Gitleaks allowlist 为什么必须精确，而不能关闭 generic secret rule；
5. Prompt Injection 测试为什么必须断言零工具调用，而不只检查回答文本；
6. CI 的全局环境变量为什么可能改变单元测试语义；
7. hosted CI 未运行时，为什么只能报告本地对照门禁通过；
8. Mock/Fake 如何提供工程证据，又为什么不能代表真实企业效果。

## 建议版本

- 实际阶段提交：`feat(delivery): complete phases 6-12`
- 建议 Tag：GitHub-hosted CI 通过后使用 `phase-12-complete`

Phase 12 仓库内工程结论为 **PASS**，总体为 **CONDITIONAL PASS**，唯一外部条件是首次 GitHub-hosted CI。根目录 `AGENTS.md` 已建立并纳入阶段提交。本次到此停止，不自动开始新的 Phase。
