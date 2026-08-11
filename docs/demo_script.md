# 5 分钟演示脚本

目标：在不使用真实企业账户、真实 API Key 或真实公司数据的情况下，演示可信 RAG、显式诊断、Mock Tool、确认建单、审计、Dashboard 和 Evaluation 闭环。

## 演示前准备

提前 3–5 分钟执行，不计入演示时间：

```bash
docker compose up --build -d
docker compose exec api python -m scripts.seed_phase11_demo
docker compose exec api python -m scripts.run_evaluations
docker compose ps
```

确认 `db`、`api`、`ui` healthy，`migrate` exited 0。打开：

- <http://127.0.0.1:8501>
- 备用 OpenAPI：<http://127.0.0.1:8000/docs>

浏览器使用本地虚构 actor，例如 `demo-employee`。不要输入真实姓名、邮箱、Ticket 或公司知识。

## 0:00–0:30：开场

讲解：

> 这是一个可审计的 Enterprise IT Support AI Agent。今天用完全虚构的数据演示三层能力：有来源的知识回答、多步骤 Mock 诊断，以及经过确认和审计的本地工单。所有模型和企业系统都是本地 Fake/Mock，不会修改真实账户。

指出页面左侧的模拟身份与角色，并说明它不是生产 SSO。

## 0:30–1:10：VPN 知识问答

在 **IT Support Chat** 输入：

```text
What is the approved VPN server address?
```

展示：

- intent 为 `knowledge_question`；
- final status 为 `completed`；
- Citation 的 Document title、version、section 和 Chunk ID；
- Agent Steps 中的 retrieve/compose/finalize。

讲解：

> 权限、状态和有效期在检索前过滤；模型只能选择当前 Context 的 E 标签，Citation 是服务器从真实 Retrieval Chunk 物化的。没有证据时系统会拒答，不会靠模型常识补企业规则。

## 1:10–2:05：Outlook 诊断与 Mock 工具

输入：

```text
Outlook desktop cannot receive all email and shows error 0x800401.
```

展开 Tool Executions，依次展示：

- `get_mail_service_status`；
- `get_account_status`；
- `search_existing_incidents`；
- `search_knowledge`。

讲解：

> 这些 observation 全是结构化虚构结果。Agent 不能自由选择任意函数：每个工具都经过 Registry、输入/输出 Schema、权限、timeout/retry 和 audit。项目中没有 Shell、Python 或 SQL Tool。

指出 Agent Step 与 Tool Execution 是两层不同轨迹：前者记录状态图步骤，后者记录受治理的工具调用。

## 2:05–3:05：用户确认与创建工单

输入：

```text
Create an IT ticket for this Outlook issue.
```

先停在 pending confirmation，展示脱敏参数摘要和 impact summary。

讲解：

> 创建工单是 R1 写操作。模型只能提出动作，原 actor 确认前数据库不会出现 Ticket。确认时 Gateway 会重新校验权限、参数、状态和幂等键。

点击 **Confirm**。展示：

- confirmation status `executed`；
- Ticket Number；
- 刷新后的 `create_ticket` Tool Execution；
- 重复确认不会创建第二张 Ticket。

如果演示取消分支，重新发起一条请求后点击 Cancel，并说明取消后不能再执行。

## 3:05–3:35：查看审计

先在 Chat 展开当前 Run 的 Tool Execution audit；如需展示全局审计，打开 FastAPI `/docs`，调用：

```text
GET /audit/events?actor_id=support-demo&user_role=it_support
```

展示 action、policy decision、result、request ID 和时间，不展示密码、Token、完整工单正文或 provider 异常。

讲解：

> 未注册、越权、失败和成功尝试都进入审计。成功业务写入和最小审计尽量在同一 PostgreSQL 事务，避免“动作成功但审计丢失”。

若本地 seed 的支持 actor 不同，以 OpenAPI 中当前可用的虚构 it_support actor 为准；不要临场改用真实身份。

## 3:35–4:20：Dashboard

切换到 **Analytics Dashboard**，使用 `it_support` 角色。依次指向：

- Ticket 分类和 VPN/Outlook/账号数量；
- 自助解决率与转人工率；
- 平均 Agent Steps、工具调用和响应时间；
- 工具成功率、满意度和失败原因；
- 最近 Evaluation。

讲解：

> Streamlit 不访问数据库，也不复制指标定义。PostgreSQL 保存原始轨迹，FastAPI 后端用 SQL 聚合、pandas 做有界投影。无样本返回 N/A，而不是伪装成 0%。

## 4:20–4:50：评估报告

在 Dashboard 的最近 Evaluation 表中打开最新 run，或在终端展示命令结果：

```bash
docker compose exec api python -m scripts.run_evaluations
```

讲解：

> 数据集有 30 条虚构案例，覆盖知识、三类诊断、工单和高风险权限。Gate 同时检查 Citation、意图、工具、工作流和禁止动作。失败报告会保留，但不会覆盖最后一个成功 baseline；安全退化让 CI 返回非零。

## 4:50–5:00：收尾

> 这个项目证明的是可控 Agent 的工程闭环，不是假装完成生产企业平台。当前没有真实 SSO、tenant 或企业 Adapter，R3 也只模拟执行。下一步会优先补可信身份、最小权限 Adapter 和数据治理，而不是增加任意工具。

## 演示失败预案

- UI 未启动：用 <http://127.0.0.1:8000/docs> 展示相同 API contract；
- 数据为空：重跑幂等 `seed_phase11_demo`，不会删除已有数据；
- migration 失败：查看 `docker compose logs migrate`，不要绕过 migration 启动 API；
- Evaluation 失败：展示失败原因和 immutable report，不修改阈值或删除案例来制造 PASS；
- Docker 不可用：明确说明环境阻塞，使用仓库截图和最后一次真实 Phase report，不声称现场运行成功。

## 演示边界清单

- 不输入真实 API Key、员工身份、公司域名或内部知识；
- 不连接真实 Microsoft、ServiceNow、Jira、VPN、目录或设备系统；
- 不演示 Shell/Python/SQL Tool，因为它们不存在；
- 不把本地 actor/role 说成生产认证；
- 不把模拟审批说成真实权限已修改；
- 不把一次 Demo 的 Dashboard 数字说成生产业务提升。
