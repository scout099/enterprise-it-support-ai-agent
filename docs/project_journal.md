# Enterprise IT Support AI Agent：项目开发日志

## 日志使用规则

本文件是项目持续开发、验证和学习记录。新记录只能追加到文件末尾，不删除、覆盖或改写已经完成的历史记录。每次开始新任务前，应先阅读文件末尾最近的步骤和 Phase 总结；每个明确子任务完成后，应先追加真实记录，再向用户汇报。

如果代码尚不存在，对“关键代码入口”应明确写“无业务代码入口”，不能虚构函数或类。命令、测试数量、问题和解决方法必须来自实际执行结果。

---

## Phase 0：确定项目 MVP 范围与基础架构

### Step 0.1：扫描空仓库并确认 Phase 0 工作范围

- **所属 Phase：** Phase 0：确定项目 MVP 范围与基础架构
- **完成日期：** 2026-07-19
- **本步骤目标：** 确认仓库是否已有代码、文档或项目级约束，避免覆盖用户已有内容，并确定 Phase 0 只做设计文档。
- **实际完成内容：** 检查工作目录、Git 状态、普通文件和 `AGENTS.md`。确认仓库只有 `.git`，没有提交、源码、依赖配置、README 或既有项目文档；因此按空仓库处理，只初始化 `docs/` 下的基础设计文档。
- **新增或修改文件：** 本步骤没有创建或修改文件。
- **请求或数据流程：**

  当前目录  
  → 枚举仓库文件与项目约束  
  → 检查 Git 工作区  
  → 确认空仓库  
  → 限定 Phase 0 为文档工作

- **关键代码入口：** 无业务代码入口；本步骤为只读仓库检查。
- **使用的核心技术：** Git、`rg`、Shell 文件系统检查。
- **为什么采用当前实现：** 开始项目前先确认真实仓库状态，可以避免覆盖用户文件，也能让后续新增文件清单准确。因为用户明确要求本阶段不实现业务代码，所以没有创建 Python 包或依赖配置。
- **运行与验证命令：** `pwd`、`rg --files`、`git status --short --branch`、`ls -la`。
- **测试结果：** 仓库扫描成功；Git 显示 `No commits yet on main`；未发现项目文件或 `AGENTS.md`。
- **遇到的问题：** 仓库没有任何可复用的工程结构，无法基于现有代码推断模块命名或技术约束。
- **解决方法：** 以用户给定的 MVP 清单作为唯一范围来源，并先建立产品范围、架构、Backlog 和 ADR 文档。
- **当前限制：** 尚无可运行应用、测试框架、数据库或 Docker 配置。
- **我需要理解的知识：** 开始开发前为什么要检查 Git 状态、项目约束和已有文件；设计阶段与实现阶段应如何分离。
- **与下一步骤的关系：** 扫描结果确认可以安全创建 `docs/product_scope.md`，下一步先固定产品范围，防止后续架构无限扩张。

### Step 0.2：定义个人作品集 MVP 产品范围

- **所属 Phase：** Phase 0：确定项目 MVP 范围与基础架构
- **完成日期：** 2026-07-19
- **本步骤目标：** 把最终企业平台愿景与当前个人作品集 MVP 分开，明确谁使用系统、解决什么问题、哪些能力进入第一版，以及如何判断项目成功。
- **实际完成内容：** 定义企业员工、IT 支持人员、知识库维护者和项目维护者四类角色；描述文档导入、带引用问答、请求分类、三类诊断、只读 Mock 工具、本地工单和评估场景；列出 MVP 功能和明确不做的功能；建立功能、质量和面试展示三类成功标准。
- **新增或修改文件：**
  - `docs/product_scope.md`
- **请求或数据流程：**

  员工问题  
  → 请求识别  
  → 企业知识检索  
  → 基础诊断  
  → 可选只读工具  
  → 回答或本地工单  
  → 保存轨迹并评估

- **关键代码入口：** 无业务代码入口；产品范围入口为 `docs/product_scope.md`。
- **使用的核心技术：** 产品范围建模、RAG 质量指标、Agent 工具治理概念。
- **为什么采用当前实现：** MVP 同时保留知识、Agent、工具、审计和评估闭环，但排除真实企业账号和高风险写操作，使项目既能展示真实 AI 应用工程，又能由个人安全地实现和演示。
- **运行与验证命令：** `test -s docs/product_scope.md`、`rg -n "MVP|明确不做|项目成功标准" docs/product_scope.md`。
- **测试结果：** 产品范围文档存在且非空；用户角色、核心场景、MVP 功能、非目标和成功标准均已覆盖。
- **遇到的问题：** “最终可以扩展为企业平台”容易导致第一版混入真实身份系统、复杂审批和分布式基础设施。
- **解决方法：** 增加“明确不做的功能”，并将所有质量目标标记为个人作品集 MVP 基线，而不是生产级承诺。
- **当前限制：** 质量阈值尚未通过真实评估集校准；当前只是后续 Phase 的验收目标。
- **我需要理解的知识：** MVP 不是功能越少越好，而是要形成最小完整价值闭环；产品目标必须转化为可验证的工程标准。
- **与下一步骤的关系：** 产品范围成为架构输入，下一步需要为范围中的每项能力确定模块职责和数据流。

### Step 0.3：设计模块化单体与完整请求数据流

- **所属 Phase：** Phase 0：确定项目 MVP 范围与基础架构
- **完成日期：** 2026-07-19
- **本步骤目标：** 设计一个可指导后续编码、但不过度复杂的 MVP 架构，并明确 LLM 与确定性代码的职责边界。
- **实际完成内容：** 选择模块化单体；定义 Web UI、FastAPI、Agent Runtime、Knowledge Ingestion、Knowledge Retrieval、Model Gateway、Tool Registry、Tool Gateway、Policy、Local Ticketing、Evaluation 和 Persistence 的职责；定义 Model、Tool、Persistence、Parser 四个关键 seam；绘制总架构、用户请求和文档导入三张 Mermaid 图；补充错误、安全、持久化和测试原则。
- **新增或修改文件：**
  - `docs/architecture/mvp_architecture.md`
- **请求或数据流程：**

  Web UI  
  → FastAPI  
  → Agent Runtime  
  → 分类与 Knowledge Retrieval  
  → Tool Registry + Schema + Policy + Mock Adapter  
  → 可选 Local Ticketing  
  → 有引用回答  
  → Evaluation

- **关键代码入口：** 无业务代码入口；架构入口为 `docs/architecture/mvp_architecture.md` 中的“模块职责与主要 interface”和“一次用户请求的完整数据流”。
- **使用的核心技术：** 模块化单体、深模块、依赖注入、Ports and Adapters、RAG、LangGraph 状态工作流、PostgreSQL/pgvector、Mermaid。
- **为什么采用当前实现：** 单一部署形态降低学习和运行成本；深模块和明确 seam 保证未来可以替换模型、工具 Adapter 或检索实现。LLM 只负责语义理解和自然语言生成，Schema、Policy、执行、审计和数据写入由确定性代码负责，以降低越权和幻觉风险。
- **运行与验证命令：** `rg -n "Web UI|FastAPI|Agent Runtime|Knowledge Retrieval|Model Gateway|Tool Gateway|Policy|PostgreSQL|Evaluation" docs/architecture/mvp_architecture.md`、Mermaid 代码块数量检查。
- **测试结果：** 指定的九个架构元素全部存在；三张 Mermaid 代码块开始和结束数量一致；请求流包含检索、工具 Policy、审计、本地工单和评估。
- **遇到的问题：** 初版请求时序图只通过文字提到可选工单，没有显式展示创建本地工单的步骤。
- **解决方法：** 在时序图中增加 `Local Ticketing` participant，并加入“未解决或用户要求升级”时使用幂等键创建工单的分支。
- **当前限制：** 本机未安装 Mermaid CLI，因此只完成代码块和关键节点的静态结构检查，尚未渲染为图片做视觉检查。
- **我需要理解的知识：** 模块与部署单元的区别；为什么 interface 是主要测试面；为什么 LLM 输出必须被视为不可信输入；为什么工具执行需要唯一网关。
- **与下一步骤的关系：** 架构明确了依赖顺序，下一步要把它拆成可以逐阶段验收的开发 Backlog，并记录关键取舍。

### Step 0.4：拆分 Phase 1–12 并记录基础架构决策

- **所属 Phase：** Phase 0：确定项目 MVP 范围与基础架构
- **完成日期：** 2026-07-19
- **本步骤目标：** 把 MVP 拆成可学习、可测试、可独立验收的开发顺序，并记录未来不应随意推翻的架构原因。
- **实际完成内容：** 创建 Phase 1–12 Backlog，每个 Phase 均包含目标、输入、输出和验收标准；开发顺序为工程骨架、数据库、文档导入、检索、RAG、分类、LangGraph 诊断、受控工具、工单、评估、Web UI 和 Docker 化验收；创建 ADR-0001，记录模块化单体、Mock Adapter、PostgreSQL + pgvector 以及先 RAG 后 LangGraph 的选择与后果。
- **新增或修改文件：**
  - `docs/backlog.md`
  - `docs/decisions/0001-mvp-scope.md`
- **请求或数据流程：**

  工程可运行  
  → 数据可持久化  
  → 文档可导入  
  → 证据可检索  
  → RAG 可引用  
  → 请求可分类  
  → 诊断可编排  
  → 工具可治理  
  → 工单可升级  
  → 质量可评估  
  → Web 可演示  
  → 环境可复现

- **关键代码入口：** 无业务代码入口；计划入口为 `docs/backlog.md`，架构决策入口为 `docs/decisions/0001-mvp-scope.md`。
- **使用的核心技术：** 增量交付、架构决策记录（ADR）、验收标准设计、测试金字塔。
- **为什么采用当前实现：** 先构建数据与 RAG 基线，再引入分类和 Agent，可以把检索错误、生成错误与状态工作流错误分开定位；把 Docker 完整交付放在最后，但数据库开发环境会在 Phase 2 提前建立。
- **运行与验证命令：** 检查 `## Phase 1` 到 `## Phase 12` 数量，并分别统计 `### 目标`、`### 输入`、`### 输出` 和 `### 验收标准`。
- **测试结果：** 检测到 12 个 Phase；四类必需字段均各出现 12 次；ADR 覆盖用户要求的四项决策理由。
- **遇到的问题：** 需要决定何时引入 LangGraph，过早加入会让 RAG 和工作流问题互相干扰，过晚则无法展示 Agent 状态管理。
- **解决方法：** 将 RAG 放在 Phase 5 完成并建立引用基线，Phase 6 完成分类，Phase 7 再引入 LangGraph；Tool Gateway 在 Phase 8 加入，确保工具治理单独验收。
- **当前限制：** Backlog 是当前决策快照；后续若范围变化，必须先更新产品文档或新增 ADR，再修改尚未执行的计划。
- **我需要理解的知识：** 为什么增量开发顺序也是架构决策；ADR 如何记录背景、决定、后果、替代方案和复审条件。
- **与下一步骤的关系：** Phase 0 文档已具备开发指导能力，下一步要建立持续项目日志机制并完成 Phase 0 静态验收。

### Step 0.5：建立追加式项目日志并完成 Phase 0 静态验收

- **所属 Phase：** Phase 0：确定项目 MVP 范围与基础架构
- **完成日期：** 2026-07-19
- **本步骤目标：** 建立贯穿整个项目的开发与学习记录，并保证后续每个明确步骤都先记录真实实现和验证结果，再向用户汇报。
- **实际完成内容：** 创建本文件并补录 Phase 0 的真实步骤；规定只追加、不删除或改写历史；要求新任务开始前阅读文件末尾；把项目日志更新加入 Backlog 的共同完成条件；检查四份 Phase 0 文档、12 个 Phase 字段、Mermaid 代码块、指定架构节点和禁用范围。
- **新增或修改文件：**
  - `docs/project_journal.md`
  - `docs/backlog.md`
- **请求或数据流程：**

  开始新任务  
  → 阅读项目日志末尾  
  → 扫描当前仓库  
  → 实现一个明确步骤  
  → 运行真实验证  
  → 追加步骤记录  
  → 向用户汇报

- **关键代码入口：** 无业务代码入口；日志入口为 `docs/project_journal.md`，共同完成条件位于 `docs/backlog.md` 的“使用方式”。
- **使用的核心技术：** Append-only 工程日志、Markdown、Git 静态检查、Shell 一致性检查。
- **为什么采用当前实现：** 追加式记录可以保留技术决定和真实问题的演进过程，适合初学者复盘，也能防止后续开发与先前设计不一致。将规则同时写入 Backlog，可以让每个 Phase 的完成标准都包含日志更新。
- **运行与验证命令：** `git diff --check`；检查四个 Phase 0 文档非空；统计 12 个 Phase 及其目标、输入、输出和验收标准；检查 Mermaid fence；搜索禁用范围和未完成占位标记；检查项目日志必需字段。
- **测试结果：** 文档静态检查全部通过；Phase 0 没有业务测试可运行；项目日志包含五条步骤记录和一份 Phase 总结。
- **遇到的问题：** 项目日志要求是在 Phase 0 完成后新增的，之前没有逐步骤实时记录；工作区还出现一个与本任务无关的未跟踪 `.DS_Store`。
- **解决方法：** 根据已经执行过的命令、文件变更和真实问题补录 Phase 0，不虚构代码或测试；保留 `.DS_Store` 不动，避免擅自删除用户或系统文件。今后所有步骤改为完成后立即追加。
- **当前限制：** Markdown Lint 和 Mermaid CLI 当前不可用；本步骤只能做结构、字段、关键词和 Git whitespace 检查。
- **我需要理解的知识：** 项目日志不是结果清单，而是目标、实现、验证、问题、限制和下一步之间的因果记录；日志必须与仓库现状一致。
- **与下一步骤的关系：** Phase 0 正式封闭。开始 Phase 1 前，必须先阅读本文件末尾和 Phase 0 总结，再按 Backlog 只实现工程骨架与质量基线。

## Phase 0 总结与索引

### 阶段结论

Phase 0 已将空仓库转化为一个有明确范围、架构、交付顺序和决策依据的项目。没有引入业务代码或运行时依赖。MVP 与未来企业平台已经分离，后续开发必须遵守“证据优先、确定性治理、所有工具走统一入口、先 RAG 后 Agent 编排”的原则。

### 步骤索引

| 步骤 | 主题 | 主要产物 |
| --- | --- | --- |
| Step 0.1 | 仓库扫描与范围确认 | 空仓库结论，无文件变更 |
| Step 0.2 | MVP 产品范围 | `docs/product_scope.md` |
| Step 0.3 | 模块化单体与数据流 | `docs/architecture/mvp_architecture.md` |
| Step 0.4 | Phase 1–12 与架构决策 | `docs/backlog.md`、`docs/decisions/0001-mvp-scope.md` |
| Step 0.5 | 项目日志与静态验收 | `docs/project_journal.md`、`docs/backlog.md` |

### Phase 0 验收状态

- MVP 和未来扩展范围清晰分离：通过；
- 模块化单体及模块职责明确：通过；
- 完整请求数据流和 LLM 职责边界：通过；
- Phase 1–12 均有目标、输入、输出和验收标准：通过；
- Mermaid 架构图包含全部指定模块：通过；
- 没有业务代码：通过；
- 运行时 Mermaid 视觉渲染：尚未执行，记录为当前限制。

### 下一 Phase 入口

Phase 1 只建立 Python/FastAPI 工程骨架、配置、健康检查、测试和静态检查基线，不实现数据库、RAG、Agent 或工具业务能力。开始前应重新检查仓库状态，并阅读本总结。

---

## Phase 1：项目工程初始化

### Step 1.1：建立目录、依赖与环境配置

- **所属 Phase：** Phase 1：项目工程初始化
- **完成日期：** 2026-07-19
- **本步骤目标：** 建立 Python 3.12+ 项目骨架和可验证的环境配置，让开发与测试使用明确分离的数据库 URL，并保证本地密钥不进入 Git。
- **实际完成内容：** 创建 `apps/`、`src/enterprise_it_support/`、`tests/`、`migrations/` 和 `scripts/` 基础目录；配置 FastAPI、Pydantic Settings、SQLAlchemy、Alembic、psycopg、pgvector、pytest、Ruff 和 Uvicorn 依赖；创建本地虚拟环境；实现 `Environment`、`Settings`、`active_database_url` 和缓存入口 `get_settings()`；通过 `.gitignore` 排除 `.env`、虚拟环境和缓存；提供不含真实凭证的 `.env.example`。
- **新增或修改文件：**
  - `.gitignore`
  - `.env.example`
  - `pyproject.toml`
  - `README.md`
  - `apps/__init__.py`
  - `apps/api/__init__.py`
  - `apps/worker/__init__.py`
  - `src/enterprise_it_support/__init__.py`
  - `src/enterprise_it_support/platform/config.py`
  - `src/enterprise_it_support/*/__init__.py`
  - `tests/unit/platform/test_config.py`
  - 测试目录中的 `__init__.py`
- **请求或数据流程：**

  操作系统环境变量或本地 `.env`  
  → Pydantic Settings 读取  
  → 类型与必填项校验  
  → 根据 `development` 或 `test` 选择数据库 URL  
  → 以 `SecretStr` 保护原始配置值

- **关键代码入口：** `enterprise_it_support.platform.config.Settings`、`Settings.active_database_url`、`get_settings()`。
- **使用的核心技术：** Python 3.14.5（项目兼容目标为 3.12+）、Pydantic Settings 2、pytest 9、Ruff 0.15、setuptools `src` layout、虚拟环境。
- **为什么采用当前实现：** 使用 `src/enterprise_it_support/` 可以保留 Phase 0 的领域模块划分，同时避免顶层 `platform` 与 Python 标准库同名冲突。测试配置必须提供单独 URL，防止测试误连开发库。数据库 URL 使用 `SecretStr`，降低调试输出泄漏密码的风险。
- **运行与验证命令：** `python3 -m venv .venv`；`.venv/bin/python -m pip install -e '.[dev]'`；`.venv/bin/python -m pytest tests/unit/platform/test_config.py -q`；`.venv/bin/ruff check src/enterprise_it_support/platform/config.py tests/unit/platform/test_config.py`。
- **测试结果：** 配置测试先因 `enterprise_it_support.platform.config` 不存在而红灯；实现后 `3 passed`。Ruff 最终输出 `All checks passed!`。
- **遇到的问题：** 沙箱内首次安装依赖无法解析 PyPI；获得联网许可后，第一次下载仍在中途结束，只安装了部分包；完整安装后 Ruff 又发现测试文件导入顺序不符合规范。
- **解决方法：** 使用获准的项目本地 pip 安装重试，直至 editable package 和全部依赖安装成功；运行 `ruff check --fix` 修正导入顺序，然后重新执行测试和 Ruff。
- **当前限制：** 目前只有配置模块；README 还是临时说明；Docker、数据库、HTTP 接口和 logging 尚未建立。
- **我需要理解的知识：** Pydantic Settings 如何把环境变量映射为强类型配置；为什么测试数据库必须隔离；`SecretStr` 只能降低意外显示风险，真正的密钥仍必须只放在环境变量中；`src` layout 如何避免导入歧义。
- **与下一步骤的关系：** 配置会为结构化 logging、FastAPI 应用和数据库管理器提供日志等级、应用版本和当前数据库 URL。下一步实现 logging 和 request ID 上下文。

### Step 1.2：实现结构化日志与 request ID 上下文

- **所属 Phase：** Phase 1：项目工程初始化
- **完成日期：** 2026-07-19
- **本步骤目标：** 建立固定 JSON 日志格式，让后续 HTTP 请求、数据库检查和错误都能通过 request ID 关联，同时避免把常见敏感字段写入日志。
- **实际完成内容：** 实现 `JsonFormatter`，固定输出 `timestamp`、`level`、`module`、`message`、`request_id`；使用 `ContextVar` 在异步上下文中保存 request ID；提供设置、读取和恢复上下文的函数；实现 API key、Authorization、password、secret 和 token 形式的基础消息脱敏；`configure_logging()` 只序列化固定字段，不自动输出任意 `extra` 内容。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/logging.py`
  - `tests/unit/platform/test_logging.py`
- **请求或数据流程：**

  request ID 进入当前异步上下文  
  → 应用模块记录日志事件  
  → `JsonFormatter` 获取固定字段  
  → 敏感键值脱敏  
  → 输出单行 JSON  
  → 请求结束后恢复原上下文

- **关键代码入口：** `JsonFormatter.format()`、`configure_logging()`、`set_request_id()`、`get_request_id()`、`reset_request_id()`。
- **使用的核心技术：** Python 标准库 `logging`、`ContextVar`、JSON、正则表达式、pytest。
- **为什么采用当前实现：** 标准库 logging 足以满足 Phase 1，避免额外依赖；固定日志 Schema 比直接序列化整个 `LogRecord` 更安全，也方便后续收集；`ContextVar` 能在并发异步请求之间隔离 request ID。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/platform/test_logging.py -q`；`.venv/bin/ruff check src/enterprise_it_support/platform/logging.py tests/unit/platform/test_logging.py`。
- **测试结果：** 测试先因 logging 模块不存在而红灯；实现后 `2 passed`。Ruff 修正导入顺序后输出 `All checks passed!`。
- **遇到的问题：** Ruff 根据项目导入排序规则，要求 `Token` 与 `ContextVar` 使用不同于手写顺序的排列。
- **解决方法：** 使用 `ruff check --fix` 做机械排序，并重新运行测试确认行为未变化。
- **当前限制：** 当前脱敏只覆盖常见 `key=value` 或 `key:value` 文本形式；代码仍必须遵守“不记录密钥”的原则，不能把脱敏器当成唯一安全措施。HTTP middleware 尚未把 header 中的 request ID 注入上下文。
- **我需要理解的知识：** 为什么 request ID 应使用异步上下文而不是全局变量；结构化日志与普通文本日志的差异；为什么固定 allowlist 字段比记录全部上下文更安全。
- **与下一步骤的关系：** 下一步的 request ID middleware 会调用这些上下文函数，统一错误处理和 `/health`、`/ready` 也会复用相同 request ID。

### Step 1.3：创建 FastAPI 应用、健康检查和统一错误响应

- **所属 Phase：** Phase 1：项目工程初始化
- **完成日期：** 2026-07-19
- **本步骤目标：** 提供可启动的 FastAPI composition root、无需外部依赖的 liveness 检查、统一错误格式，以及贯穿请求和响应的 request ID。
- **实际完成内容：** 实现 `create_app()` factory；创建 `/health`；实现纯 ASGI `RequestIDMiddleware`，接受合法 `X-Request-ID` 或生成 UUID，并回写响应 header；创建稳定的 `ErrorResponse` envelope；统一处理 404、校验错误和未处理异常；通过 HTTP interface 测试健康响应、request ID 和 404 格式。
- **新增或修改文件：**
  - `apps/api/main.py`
  - `src/enterprise_it_support/interaction/schemas.py`
  - `src/enterprise_it_support/interaction/middleware.py`
  - `src/enterprise_it_support/interaction/errors.py`
  - `src/enterprise_it_support/interaction/routes.py`
  - `tests/conftest.py`
  - `tests/integration/api/test_health.py`
  - `pyproject.toml`
- **请求或数据流程：**

  HTTP 请求  
  → 校验或生成 request ID  
  → 写入 ASGI state 和 logging context  
  → FastAPI 路由或异常处理器  
  → 统一 JSON 响应  
  → 将同一 request ID 写入响应 header  
  → 清理上下文

- **关键代码入口：** `apps.api.main.create_app()`、`RequestIDMiddleware.__call__()`、`health()`、`register_exception_handlers()`。
- **使用的核心技术：** FastAPI 0.139、Starlette ASGI middleware、Pydantic response model、HTTPX2 TestClient、pytest。
- **为什么采用当前实现：** factory 方式允许测试显式注入 Settings，模块导入时不会强制读取本地 `.env`；纯 ASGI middleware 避免额外 middleware task 对上下文传播的限制；`/health` 只检查进程本身，数据库状态由独立 `/ready` 负责。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/integration/api/test_health.py -q`；`.venv/bin/ruff check apps/api/main.py src/enterprise_it_support/interaction tests/conftest.py tests/integration/api/test_health.py`。
- **测试结果：** HTTP 测试先因 `apps.api.main` 不存在而红灯；实现后 `3 passed`，Ruff 输出 `All checks passed!`，测试运行不再产生 TestClient 弃用警告。
- **遇到的问题：** 安装到的当前 FastAPI 使用 Starlette 1.3，测试时提示旧 `httpx` 已弃用并建议使用 `httpx2`；新文件也出现四处导入顺序检查错误。
- **解决方法：** 查阅当前 Starlette 官方 TestClient 文档后，把开发依赖从 `httpx` 改为 `httpx2>=2,<3` 并重新安装；使用 Ruff 机械修复导入顺序，再重复测试。
- **当前限制：** `/health` 只证明应用进程可响应；数据库管理器和 `/ready` 尚未实现。统一错误目前只包含安全的通用消息，不返回字段级校验细节。
- **我需要理解的知识：** liveness 与 readiness 的区别；ASGI middleware 如何包裹应用；为什么 request ID 同时放在上下文、request state 和 response header；为什么 app factory 比模块级实例更容易测试。
- **与下一步骤的关系：** 下一步创建 `DatabaseManager`、`/ready`、Alembic 和真实 PostgreSQL 集成测试，并把数据库依赖通过 app factory 注入。

### Step 1.4：接入 PostgreSQL/pgvector、readiness 与 Alembic

- **所属 Phase：** Phase 1：项目工程初始化
- **完成日期：** 2026-07-19
- **本步骤目标：** 用 Docker Compose 提供真实 PostgreSQL/pgvector，建立数据库生命周期和 migration 基础，使 `/ready` 能验证数据库连接与 vector 扩展，而不是只返回固定成功。
- **实际完成内容：** 创建 async `DatabaseManager`、`DatabaseCheckResult` 和最小 `DatabaseLifecycle` interface；readiness 执行 `SELECT 1` 并检查 `pg_extension` 中的 `vector`；FastAPI lifespan 关闭连接池；`/ready` 在可用时返回 200、不可用时通过统一错误 envelope 返回 503；创建 PostgreSQL/pgvector Compose、独立测试数据库初始化脚本、Alembic 环境和首个 vector 扩展 migration；真实启动容器、迁移开发库与测试库，并完成 pgvector 集成测试。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/database.py`
  - `src/enterprise_it_support/interaction/routes.py`
  - `src/enterprise_it_support/interaction/schemas.py`
  - `src/enterprise_it_support/interaction/errors.py`
  - `apps/api/main.py`
  - `compose.yaml`
  - `scripts/postgres/init-test-database.sh`
  - `alembic.ini`
  - `migrations/env.py`
  - `migrations/script.py.mako`
  - `migrations/versions/20260719_0001_enable_pgvector.py`
  - `tests/integration/api/test_ready.py`
  - `tests/integration/platform/test_database.py`
  - `pyproject.toml`
- **请求或数据流程：**

  `GET /ready`  
  → `DatabaseLifecycle.check()`  
  → SQLAlchemy async connection  
  → `SELECT 1`  
  → 检查 `vector` extension  
  → ready 200 或统一 503  
  → FastAPI shutdown 时释放 engine

  `docker compose up -d db`  
  → 初始化开发库与独立测试库  
  → Alembic 连接选定环境数据库  
  → `CREATE EXTENSION IF NOT EXISTS vector`  
  → 数据库通过 readiness

- **关键代码入口：** `DatabaseManager.check()`、`DatabaseManager.close()`、`ready()`、`create_app()` 的 lifespan、migration `upgrade()`、`scripts/postgres/init-test-database.sh`。
- **使用的核心技术：** SQLAlchemy 2 async engine、psycopg 3、PostgreSQL 17、pgvector 0.8.2、Alembic 1.18、Docker Desktop 4.82、Docker Engine 29.6、Docker Compose 5.3。
- **为什么采用当前实现：** `/health` 与 `/ready` 分离，避免数据库故障把进程存活误判为死亡；readiness 同时验证 vector extension，使“数据库能连但 migration 未执行”仍被判为未就绪。开发与测试数据库物理分离，真实集成测试不使用 SQLite。Alembic 使用短生命周期同步 engine，在线应用使用 async engine，分别符合迁移和请求 I/O 的使用方式。
- **运行与验证命令：** `docker compose config --quiet`；`docker compose up -d db`；`docker compose ps`；`.venv/bin/alembic upgrade head`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/alembic current`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic current`；`.venv/bin/python -m pytest -q`；真实请求 `/health` 与 `/ready`。
- **测试结果：** readiness HTTP 测试先因 database 模块不存在而红灯；实现后 HTTP 集成测试 `5 passed`。数据库容器状态为 `healthy`；开发库和测试库 revision 均为 `20260719_0001 (head)`；真实 `/health` 和 `/ready` 最终均返回 200；完整测试达到 `11 passed`。
- **遇到的问题：** async engine 关闭时暴露缺少 `greenlet`；本机最初没有 Docker；Homebrew 内部 API 与 GitHub clone 均受网络阻断；Docker Desktop 首次下载连接重置；安装后缺少 CLI 和 credential-helper 的 PATH 链接；第一次完整 pytest 有 Alembic `path_separator` 警告；按 `os` 分隔修警告后又让 `prepend_sys_path = . src` 变成错误的单一路径，直接 Alembic CLI 无法导入项目包。
- **解决方法：** 把依赖改为 `sqlalchemy[asyncio]`；从可达的 Docker 官方端点续传并校验 DMG，安装启动 Docker Desktop；为已确认不存在的 CLI 路径创建 `docker` 与 `docker-credential-desktop` 符号链接；重试镜像拉取；将 Alembic 路径改为 `path_separator = newline` 和两行路径，并独立复测 CLI，而不只依赖 pytest 的 `pythonpath`。
- **当前限制：** Compose 当前只运行数据库，不容器化 FastAPI，完整应用镜像属于 Phase 12；数据库只有基础 extension，没有任何领域表；本机 Docker Desktop 是为了验收安装的外部开发工具，不属于仓库内容。
- **我需要理解的知识：** liveness 与 readiness；async engine 为什么需要显式生命周期；migration 与 ORM 模型的关系；为什么测试数据库必须独立；Compose healthcheck 与应用 readiness 的差异；为什么集成测试之外还要直接验证命令行入口。
- **与下一步骤的关系：** 数据库、HTTP 和基础设施均已可运行。下一步完成 README、全量静态检查、无警告测试、Git 安全检查和 Phase 1 总结。

### Step 1.5：完善使用文档并完成全量工程验收

- **所属 Phase：** Phase 1：项目工程初始化
- **完成日期：** 2026-07-19
- **本步骤目标：** 把 Phase 1 的安装、启动、迁移、测试和范围边界写成可重复执行的文档，并对 HTTP、数据库、迁移、代码质量与 Git 安全进行最终回归验收。
- **实际完成内容：** 完善 README 的环境要求、项目结构、安装、Compose、开发库与测试库迁移、FastAPI 启动、接口验证、测试、Ruff、配置和当前范围；执行开发数据库与测试数据库 revision 核验；再次执行完整 pytest；检查 Ruff lint、Ruff format、Python 编译、Shell 语法、依赖完整性和 Git whitespace；确认 `.env`、`.DS_Store`、虚拟环境及缓存不会进入 Git；确认源码和依赖中没有实现或引入 Agent、LLM、RAG、工具调用或聊天能力。
- **新增或修改文件：**
  - `README.md`
  - `alembic.ini`
  - `docs/project_journal.md`
- **请求或数据流程：**

  开发者复制 `.env.example` 为本地 `.env`  
  → Compose 启动 PostgreSQL/pgvector  
  → Alembic 分别迁移开发库与测试库  
  → Uvicorn 通过 app factory 启动 FastAPI  
  → `/health` 验证进程、`/ready` 验证数据库和 vector  
  → pytest 与 Ruff 验证行为和代码质量

- **关键代码入口：** `README.md` 中的运行手册；`apps.api.main.create_app()`；`migrations/env.py`；`pyproject.toml` 的 pytest 与 Ruff 配置。
- **使用的核心技术：** Markdown、Docker Compose、Alembic CLI、pytest、Ruff、Python `compileall`、`bash -n`、`pip check`、Git whitespace 检查。
- **为什么采用当前实现：** README 使用与真实验收一致的命令，避免“文档上可运行、实际不可运行”；验收同时覆盖进程、HTTP、数据库、migration 和静态质量，避免只依赖单一测试信号；使用显式 `PYTHONPATH=.:src` 启动，兼容当前 Python 3.14 对 editable-install `.pth` 的安全跳过行为，同时仍保留标准 `src` layout。
- **运行与验证命令：** `docker compose config --quiet`；`docker compose ps`；`.venv/bin/alembic current`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic current`；`.venv/bin/pytest -q`；`.venv/bin/ruff format --check .`；`.venv/bin/ruff check .`；`.venv/bin/python -m compileall -q apps src migrations`；`bash -n scripts/postgres/init-test-database.sh`；`.venv/bin/pip check`；`git diff --check`。
- **测试结果：** PostgreSQL 容器为 `healthy`；开发库与测试库均为 `20260719_0001 (head)`；pytest 输出 `11 passed in 0.27s` 且无 warning；Ruff 显示 `34 files already formatted` 和 `All checks passed!`；Python 编译、Shell 语法、依赖检查与 Git whitespace 检查均通过。
- **遇到的问题：** 最终验收脚本第一次误用了未定义的 `APP_ENV=test`，该变量不会被带有 `IT_SUPPORT_` 前缀的 Pydantic Settings 读取，因此当次命令实际检查的是默认开发数据库；Python 3.14.5 还会跳过 setuptools 生成的隐藏 editable `.pth` 文件，使只依赖 editable install 的 Uvicorn 命令无法找到工作区模块。
- **解决方法：** 立即使用正确的 `IT_SUPPORT_ENVIRONMENT=test` 独立重跑 test migration、`current` 和真实数据库测试，确认测试库确实位于 head；README 的 Uvicorn 命令显式设置 `PYTHONPATH=.:src`，并实际启动后请求 `/health` 与 `/ready` 验证。
- **当前限制：** FastAPI 尚未制作应用镜像，Compose 只管理数据库；没有领域表、身份认证、业务接口或前端；结构化日志目前输出到标准输出，没有接入集中日志系统；CI 尚未建立。以上均属于后续 Phase，Phase 1 不提前实现。
- **我需要理解的知识：** 环境变量前缀必须与 Settings 定义完全匹配；测试通过不等于命令行入口可用，migration 和 Uvicorn 需要单独 smoke test；`/health`、`/ready`、Compose healthcheck 分别回答不同层次的可用性问题；静态检查、单元测试和真实基础设施集成测试不能互相替代。
- **与下一步骤的关系：** Phase 1 提供了后续所有 Phase 共用的配置、HTTP、数据库、migration、测试和质量基线。Phase 2 应只在此基础上增加核心数据模型与迁移，不修改 Phase 1 的职责边界。

## Phase 1 总结与索引

Phase 1 已把 Phase 0 的模块化单体设计落成可运行、可迁移、可测试的工程骨架。当前系统能够启动 FastAPI，提供统一 request ID 与错误 envelope，通过真实 PostgreSQL/pgvector 进行 readiness 检查，并使用 Alembic 管理数据库扩展。预留领域包只有边界说明，没有 Agent、LLM、RAG、工具或聊天业务实现。

### 步骤索引

| 步骤 | 主题 | 主要产物 |
| --- | --- | --- |
| Step 1.1 | 目录、依赖与环境配置 | `pyproject.toml`、`.env.example`、`platform/config.py` |
| Step 1.2 | 结构化日志 | `platform/logging.py`、logging 单元测试 |
| Step 1.3 | FastAPI 与 HTTP 基线 | app factory、request ID、统一错误、`/health` |
| Step 1.4 | PostgreSQL/pgvector 基线 | Compose、DatabaseManager、`/ready`、Alembic |
| Step 1.5 | 文档与全量验收 | `README.md`、最终测试和静态检查结果 |

### Phase 1 验收状态

- `docker compose up -d db` 可启动 PostgreSQL/pgvector：通过；
- FastAPI app factory 可正常启动：通过；
- `/health` 返回 200：通过；
- `/ready` 真实验证数据库和 vector 扩展并返回 200：通过；
- Alembic 可迁移开发库与独立测试库：通过；
- pytest 全部通过：`11 passed`；
- Ruff lint 与 format check：通过；
- `.env` 与敏感配置不进入 Git：通过；
- 未实现 Agent、LLM、RAG、工具调用和聊天功能：通过。

### 下一 Phase 入口

Phase 2 开始前先阅读本总结和 Step 1.5。下一阶段应建立核心业务数据模型与迁移，并继续采用独立测试数据库、Alembic、类型标注和测试先行；不得提前实现知识库导入、RAG 或 Agent。

---

## Phase 1 收尾验收补充记录

### Step 1.6：执行双轴代码审查并修复 500 request ID 丢失

- **所属 Phase：** Phase 1：项目工程初始化（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 不以“测试能跑”为默认通过条件，分别检查工程规范和 Phase 1 规格，并修复未处理异常无法完整关联 request ID 的 Blocking 问题。
- **实际完成内容：** 在仓库没有 HEAD、全部文件尚未跟踪的前提下，以当前工作区作为审查对象；分别完成 Standards 与 Spec 审查；确认没有提前实现 Agent、RAG、LLM 或工具能力，也没有需要删除的过度设计；新增真实 HTTP 500 测试，证明旧实现的响应缺少 `X-Request-ID`；修改统一错误响应，使外层 ServerErrorMiddleware 生成的 500 也携带 request ID；在未处理异常日志前临时恢复 request ID 上下文，使日志和响应可关联。
- **新增或修改文件：**
  - `tests/integration/api/test_health.py`
  - `src/enterprise_it_support/interaction/errors.py`
  - `docs/project_journal.md`
- **请求或数据流程：**

  带 `X-Request-ID` 的请求  
  → `RequestIDMiddleware` 保存 ID  
  → 路由抛出未处理异常  
  → middleware 清理自身上下文并向外抛出  
  → FastAPI/Starlette 外层 500 handler 从 `request.state` 读取 ID  
  → 临时绑定日志 ContextVar  
  → 输出带 request ID 的结构化日志和统一 500 响应

- **关键代码入口：** `unhandled_exception_handler()`、`_error_response()`、`test_unhandled_errors_keep_request_id_in_response_and_log()`。
- **使用的核心技术：** FastAPI/Starlette 异常层级、纯 ASGI middleware、`ContextVar`、HTTP 集成测试、双轴代码审查。
- **为什么采用当前实现：** FastAPI 的外层 ServerErrorMiddleware 会在用户 middleware 之外处理未捕获异常，不能假设普通 response wrapper 一定能看到 500 response；统一错误构造器直接写入 header，并在 handler 内短暂恢复 logging context，是不改变应用结构的最小修复。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/api/test_health.py::test_unhandled_errors_keep_request_id_in_response_and_log -q`。
- **测试结果：** 新测试先以 `KeyError: 'x-request-id'` 红灯失败；最小修复后 `1 passed`，并验证日志 `request_id=request-500`。
- **遇到的问题：** 原有 404 和 readiness 503 都在内部 ExceptionMiddleware 中转换，掩盖了未捕获 500 经过不同异常边界的事实。
- **解决方法：** 使用 `raise_server_exceptions=False` 从真实 HTTP seam 触发未处理异常，同时断言 body、header 和结构化日志，而不是只直接调用 exception handler。
- **当前限制：** 500 日志只记录安全的异常类型，不记录堆栈；这是 Phase 1 的安全取舍，后续可观察性设计再决定受控堆栈记录策略。
- **我需要理解的知识：** Starlette 的 ServerErrorMiddleware、用户 middleware 和 ExceptionMiddleware 的顺序；为什么 request state 与 ContextVar 承担不同角色；为什么 404 测试不能证明 500 路径正确。
- **与下一步骤的关系：** request ID 已能覆盖正常、受控错误和未处理错误。下一步修复日志脱敏、测试数据库隔离和本地数据库网络暴露。

### Step 1.7：收紧日志、测试数据库与本地端口安全边界

- **所属 Phase：** Phase 1：项目工程初始化（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 修复审查发现的敏感日志泄漏风险，并把“测试库隔离”和“仅本机数据库”从文档约定变为可验证约束。
- **实际完成内容：** 为日志新增 Bearer/Basic Authorization、带引号 JSON 敏感字段和 URL 凭证脱敏；新增测试环境不得复用开发数据库 URL 的 Settings 校验；把 Compose PostgreSQL 端口从所有网卡改为只绑定 `127.0.0.1`；同步 README 的安全与测试说明。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/logging.py`
  - `src/enterprise_it_support/platform/config.py`
  - `tests/unit/platform/test_logging.py`
  - `tests/unit/platform/test_config.py`
  - `compose.yaml`
  - `README.md`
- **请求或数据流程：**

  日志消息  
  → URL credential 脱敏  
  → Authorization credential 脱敏  
  → 通用敏感键脱敏  
  → 固定 JSON Schema 输出

  test 环境配置  
  → 检查 test URL 存在  
  → 检查 test URL 与 development URL 不同  
  → 允许创建 Settings 或返回清晰校验错误

- **关键代码入口：** `_redact()`、`Settings.require_isolated_test_database()`、`compose.yaml` 的 `ports`。
- **使用的核心技术：** 正则表达式、Pydantic model validator、`SecretStr`、Docker Compose loopback port binding、pytest。
- **为什么采用当前实现：** 只记录固定字段仍不能阻止开发者把凭证拼进 message，因此需要覆盖常见文本格式；测试库隔离属于防止误删开发数据的安全边界，不能只依赖 README；本地开发数据库没有局域网访问需求，应遵守最小暴露原则。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/platform/test_logging.py -q`；`.venv/bin/pytest tests/unit/platform/test_config.py -q`；`docker compose up -d --force-recreate db`；`docker compose port db 5432`。
- **测试结果：** 新日志测试先暴露 `bearer-secret` 未被隐藏，修复后 logging `3 passed`；相同 URL 测试先因未抛错失败，修复后 config `4 passed`；重建容器后端口为 `127.0.0.1:5432`。
- **遇到的问题：** 原正则只消费 Authorization 后的第一个单词，因此把 `Bearer` 替换后仍留下真实 token；JSON 键名的引号和 DSN 中的密码也不符合旧模式。
- **解决方法：** 按 URL、Authorization、通用敏感键三个明确模式顺序脱敏，并用独立已知秘密字符串断言输出中完全不存在原值。
- **当前限制：** 文本脱敏不可能覆盖任意自定义编码或混淆形式，首要规则仍是调用代码不得主动记录密钥；URL 隔离校验阻止完全相同 URL，不负责识别所有语义等价的代理或别名地址。
- **我需要理解的知识：** 防御纵深；为什么脱敏不能替代“不记录”；loopback 与 `0.0.0.0` 的网络暴露差异；Pydantic 模型级校验适合表达跨字段约束。
- **与下一步骤的关系：** 基础安全边界已收紧。下一步补足真实数据库和统一错误处理失败路径，并修正文档中的 Phase 边界偏差。

### Step 1.8：补齐关键失败路径并校准 Phase 文档

- **所属 Phase：** Phase 1：项目工程初始化（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 用真实 seam 证明数据库失败与统一错误行为，并使 Backlog、README 与用户后来明确下达的 Phase 1 原始任务保持一致。
- **实际完成内容：** 新增 422 HTTP 错误集成测试；新增真实不可达 PostgreSQL 连接测试；在独立测试库执行 Alembic downgrade，验证缺少 vector extension 时 readiness 失败，并在 `finally` 中恢复 head；删除 `SELECT 1` 后理论上不可达的 `unexpected_response` 分支；更新 Backlog，把用户明确要求的 PostgreSQL/pgvector、Alembic 和 `/ready` 纳入 Phase 1，并将 Phase 2 调整为在现有数据库基础上建立核心领域模型和持久化规范；明确原任务要求基础类型标注和 Ruff，而未要求独立 mypy/Pyright 门禁。
- **新增或修改文件：**
  - `tests/integration/api/test_health.py`
  - `tests/integration/platform/test_database.py`
  - `src/enterprise_it_support/platform/database.py`
  - `docs/backlog.md`
  - `README.md`
- **请求或数据流程：**

  真实测试数据库  
  → Alembic downgrade 到 base  
  → `DatabaseManager.check()` 连接成功但找不到 vector  
  → 返回 `vector_extension_missing`  
  → `finally` 中 upgrade 到 head

  不可达 PostgreSQL URL  
  → SQLAlchemy/psycopg 连接失败  
  → 捕获 SQLAlchemyError  
  → 返回 `connection_failed`，不泄漏 URL

- **关键代码入口：** `DatabaseManager.check()`、`test_database_reports_connection_failure()`、`test_database_reports_missing_vector_extension()`、`validation_exception_handler()`。
- **使用的核心技术：** 真实 PostgreSQL 测试、Alembic upgrade/downgrade、SQLAlchemy async engine、FastAPI validation、文档契约校准。
- **为什么采用当前实现：** 数据库是明确的系统边界，应优先使用隔离的真实测试库而不是模拟 SQL；不可达连接使用固定本机关闭端口，不依赖外部网络；Backlog 的旧顺序是 Phase 0 设计，后来用户的明确 Phase 1 指令具有更高优先级，因此记录并修正文档，而不额外引入原任务未要求的类型检查工具。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/api/test_health.py::test_validation_errors_use_unified_response -q`；`.venv/bin/pytest tests/integration/platform/test_database.py -q`；`.venv/bin/pytest -q`；`.venv/bin/ruff format .`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`.venv/bin/python -m compileall -q apps src migrations`；`bash -n scripts/postgres/init-test-database.sh`；`.venv/bin/pip check`。
- **测试结果：** 422 测试 `1 passed`；数据库成功、连接失败、vector 缺失三条真实路径 `3 passed`；全量达到 `17 passed`；Ruff 首次 format check 发现 5 个新修改文件需格式化，运行机械格式化后 lint 与 format check 全部通过；编译、Shell 语法和依赖检查通过。
- **遇到的问题：** Phase 0 Backlog 把数据库基础放在 Phase 2，但用户随后在 Phase 1 原始任务中明确要求 PostgreSQL、pgvector、Alembic 和 `/ready`；直接把旧 Backlog 当成最终契约会造成文档与仓库状态冲突。
- **解决方法：** 保留历史日志不覆盖，在当前 Backlog 和本补充记录中明确变更来源与原因；Phase 2 只保留尚未实现的领域模型、事务和 Repository 工作。
- **当前限制：** 本阶段没有独立 mypy/Pyright 门禁；这与最新 Phase 1 原始任务一致，但未来若把静态类型检查设为正式质量门禁，需要独立 Phase 指令或 ADR。测试会短暂 downgrade 独立 test 数据库，因此不应对开发库执行该测试配置。
- **我需要理解的知识：** 真实边界测试与 fake adapter HTTP 测试解决的问题不同；为什么 migration 测试必须恢复数据库；需求变更后为什么要更新当前设计并保留历史日志；基础类型标注、Python 编译检查与静态类型检查器不是同一件事。
- **与下一步骤的关系：** Blocking 与必要 Important 工程问题已经修复。下一步只执行最终全量回归、一个正常和两个失败的实际演示，并给出 Phase 1 最终判定。

### Step 1.9：执行真实演示并完成 Phase 1 最终验收

- **所属 Phase：** Phase 1：项目工程初始化（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 在完成修复后重新运行全部质量门禁，并通过实际启动的 FastAPI 与真实 PostgreSQL 验证至少一个正常场景和两个失败场景。
- **实际完成内容：** 使用修复后的 Compose 重建 PostgreSQL/pgvector；迁移开发库与测试库；运行 17 项完整测试、Ruff lint/format、Python 编译、Shell 语法和依赖检查；实际启动 Uvicorn；验证健康与就绪正常响应；验证不存在路由的统一 404；真实停止数据库后验证 `/health` 仍为 200、`/ready` 为统一 503，并读取服务端结构化 warning 日志确认 request ID 可追踪；最后正常关闭 FastAPI，数据库保持停止且数据卷保留。
- **新增或修改文件：**
  - `README.md`
  - `docs/project_journal.md`
- **请求或数据流程：**

  正常场景：请求  
  → request ID middleware  
  → `/ready`  
  → SQLAlchemy 连接 PostgreSQL  
  → `SELECT 1` 与 vector extension 检查  
  → HTTP 200 + 同一 request ID

  数据库失败场景：停止 PostgreSQL  
  → `/health` 不访问外部依赖并返回 200  
  → `/ready` 连接失败  
  → 安全 warning 日志  
  → 统一 HTTP 503 + 同一 request ID

- **关键代码入口：** `create_app()`、`health()`、`ready()`、`DatabaseManager.check()`、`RequestIDMiddleware.__call__()`。
- **使用的核心技术：** Docker Compose、PostgreSQL/pgvector、Alembic、Uvicorn、curl、pytest、Ruff、结构化日志。
- **为什么采用当前实现：** 单元测试无法证明容器端口、migration、实际服务器和真实数据库的组合行为；正常与失败演示同时验证 liveness/readiness 分离、错误 envelope、request ID 和日志关联，是 Phase 1 最小但完整的运行证据。
- **运行与验证命令：** `docker compose up -d --force-recreate db`；`docker compose port db 5432`；`.venv/bin/alembic upgrade head`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`env PYTHONPATH=.:src .venv/bin/uvicorn apps.api.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log`；使用带固定 `X-Request-ID` 的 curl 请求 `/health`、`/ready` 和 `/does-not-exist`；`docker compose stop db`；再次请求 `/health` 与 `/ready`。
- **测试结果：** 全量 `17 passed in 0.31s`；Ruff `All checks passed!` 且 `34 files already formatted`；正常 `/health` 和 `/ready` 均为 200；失败场景一为统一 404；停止数据库后 `/health` 仍为 200，`/ready` 为统一 503；数据库 warning 日志的 `request_id` 为 `demo-ready-db-down`；容器端口为 `127.0.0.1:5432`。
- **遇到的问题：** 收尾修改后的第一次 Ruff format check 报告 5 个文件需要格式化；数据库停止演示必须确保应用继续运行，才能区分进程存活与依赖就绪。
- **解决方法：** 仅使用 Ruff 做机械格式化，再重复 lint、format、编译和完整测试；演示时先启动应用和数据库验证正常场景，再只停止数据库并分别请求两个操作接口，最后正常关闭 Uvicorn。
- **当前限制：** 仓库尚无 HEAD 提交，所有项目文件仍未跟踪，因此无法生成标准 merge-base diff；本轮按当前工作区完整审查。数据库容器当前停止，运行项目前需执行 `docker compose up -d db`。没有独立 mypy/Pyright 门禁，且没有应用 Docker image、CI 或后续业务能力。
- **我需要理解的知识：** 为什么实际 smoke test 不能被 pytest 完全替代；正常和失败场景如何形成可审计证据；数据库停止时 health 仍成功为什么是正确行为；如何从 request ID 关联 HTTP 响应和结构化日志。
- **与下一步骤的关系：** Phase 1 工程验收结论为 PASS，可以在用户明确指令后进入下一阶段；本次任务到此停止，不自动开始 Phase 2。

## Phase 1 最终收尾结论

- **工程状态：** PASS；
- **Blocking：** 1 项，已修复并增加回归测试；
- **Important：** 日志脱敏、测试库隔离、数据库失败测试、422/500 错误测试、本地端口暴露和文档边界偏差均已修复；
- **Optional：** readiness checks 强类型化、测试常量去重、Alembic dispose 风格等保持不变，未在收尾阶段扩展；
- **测试：** 17 passed；
- **代码质量：** Ruff lint 与 format check 通过；
- **实际演示：** 1 个正常路径、2 个失败路径通过；
- **建议 Commit：** `chore(phase-1): finalize foundation and acceptance checks`；
- **建议 Tag：** `phase-1-complete`。

---

## Phase 2：知识库数据模型与文档解析

### Step 2.1：建立知识领域语言并实现 TXT 标准化解析

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 明确逻辑文档、不可变版本和 Chunk 的领域边界，并建立第一个从原始 TXT 到统一 `DocumentContent` 的可测试解析 seam。
- **实际完成内容：** 创建根级领域词汇表，定义 Knowledge Source、Document、Document Version、Document Chunk、Document Content 和 Duplicate Import；创建 `DocumentSourceType`、`SourceLocation`、`DocumentSection` 和 `DocumentContent`；实现 TXT UTF-8 解码、换行规范化、按空行识别段落、标题提取和起止行记录；新增虚构 Outlook 排查文档与 TXT parser 测试。
- **新增或修改文件：**
  - `CONTEXT.md`
  - `src/enterprise_it_support/knowledge/domain.py`
  - `src/enterprise_it_support/knowledge/parsers.py`
  - `tests/unit/knowledge/test_parsers.py`
  - `tests/unit/knowledge/__init__.py`
  - `tests/fixtures/knowledge/outlook_mail_troubleshooting.txt`
  - `tests/fixtures/knowledge/vpn_configuration_sop.md`
  - `docs/project_journal.md`
- **请求或数据流程：** TXT bytes → UTF-8 解码 → 规范化换行 → 按空行形成段落 → 记录 start/end line → 生成统一 `DocumentContent`。
- **关键代码入口：** `DocumentParserRegistry.parse()`、`DocumentContent.canonical_text`、`_paragraph_sections()`。
- **使用的核心技术：** Python dataclass、`StrEnum`、UTF-8、路径后缀分派、pytest、领域通用语言。
- **为什么采用当前实现：** Document 是跨上传保持稳定的逻辑身份，Version 才代表内容快照；统一 parser 输出让 Chunking 和持久化不依赖文件格式；TXT 用空行划分段落简单、确定且能保留来源行号。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/knowledge/test_parsers.py::test_txt_parser_returns_normalized_sections_with_line_positions -q`。
- **测试结果：** 首次因 `enterprise_it_support.knowledge.domain` 不存在而 collection 红灯；实现后 `1 passed`。
- **遇到的问题：** 用户使用“文档”和“文件”描述上传对象，若不先区分，会导致重复导入时无法判断应创建新 Document 还是新 Version。
- **解决方法：** 使用领域词汇表固定术语：File 是输入载体，Document 是逻辑身份，Document Version 是不可变内容，Document Chunk 属于具体 Version。
- **当前限制：** 当前 registry 只实现 TXT；Markdown、PDF、Chunking 和数据库均未实现。TXT 只支持 UTF-8，不自动猜测遗留编码。
- **我需要理解的知识：** 为什么一个 Document 需要多个 Version；为什么 Chunk 不能直接属于 Document；标准化 parser 输出如何隔离文件格式差异。
- **与下一步骤的关系：** Markdown 和 PDF parser 将复用相同 `DocumentContent` seam；Chunking 只消费该结构，不关心原始文件类型。

### Step 1.10：统一 Uvicorn 日志并消除 access log 回归

- **所属 Phase：** Phase 1：项目工程初始化（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 修复实际演示发现的 Uvicorn 运行日志仍为默认文本的问题，同时确保结构化配置不绕过命令行的 `--no-access-log` 设置。
- **实际完成内容：** 新增 Uvicorn error logger 公共输出测试；让 `uvicorn` 与 `uvicorn.error` 移除默认 handler 并传播到应用 JSON root handler；实际启动后确认启动和关闭日志包含固定五字段；发现第一版修复会把已禁用的 access logger 重新启用，新增回归测试后改为只有 access logger 原本存在 handler 时才将其结构化；最终确认 `--no-access-log` 下请求不会生成访问日志。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/logging.py`
  - `tests/unit/platform/test_logging.py`
  - `README.md`
  - `docs/project_journal.md`
- **请求或数据流程：**

  Uvicorn 启动/关闭事件  
  → `uvicorn.error` logger  
  → 传播到 root logger  
  → `JsonFormatter`  
  → timestamp、level、module、message、request_id

  `--no-access-log`  
  → Uvicorn 移除 access handler  
  → 应用 logging 配置检测到 handler 不存在  
  → 保持 `propagate=False`  
  → HTTP 请求不产生日志

- **关键代码入口：** `configure_logging()`、`test_configure_logging_routes_uvicorn_logs_to_json()`、`test_configure_logging_keeps_disabled_uvicorn_access_log_disabled()`。
- **使用的核心技术：** Python logging hierarchy、logger handler/propagate、Uvicorn logging、pytest capture、真实 Uvicorn smoke test。
- **为什么采用当前实现：** 只配置 root logger 不能覆盖 `propagate=False` 且拥有自己 handler 的 Uvicorn logger；同时不能无条件修改 access logger，因为 handler 是否存在表达了用户是否启用访问日志。按当前 logger 状态做最小适配，可以同时满足结构化和命令行开关语义。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/platform/test_logging.py::test_configure_logging_routes_uvicorn_logs_to_json -q`；`.venv/bin/pytest tests/unit/platform/test_logging.py::test_configure_logging_keeps_disabled_uvicorn_access_log_disabled -q`；`.venv/bin/pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；实际启动 Uvicorn 并请求 `/health`；轮询服务输出确认没有 access log。
- **测试结果：** Uvicorn JSON 测试先因 capture 为空而红灯，修复后通过；access log 测试先捕获到不应出现的 JSON 记录而红灯，回归修复后 logging `5 passed`；最终全量 `19 passed in 0.32s`；Ruff `All checks passed!` 且 `34 files already formatted`；实际启动与关闭日志均为 JSON，请求 `/health` 后没有 access log 输出。
- **遇到的问题：** 第一版为了统一所有 Uvicorn logger，错误地无条件设置 `uvicorn.access.propagate=True`，覆盖了 `--no-access-log` 的效果。
- **解决方法：** 把 error logger 与 access logger 分开处理；error logger 始终结构化，access logger 仅在 Uvicorn 已为其配置 handler 时才改为传播，从而保留禁用状态。
- **当前限制：** 当启用 access log 时，请求行会进入结构化 message；生产环境仍需根据隐私策略决定是否记录查询路径。启动/关闭日志没有请求上下文，因此 `request_id=null` 是正确结果。
- **我需要理解的知识：** logger 名称层级、handler 与 propagate 如何共同决定输出；为什么 `request_id=null` 对非请求事件是合理的；为什么真实 smoke test 能发现单元测试未覆盖的第三方 logger 配置。
- **与下一步骤的关系：** Phase 1 所有已知 Blocking 和必要 Important 问题均已修复。最终工程结论仍为 PASS，最新测试数字以本步骤和下方补充结论为准。

## Phase 1 最终收尾结论补充

Step 1.9 的 `17 passed` 是当时的真实结果；在补齐 Uvicorn logging 与 access-log 回归测试后，最终结果更新为：

- **工程状态：** PASS；
- **最终测试：** 19 passed；
- **最终代码质量：** Ruff lint、Ruff format、Python compileall、Shell 语法和依赖检查全部通过；
- **最终运行验证：** Uvicorn 日志为 JSON，`--no-access-log` 保持有效；正常 200、统一 404、数据库故障 503 场景通过；
- **运行状态：** FastAPI 和 Compose 容器已停止，PostgreSQL 命名数据卷保留；
- **建议 Commit：** `chore(phase-1): finalize foundation and acceptance checks`；
- **建议 Tag：** `phase-1-complete`。

---

## Phase 2 当前续写入口

Step 2.1 的完整记录已写入本文件，但因追加补丁使用了重复的 Phase 1 Tag 作为定位点，被插入到后来追加的 Step 1.10 之前。为遵守“不删除或重写历史记录”，保留原记录并在文件末尾增加本说明；从此处继续追加 Phase 2 后续步骤。当前已完成 Step 2.1：知识领域语言与 TXT 标准化解析。

### Step 2.2：完成 Markdown/PDF 解析与虚构样例文档

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 让 Markdown、TXT、PDF 三种输入都通过同一个 parser registry 输出可追溯的 `DocumentContent`，并提供可重复生成、视觉可验证的虚构 PDF 样例。
- **实际完成内容：** 实现 Markdown heading 分段、代码围栏保护、标题和行号保留；实现基于 pypdf 的 PDF 页级提取、加密 PDF 拒绝、空文本拒绝、metadata 标题和页码保留；扩展 canonical text 包含 section title；新增 pypdf、python-multipart 和 reportlab 依赖；创建可重复生成的两页账号 FAQ PDF 脚本与 fixture；使用 pdfinfo 检查文件结构，渲染两页 PNG 并人工检查版式；完成 TXT、Markdown、PDF 三个 parser 行为测试。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/domain.py`
  - `src/enterprise_it_support/knowledge/parsers.py`
  - `tests/unit/knowledge/test_parsers.py`
  - `tests/fixtures/knowledge/account_common_questions_faq.pdf`
  - `scripts/generate_sample_pdf.py`
  - `pyproject.toml`
  - `docs/project_journal.md`
- **请求或数据流程：** 文件名与 bytes → registry 按后缀选择 parser → Markdown 行/heading、TXT 段落或 PDF page 提取 → 标准化文本与来源位置 → `DocumentContent`。
- **关键代码入口：** `DocumentParserRegistry.parse()`、`_parse_markdown()`、`_parse_pdf()`、`generate_pdf()`。
- **使用的核心技术：** pypdf、reportlab、PDF metadata、Poppler pdfinfo/pdftoppm、Markdown heading 正则、pytest。
- **为什么采用当前实现：** Markdown 以 heading 作为天然章节边界；PDF 文本布局难以稳定还原标题层级，因此 MVP 使用可靠的页级位置；reportlab 脚本使二进制 fixture 可重新生成并确认完全虚构。
- **运行与验证命令：** `.venv/bin/python -m pip install -e '.[dev]'`；`.venv/bin/python scripts/generate_sample_pdf.py`；`pdfinfo tests/fixtures/knowledge/account_common_questions_faq.pdf`；`pdftoppm -png -r 120 ... tmp/pdfs/account_faq`；视觉检查两页 PNG；`.venv/bin/pytest tests/unit/knowledge/test_parsers.py -q`。
- **测试结果：** Markdown 测试先因 `.md` 不受支持失败，修复后又发现尾部空行将 end line 错记为 18，修正后通过；PDF 测试先因 `.pdf` 不受支持失败，实现后通过；最终 `3 passed`。PDF 为 2 页、Letter 页面、未加密，视觉检查无裁切、重叠或不可读内容。
- **遇到的问题：** Poppler 渲染输出大量 fontconfig cache 不可写 warning，但仍成功生成两页 PNG；一次补丁定位把 `_parse_markdown()` 错误缩进到 `_normalize_pdf_text()` 之后。
- **解决方法：** 以生成文件、pdfinfo 和实际 PNG 为准确认 warning 不影响结果；立即检查带行号源码并恢复方法到 registry 类，再运行全部 parser 测试。
- **当前限制：** PDF 只处理可提取文本的非加密 PDF，不进行 OCR；Markdown 不是完整 CommonMark AST parser，MVP 只识别非代码围栏内的 ATX headings；文本只支持 UTF-8。
- **我需要理解的知识：** 为什么 parser 输出必须与格式无关；PDF 页码与 Markdown 行号的追溯粒度为何不同；文本提取成功不等于 PDF 视觉布局正确。
- **与下一步骤的关系：** Chunking 将只消费 `DocumentContent.sections`，利用 section title、line/page location 生成可追溯 Chunk，不依赖具体 parser。

### Step 2.3：实现可配置、可追溯的边界感知 Chunking

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 把标准化章节切成有大小上限、可重叠且保留来源位置的 Chunk，同时避免空 Chunk 和极短无意义内容。
- **实际完成内容：** 创建 `DocumentChunkDraft` 和 `DocumentChunker`；实现 `chunk_size >= 2`、`0 <= overlap < size` 参数校验；使用确定性正则估算英文词、中文字符和标点 token；长章节按 token window 切分并重叠；在窗口内优先选择段落结束；每个 Chunk 保存 source type、原文件名、section index、行或页位置及 token start/end；过滤少于两个 token 或不含字母数字的内容；保持全局连续 chunk index。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/chunking.py`
  - `tests/unit/knowledge/test_chunking.py`
  - `docs/project_journal.md`
- **请求或数据流程：** `DocumentContent.sections` → 确定性 token spans → 选择不超过 size 的段落边界 → 应用 overlap → 过滤无意义文本 → 生成带位置 metadata 的有序 Chunk drafts。
- **关键代码入口：** `DocumentChunker.split()`、`DocumentChunker._split_section()`、`DocumentChunkDraft`。
- **使用的核心技术：** 正则 token spans、字符 offset、段落边界、dataclass、pytest。
- **为什么采用当前实现：** 本阶段禁止 LLM/Embedding，不能绑定某个模型 tokenizer；确定性估算便于复现和面试解释。按 section 独立切分可以保留标题，段落边界优先于机械固定窗口，但超长内容仍有明确上限。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/knowledge/test_chunking.py -q`。
- **测试结果：** 首个测试先因 chunking 模块不存在 collection 红灯，实现后通过；段落边界、overlap、连续 index、来源位置和无意义文本过滤测试最终 `2 passed`。
- **遇到的问题：** overlap 会让新 Chunk 从上一 Chunk 的段落尾部开始，因此不能简单假设每个 Chunk 都从新段落开头；段落边界与严格 size 可能冲突。
- **解决方法：** 结束位置优先选择当前 window 后半段内最近的段落边界；下一窗口再按 token overlap 回退，保证 size、覆盖和上下文连续性三者的确定规则。
- **当前限制：** token_count 是模型无关估算值，不等同于未来某个 Embedding 模型的精确 token 数；PDF 只能追溯到页，不能追溯页面坐标；极短但业务上重要的单词会被过滤。
- **我需要理解的知识：** Chunk size 与 overlap 的权衡；为什么 source location 和数据库外键共同构成追溯链；为什么确定性 token 估算适合导入基线但未来需要版本化。
- **与下一步骤的关系：** 下一步把 Chunk draft 写入 `document_chunks`，并通过 `document_version_id` 连接到不可变版本和逻辑文档。

### Step 2.4：创建知识库实体与 Alembic migration

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 用 PostgreSQL schema 表达 Knowledge Source、Document、不可变 Version 和可追溯 Chunk 的关系与约束。
- **实际完成内容：** 创建四个 SQLAlchemy 2 typed models；使用 UUID 主键、timezone-aware 时间、外键和 cascade；Document 包含 title、source type、status、owner；Version 包含递增版本号、SHA-256、有效期和原文件路径；Chunk 包含顺序、内容、token count、section title 和 JSONB metadata；增加 source/title、document/version、document/hash、version/chunk index 唯一约束及状态、类型、正数和日期检查；创建 `20260719_0002` migration；让 Alembic metadata 显式加载 Knowledge models；在真实测试库检查四表全部必需列。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/domain.py`
  - `src/enterprise_it_support/knowledge/models.py`
  - `migrations/env.py`
  - `migrations/versions/20260719_0002_create_knowledge_tables.py`
  - `tests/integration/knowledge/test_migrations.py`
  - `tests/integration/knowledge/__init__.py`
  - `docs/project_journal.md`
- **请求或数据流程：** Alembic 读取 Settings → 加载 Base metadata 与 Knowledge models → 创建 Source → Document → Version → Chunk → inspector 从真实 PostgreSQL 验证列集合。
- **关键代码入口：** `KnowledgeSource`、`Document`、`DocumentVersion`、`DocumentChunk`、migration `upgrade()`/`downgrade()`。
- **使用的核心技术：** SQLAlchemy 2 typed ORM、PostgreSQL UUID/JSONB、Alembic、外键、unique/check constraints、真实数据库 schema inspection。
- **为什么采用当前实现：** 逻辑 Document 与不可变 Version 分离才能保留历史；Chunk 外键指向 Version 才能保证引用可复现；关键业务不变量同时放在应用和数据库约束中，防止绕过 Service 写入无效状态。
- **运行与验证命令：** `docker compose up -d db`；`.venv/bin/pytest tests/integration/knowledge/test_migrations.py -q`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic current`。
- **测试结果：** migration 测试先以 `NoSuchTableError: knowledge_sources` 红灯；实现并升级后 `1 passed`，测试库为 `20260719_0002 (head)`。
- **遇到的问题：** `metadata` 是 SQLAlchemy DeclarativeBase 的保留属性名，不能直接作为 ORM Python 属性；Alembic 只导入 Base 时不会自动发现尚未加载的业务 models。
- **解决方法：** 数据库列仍命名 `metadata`，ORM 使用 `metadata_ = mapped_column("metadata", JSONB)`；migration env 显式导入 Knowledge models 以注册 metadata。
- **当前限制：** 当前表没有 Embedding/vector 列，符合本阶段边界；没有删除 API；source/title 的唯一性是大小写敏感的精确匹配；尚未通过 Repository 写入业务数据。
- **我需要理解的知识：** ORM relationship 与数据库 foreign key 的区别；为什么唯一约束要覆盖 version/hash/chunk index；JSONB metadata 如何补充而不替代强类型列。
- **与下一步骤的关系：** Repository 和 ingestion service 将在同一事务中创建 Source、Document、Version 和 Chunks，并依赖这些约束处理并发和重复内容。

### Step 2.5：实现版本化导入 Service 与重复内容处理

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 完成“校验 → 解析 → hash → 切分 → 保存原文件 → 原子写入版本和 chunks”的应用流程，并证明重复内容不新增版本、变化内容保留历史。
- **实际完成内容：** 为 DatabaseManager 增加 async session factory；增加知识存储目录、文件上限、chunk size/overlap 配置；实现生成式安全文件名的 LocalDocumentStorage；实现 KnowledgeRepository 的 duplicate 查询、source/document get-or-create、document row lock、版本号递增、版本/hash 再检查和 chunk 批量写入；实现 DocumentIngestionService 的空文件/大小/必填值校验、标准化内容 SHA-256、快速重复检查、chunking、原文件保存、失败清理和 race duplicate 清理；实现 Document detail 读取及版本 DTO；真实测试重复上传复用 version 1，内容变化创建 version 2 且 version 1 仍可读取。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/config.py`
  - `src/enterprise_it_support/platform/database.py`
  - `src/enterprise_it_support/knowledge/domain.py`
  - `src/enterprise_it_support/knowledge/repository.py`
  - `src/enterprise_it_support/knowledge/service.py`
  - `tests/integration/knowledge/test_ingestion.py`
  - `.env.example`
  - `.gitignore`
  - `data/knowledge/.gitkeep`
  - `docs/project_journal.md`
- **请求或数据流程：** file bytes → size/type/parse → canonical text SHA-256 → 查同 Document 的 hash → 非重复时 Chunking → UUID raw path 保存 → Repository transaction 创建或锁定 Source/Document → 再查 hash → 创建 Version/Chunks → 返回 ID、version、chunk count；失败则删除新 raw file。
- **关键代码入口：** `DocumentIngestionService.ingest()`、`KnowledgeRepository.persist_import()`、`KnowledgeRepository.find_duplicate()`、`LocalDocumentStorage.save()`。
- **使用的核心技术：** SQLAlchemy AsyncSession、事务、`SELECT FOR UPDATE`、SHA-256、UUID 文件名、PostgreSQL unique constraints、pytest async fixture、真实测试数据库。
- **为什么采用当前实现：** hash 基于标准化文本而非文件 bytes，避免 PDF metadata 或换行差异制造无意义版本；先快速查重减少文件 I/O，再在写事务中复查防止常见 race；Repository 拥有 SQL，Service 只编排业务流程。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/knowledge/test_ingestion.py::test_duplicate_content_reuses_existing_document_version -q`；`.venv/bin/pytest tests/integration/knowledge/test_ingestion.py::test_changed_content_creates_new_version_and_keeps_history -q`；`.venv/bin/pytest tests/integration/knowledge/test_ingestion.py -q`。
- **测试结果：** 首次 collection 因 repository 模块不存在红灯；实现后测试 fixture 又因复用 Phase 1 HTTP 假 URL 报数据库认证失败，修正为真实 test URL；新版本测试先因 `get_document()` 不存在红灯；最终 `2 passed`。
- **遇到的问题：** Phase 1 的 `test_settings` 故意使用假数据库 URL，不能用于 Repository 集成测试；文件保存和数据库事务无法天然成为单一原子事务。
- **解决方法：** 知识集成 fixture 读取 `.env` 中隔离的真实 test URL；Service 在 DB 失败或事务内发现 race duplicate 时删除刚写入的 raw file，降低孤儿文件风险。
- **当前限制：** 进程在文件写入后、进入异常清理前崩溃仍可能留下孤儿文件；新 Document 的极端并发创建仍依赖 unique constraint，尚未实现冲突重试；同一 Document 不允许在后续版本改变 source type。
- **我需要理解的知识：** 逻辑去重与数据库唯一约束为什么都需要；为什么 hash 应基于规范化内容；跨文件系统和数据库无法获得普通单库事务的原子性。
- **与下一步骤的关系：** 四个 API 将复用 Service 和 Repository 公开 DTO；API 不直接访问 ORM，也不会自行计算版本号或 hash。

### Step 2.6：创建知识文档 API 与端到端集成测试

- **所属 Phase：** Phase 2：知识库数据模型与文档解析
- **完成日期：** 2026-07-19
- **本步骤目标：** 通过稳定的 HTTP seam 暴露文档上传、列表、详情和最新版本 Chunk 查询，同时保持路由层不直接访问 ORM 或编写 SQL。
- **实际完成内容：** 创建知识 API Pydantic Schema 和 APIRouter；把 Ingestion Service 装配到 FastAPI composition root；实现 `POST /knowledge/documents`、`GET /knowledge/documents`、`GET /knowledge/documents/{document_id}` 和 `GET /knowledge/documents/{document_id}/chunks`；重复上传返回 200，新版本创建返回 201；内部 raw file path 不通过 API 暴露；完成三格式上传、重复上传、详情和 Chunk 追溯集成测试。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/routes.py`
  - `src/enterprise_it_support/knowledge/schemas.py`
  - `src/enterprise_it_support/knowledge/domain.py`
  - `src/enterprise_it_support/knowledge/repository.py`
  - `src/enterprise_it_support/knowledge/service.py`
  - `apps/api/main.py`
  - `tests/integration/api/test_knowledge_documents.py`
  - `docs/project_journal.md`
- **请求或数据流程：** multipart upload → FastAPI 参数校验 → `DocumentIngestionService.ingest()` → parser → hash/duplicate → chunker → local storage → Repository transaction → PostgreSQL → `DocumentImportResponse`；GET → Service → Repository projection → Pydantic response。
- **关键代码入口：** `upload_document()`、`list_documents()`、`get_document()`、`get_document_chunks()`、`create_app()`。
- **使用的核心技术：** FastAPI multipart、Pydantic response model、依赖装配、统一 `ApplicationError`、TestClient、真实 PostgreSQL。
- **为什么采用当前实现：** HTTP 层只负责协议转换和安全错误映射；业务规则放在 Service，SQL 放在 Repository，使 API、未来 worker 和测试可以复用同一导入流程。详情返回全部 Version 摘要，Chunks 接口明确返回最新 Version，满足当前 API 规格且不提前设计版本选择功能。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/api/test_knowledge_documents.py -q`。
- **测试结果：** API 初始测试先得到 404；完成路由装配后，三种格式、上传读取、串行重复和不支持类型共 6 个测试案例通过。
- **遇到的问题：** Phase 1 测试使用可注入的 fake database lifecycle，无法自动构造依赖真实 `session_factory` 的 Knowledge Service。
- **解决方法：** `create_app()` 只在实际依赖是 `DatabaseManager` 时构造默认 Knowledge Service；测试仍可显式注入 Service，fake database 场景则让知识接口安全返回 503。
- **当前限制：** 列表未分页；Chunks API 只返回最新 Version；没有删除和归档 API；这些均不属于 Phase 2 原始范围。
- **我需要理解的知识：** composition root 为什么负责对象装配；HTTP Schema、domain DTO 与 ORM model 为什么分层；201 创建与 200 去重为什么表达不同结果。
- **与下一步骤的关系：** 收尾审查将用同一 HTTP seam 验证失败响应，并核对 API、README 和 Phase 2 原始规格是否一致。

### Step 2.7：修复 Phase 2 收尾审查中的必要问题

- **所属 Phase：** Phase 2：知识库数据模型与文档解析（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 修复并发首次导入、推导标题边界、async 阻塞和失败测试缺口，不引入 Embedding、检索、LLM 或新业务接口。
- **实际完成内容：** 进行 Spec 与 Standards 双轴审查；新增并发首次导入集成测试并复现 `knowledge_sources_name_key` 冲突；在 Repository transaction 开始处按 Knowledge Source + Document title 获取 PostgreSQL transaction advisory lock，使跨请求首次导入串行化；新增超长 parser 推导标题测试并在 Service 以 500 字符边界返回安全 422；使用 `asyncio.to_thread()` 执行同步 parser、Chunking 和本地文件 I/O，避免阻塞 async 事件循环；补空文件、超限文件、损坏 PDF 和 detail/chunks 404 API 测试；运行 Ruff 机械格式化。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/repository.py`
  - `src/enterprise_it_support/knowledge/service.py`
  - `tests/integration/knowledge/test_ingestion.py`
  - `tests/integration/api/test_knowledge_documents.py`
  - `docs/project_journal.md`
- **请求或数据流程：** 两个相同并发请求 → 各自快速查重均未命中 → 保存临时 raw file → transaction advisory lock 只允许一个请求进入 Document 创建区 → 第一个创建 Version 1 并提交 → 第二个获得锁后查到相同 hash → 复用 Version 1 → 删除第二份临时 raw file。
- **关键代码入口：** `KnowledgeRepository.persist_import()`、`DocumentIngestionService.ingest()`、`test_concurrent_first_import_reuses_one_document_version()`、`test_api_rejects_parser_inferred_title_longer_than_database_limit()`。
- **使用的核心技术：** PostgreSQL `pg_advisory_xact_lock`、`hashtextextended`、asyncio thread offload、真实并发集成测试、FastAPI error envelope、TDD 红绿循环。
- **为什么采用当前实现：** `SELECT FOR UPDATE` 只能锁已存在行，不能锁缺失的 Source/Document；advisory lock 使用逻辑 Document key，能在插入前跨连接协调，且随事务自动释放。超长 title 在 Service 拒绝，既保护 HTTP 又保护未来 worker 调用。同步 PDF 解析属于 CPU/阻塞工作，移出事件循环比在路由中混入线程逻辑更清晰。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/knowledge/test_ingestion.py::test_concurrent_first_import_reuses_one_document_version -q`；`.venv/bin/pytest tests/integration/api/test_knowledge_documents.py::test_api_rejects_parser_inferred_title_longer_than_database_limit -q`；`.venv/bin/pytest tests/integration/api/test_knowledge_documents.py -q`；`.venv/bin/ruff format .`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`。
- **测试结果：** 并发用例先以 PostgreSQL UniqueViolation 红灯，修复后 `1 passed`；超长标题先以 StringDataRightTruncation/未处理异常红灯，修复后 `1 passed`；知识 API 最终 `12 passed`；Ruff lint 与 format check 通过。
- **遇到的问题：** 初次不带额外权限运行全量 pytest 时，sandbox 禁止连接 `127.0.0.1:5432`，产生 3 failed、8 errors；这不是代码或数据库故障。第一次 Ruff format 后 import order 仍需 `ruff check --fix`。
- **解决方法：** 只为本机隔离测试数据库申请受控命令权限后重跑；保留第一次失败作为环境证据，不把它误判为产品 bug；运行 `ruff check --fix` 后再次执行 lint 和 format check。
- **当前限制：** advisory lock 依赖 PostgreSQL，符合本项目已确定的数据库技术栈；5 MB 默认限制和 thread offload 降低 PDF 资源风险，但尚无独立页数/解压后字符数限制；文件系统与数据库仍不是同一原子事务。
- **我需要理解的知识：** 为什么缺失行无法被普通行锁保护；transaction advisory lock 与唯一约束分别承担什么职责；async 服务为什么要把同步 PDF 解析移出事件循环。
- **与下一步骤的关系：** Blocking 和必要 Important 问题修复后，可以进行最终 migration、全量测试、真实 API 演示和文档一致性验收。

### Step 2.8：完成 Phase 2 最终运行验收与文档同步

- **所属 Phase：** Phase 2：知识库数据模型与文档解析（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 用真实 PostgreSQL、Alembic、Uvicorn 和 curl 证明 Phase 2 正常及失败路径可运行，并让 README、Backlog 和代码保持一致。
- **实际完成内容：** 全量运行 43 个测试；在隔离测试库把 migration 从 `0002` 降到 `0001` 再升级到 `0002 (head)`；启动真实 Uvicorn，上传虚构 VPN Markdown，读取最新 Version 的 4 个 Chunks，并验证空文件和 `.docx` 两个失败场景；更新 README 的当前 Phase、四个 API、配置、测试范围、明确不做和已知限制；调整 Backlog，使 Phase 2 合并知识模型与导入、Phase 3 起进入 Embedding/检索；忽略并清理 PDF 视觉 QA 临时 PNG。
- **新增或修改文件：**
  - `README.md`
  - `docs/backlog.md`
  - `.gitignore`
  - `docs/project_journal.md`
- **请求或数据流程：** curl multipart → Uvicorn/FastAPI → request ID → Service → thread-offloaded parser/chunker/storage → Repository/advisory lock/transaction → PostgreSQL → 201 import；GET chunks → latest Version query → Chunk trace metadata → 200；空文件 → Service validation → 422；`.docx` → parser registry rejection → 415。
- **关键代码入口：** `create_app()`、`upload_document()`、`DocumentIngestionService.ingest()`、`KnowledgeRepository.persist_import()`。
- **使用的核心技术：** Docker Compose PostgreSQL/pgvector、Alembic、Uvicorn、curl multipart、pytest、Ruff、只追加开发日志。
- **为什么采用当前实现：** 单元和 TestClient 测试不能单独证明容器端口、真实 migration、实际 ASGI server、multipart 和本地文件路径的组合行为；真实成功和失败演示提供了独立于测试代码的验收证据。
- **运行与验证命令：** `docker compose ps`；`.venv/bin/pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260719_0001`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic current`；`.venv/bin/alembic upgrade head`；`env PYTHONPATH=.:src .venv/bin/uvicorn apps.api.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log`；curl 上传、读取 Chunks、空文件和 `.docx` 请求。
- **测试结果：** `43 passed in 1.09s`；Ruff `All checks passed!` 且 `51 files already formatted`；migration 最终为 `20260719_0002 (head)`；真实 Markdown 上传 201、Version 1、4 Chunks；Chunks 查询 200；空文件 422；不支持类型 415；响应 request ID 均正确。
- **遇到的问题：** 仓库仍没有 HEAD 提交，无法运行标准 merge-base diff review；curl 的两个并行失败演示在工具编排层等待较久，但两个 HTTP 请求最终都正常完成。
- **解决方法：** 明确将审查基线设为当前工作区完整快照，并分别执行 Spec/Standards 审查；以 curl 的最终响应和服务日志为验收证据，不把工具等待时间当成应用失败。
- **当前限制：** 开发数据库保留一条 Phase 2 演示文档；PostgreSQL 容器继续运行，命名数据卷保留；PDF 无 OCR；TXT/Markdown 仅 UTF-8；列表无分页；无 Embedding、检索、LLM、Agent、工具或聊天功能。
- **我需要理解的知识：** 如何用 migration、测试和真实 smoke test 组成三层证据；为什么响应中的 Version ID 和 Chunk metadata 构成可追溯链；为什么文档必须明确区分已实现和未来能力。
- **与下一步骤的关系：** Phase 2 工程状态可作独立验收；本次工作到此停止，不自动进入 Phase 3。

## Phase 2 总结与索引

- **Step 2.1：** 领域语言与 TXT 标准化解析；
- **Step 2.2：** Markdown/PDF 解析与三份虚构样例；
- **Step 2.3：** 可配置、可追溯 Chunking；
- **Step 2.4：** 四个知识实体与 Alembic migration；
- **Step 2.5：** 版本化 Ingestion Service、Repository、去重和新版本；
- **Step 2.6：** 四个知识文档 API 与集成测试；
- **Step 2.7：** 并发幂等、边界校验、async 阻塞和失败路径修复；
- **Step 2.8：** 全量验证、真实演示和文档同步。

最终结论：Phase 2 的功能、测试、静态检查、migration、真实演示和文档均满足当前范围；未实现任何 Embedding、向量检索、LLM 或 Agent 功能。建议 Commit 为 `feat(knowledge): complete versioned document ingestion`，建议 Tag 为 `phase-2-complete`。

### Step 2.9：文档更新后的最终一致性复验

- **所属 Phase：** Phase 2：知识库数据模型与文档解析（收尾验收）
- **完成日期：** 2026-07-19
- **本步骤目标：** 确认 README、Backlog、Dev Log 和临时文件清理完成后，代码、测试、格式与范围边界没有回归。
- **实际完成内容：** 再次运行完整 pytest、Ruff lint/format、Python compileall 和范围关键词扫描；确认 `.env` 与运行时原文件目录被 Git 忽略；检查工作区状态并记录仓库仍没有初始提交。
- **新增或修改文件：** `docs/project_journal.md`。
- **请求或数据流程：** 最终工作区 → pytest 连接隔离 PostgreSQL → 43 个单元/集成案例 → Ruff/compileall → Git ignore 与范围扫描 → Phase 2 最终结论。
- **关键代码入口：** `pytest` 收集的 43 个测试、`pyproject.toml` Ruff/pytest 配置、`.gitignore`。
- **使用的核心技术：** pytest、Ruff、Python compileall、ripgrep、Git ignore。
- **为什么采用当前实现：** 文档和格式化本身也可能意外改变文件或暴露陈旧描述，因此必须在所有收尾写入完成后再做一次独立复验。
- **运行与验证命令：** `.venv/bin/pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`.venv/bin/python -m compileall -q apps src migrations scripts`；`rg` 范围扫描；`git status --short`；`git check-ignore .env data/knowledge/raw`。
- **测试结果：** 最终 `43 passed in 1.10s`；Ruff `All checks passed!`、`51 files already formatted`；compileall 成功；代码和依赖中没有 Phase 2 禁止的模型能力，关键词扫描唯一误命中为 middleware 的 `fullmatch` 子串；`.env` 与 `data/knowledge/raw` 均被忽略。
- **遇到的问题：** 朴素关键词 `llm` 会误命中单词 `fullmatch`，不能把字符串扫描结果直接当成范围蔓延证据。
- **解决方法：** 人工核对命中上下文，确认它是 request ID 正则的 `fullmatch()`，与 LLM 无关；最终范围结论结合依赖清单和模块内容作出。
- **当前限制：** 仓库没有 HEAD，所有项目文件仍显示未跟踪；本阶段未创建 commit 或 tag，只提供建议名称。
- **我需要理解的知识：** 为什么静态关键词扫描需要上下文解释；为什么最终测试必须在文档和格式化完成后重跑；Git ignored、untracked 和 committed 三种状态的区别。
- **与下一步骤的关系：** Phase 2 最终验收为 PASS；只有用户明确下达新 Phase 指令后才继续。

## Phase 2 最终复验补充

- **最终测试：** 43 passed；
- **最终 Ruff：** lint 与 format check 通过；
- **最终 migration：** `20260719_0002 (head)`；
- **最终运行演示：** 201 成功上传、200 Chunk 查询、422 空文件、415 不支持类型；
- **最终工程判断：** PASS。

---

## Phase 3：Embedding 与向量索引

### Step 3.1：定义 Embedding Provider seam 与稳定 Fake 实现

- **所属 Phase：** Phase 3：Embedding 与向量索引
- **完成日期：** 2026-07-19
- **本步骤目标：** 建立可替换的异步 Embedding Provider 边界，让测试不访问外部 API，同时保留真实 OpenAI/OpenAI-compatible 运行能力。
- **实际完成内容：** 在领域词汇表新增 Embedding、Embedding Profile 和 Indexed Chunk；定义只暴露 `embed_documents(texts)` 与 `embed_query(text)` 的 `EmbeddingProvider` Protocol；实现基于 SHA-256、跨进程稳定且 L2 归一化的 `FakeEmbeddingProvider`；实现使用官方 `AsyncOpenAI.embeddings.create()` 的 `OpenAIEmbeddingProvider`，支持模型、维度、base URL 和 API Key 注入，并将 SDK 异常转换为不泄漏密钥的 `EmbeddingProviderError`；增加 OpenAI 2.x 运行依赖。
- **新增或修改文件：**
  - `CONTEXT.md`
  - `src/enterprise_it_support/intelligence/embeddings.py`
  - `tests/unit/intelligence/__init__.py`
  - `tests/unit/intelligence/test_embeddings.py`
  - `pyproject.toml`
  - `docs/project_journal.md`
- **请求或数据流程：** texts → `EmbeddingProvider.embed_documents()` → Fake 的 SHA-256 数值展开或 OpenAI `/embeddings` → 保持输入顺序的 `list[list[float]]`；query → 同一 Provider/同一 Profile → 单个兼容向量。
- **关键代码入口：** `EmbeddingProvider`、`FakeEmbeddingProvider.embed_documents()`、`OpenAIEmbeddingProvider.embed_documents()`。
- **使用的核心技术：** Python Protocol、async interface、SHA-256、L2 normalization、OpenAI Async SDK、Pydantic SecretStr 的后续配置边界、pytest-asyncio。
- **为什么采用当前实现：** Provider seam 隔离外部模型供应商，Indexing Service 只依赖协议；Fake 不能使用 Python 内置 `hash()`，因为它会受进程随机化影响；模型、维度和版本共同定义兼容向量空间，不能只记录模型名称。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/intelligence/test_embeddings.py -q`；`.venv/bin/python -m pip install -e '.[dev]'`。
- **测试结果：** 首次 collection 因 `enterprise_it_support.intelligence.embeddings` 不存在而红灯；实现并安装官方 SDK 后 `1 passed`。首次依赖安装因 sandbox DNS 受限失败，经允许访问 PyPI 后安装 `openai 2.46.0` 成功。
- **遇到的问题：** 当前会话没有 OpenAI Docs MCP 或 API Key 凭证工具；普通 sandbox 无法访问 PyPI。
- **解决方法：** 不修改用户的全局 Codex MCP 配置，按技能回退规则只读取 OpenAI 官方 API Reference 和官方 Python SDK；测试和实现验证使用 Fake Provider；仅为依赖安装申请受控网络权限。
- **当前限制：** 尚未创建向量列、migration 或 Indexing Service；真实 Provider 未调用真实 API，因为本阶段验收明确要求测试不访问外部服务。
- **我需要理解的知识：** 为什么 Embedding Provider 是外部系统 seam；为什么 Fake 必须跨进程确定；为什么 query 和 document 必须使用相同 Embedding Profile。
- **与下一步骤的关系：** 下一步把 Provider 所需的模型、维度、版本、批大小、base URL 和 API Key 纳入 Settings，并创建 pgvector schema。

### Step 3.2：增加 Embedding 配置与 pgvector schema

- **所属 Phase：** Phase 3：Embedding 与向量索引
- **完成日期：** 2026-07-19
- **本步骤目标：** 把向量空间和 Provider 运行参数全部纳入环境配置，并让每个 Document Chunk 能原子保存向量及完整生成信息。
- **实际完成内容：** 新增 fake/openai Provider 类型、模型名、维度、版本、批大小、API Key 和 base URL Settings；API Key 使用 `SecretStr`；test 环境拒绝真实 Provider；为 `document_chunks` ORM 和 `20260719_0003` migration 增加无固定 typmod 的 pgvector `embedding`、`embedding_model`、`embedding_version`、`indexed_at`；增加完整性约束，禁止只保存部分 Embedding Profile；增加模型/版本普通索引。
- **新增或修改文件：**
  - `src/enterprise_it_support/platform/config.py`
  - `tests/unit/platform/test_config.py`
  - `src/enterprise_it_support/knowledge/models.py`
  - `migrations/versions/20260719_0003_add_chunk_embeddings.py`
  - `tests/integration/knowledge/test_migrations.py`
  - `docs/project_journal.md`
- **请求或数据流程：** `IT_SUPPORT_EMBEDDING_*` → Pydantic Settings 校验 → composition root 选择 Provider；Alembic `0003` → document_chunks 新增 vector/profile/time → 完整性 check constraint。
- **关键代码入口：** `Settings.require_isolated_test_database()`、`DocumentChunk.embedding`、migration `upgrade()`/`downgrade()`。
- **使用的核心技术：** Pydantic Settings、`SecretStr`、pgvector SQLAlchemy `Vector`、Alembic、PostgreSQL check constraint、真实 schema inspection。
- **为什么采用当前实现：** 模型名、维度和应用版本共同定义向量空间；列不固定 typmod 让 Fake 小向量和未来兼容 Provider 可替换，维度由 Service 严格验证；HNSW/IVFFlat 依赖稳定维度与检索算子，留到真正实现检索的阶段，避免本阶段提前设计。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/platform/test_config.py -q`；`.venv/bin/pytest tests/integration/knowledge/test_migrations.py -q`。
- **测试结果：** 配置测试先因 `EmbeddingProviderType` 不存在红灯，完成后 `9 passed`；migration 测试先因四列缺失红灯，完成后 `1 passed`。一次受控数据库命令等待是权限审批超时而非测试执行，重新审批后用例在 0.25 秒内通过。
- **遇到的问题：** 用户要求维度来自配置，而 PostgreSQL `vector(n)` 会把维度固定在 migration 中；同时本阶段标题中的“索引”容易与 HNSW 数据库索引混淆。
- **解决方法：** 使用 pgvector 可变维度 `vector` 存储，由 Indexing Service 校验所有输出长度；把本阶段“索引”定义为生成并持久化 Embedding 的 indexing workflow，近似最近邻索引等到检索阶段基于确定算子和维度创建。
- **当前限制：** 尚未实现 Service 维度校验和批量保存；没有 HNSW/IVFFlat；API Key 未写入 `.env.example` 之前不会用于真实运行。
- **我需要理解的知识：** `vector` 与 `vector(n)` 的差异；为什么完整性约束要求向量、模型、版本和时间全有或全无；为什么 test 环境应从配置层禁止真实 Provider。
- **与下一步骤的关系：** 下一步实现按批次独立事务的 Indexing Repository/Service，并通过维度错误和 Provider 失败测试证明部分失败可恢复。

### Step 3.3：实现批量 Indexing Service、失败隔离与 pgvector 查询验证

- **所属 Phase：** Phase 3：Embedding 与向量索引
- **完成日期：** 2026-07-19
- **本步骤目标：** 把未索引或 Profile 过期的 Chunks 分批生成向量，每批独立提交，并保证维度错误或单批 Provider 失败不会丢失其他批次结果。
- **实际完成内容：** 创建 `EmbeddingProfile`、候选 Chunk、写入命令、索引结果和状态 DTO；实现 Repository 的 Document 存在性检查、Profile 匹配、候选查询、每批事务写入、状态聚合和待索引 Document 列表；实现 `IndexingService.index_document()`、`index_pending_documents()` 和 `get_status()`；默认跳过同 Profile/同维度向量，`force=True` 重算；严格校验向量数量、维度和有限数值；批次失败记录安全错误日志并继续；真实验证 pgvector `vector_dims()` 与 cosine distance 排序。
- **新增或修改文件：**
  - `src/enterprise_it_support/knowledge/indexing.py`
  - `tests/integration/knowledge/test_indexing.py`
  - `docs/project_journal.md`
- **请求或数据流程：** document_id → 查询所有 Version 的 Chunks → 过滤当前 Embedding Profile → 按 batch size 分组 → Provider → 数量/维度/有限值校验 → 单批 PostgreSQL transaction → embedding/profile/indexed_at；失败批保持 pending → 继续下一批 → 返回聚合结果。
- **关键代码入口：** `IndexingService.index_document()`、`IndexingRepository.get_candidates()`、`IndexingRepository.save_batch()`、`IndexingRepository.get_status()`。
- **使用的核心技术：** SQLAlchemy async transaction、pgvector、PostgreSQL `vector_dims` 与 `<=>` cosine comparator、批处理、错误隔离、结构化安全日志、真实数据库集成测试。
- **为什么采用当前实现：** Document Version 和 Chunk 不可变，因此同一 Chunk 行加同一 Profile 即可判断内容未变化并跳过；每批独立事务让前面已完成批次不因后续 Provider 失败回滚；旧 Version 向量保留支持历史引用可复现，新 Version 只产生新的 pending Chunks。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/knowledge/test_indexing.py -q`；单独运行批量、维度错误、Provider 失败和 pgvector 距离测试。
- **测试结果：** 批量测试先因 indexing 模块不存在红灯，实现后通过；重复跳过、force、新 Version 测试 `3 passed`；错误维度测试通过；Provider 失败测试首次发现 `logger.exception` 会把虚构异常正文写入日志，改为仅记录异常类型后 `2 passed`；pgvector 实际存储/余弦排序测试 `1 passed`。
- **遇到的问题：** `logger.exception` 虽便于排错，但会附带外部 Provider 异常正文，可能包含请求细节；可变维度 vector 的当前 Profile 判断必须检查数据库中的实际 `vector_dims()`，不能只比较模型名和版本。
- **解决方法：** 日志改用参数化 `logger.error`，只记录 document ID、batch start/size 和 exception type；Profile 匹配同时比较 model、version 和 `vector_dims(embedding)`。
- **当前限制：** 没有持久化每次失败的详细索引任务记录，失败通过日志和仍为 pending 的 Chunk 表达；并发触发同一 Document 可能产生重复 Provider 成本，但最终写入幂等；尚未实现检索 Service。
- **我需要理解的知识：** 为什么 batch transaction 是失败隔离边界；为什么模型名相同仍要检查版本和维度；为什么旧 Version 向量保留但未来检索必须过滤有效 Version。
- **与下一步骤的关系：** 下一步把 Indexing Service 装配到 FastAPI，增加 index/index-status API，并用 Fake Provider 做端到端测试。

### Step 3.4：暴露索引 API、状态 API 与批量 CLI

- **所属 Phase：** Phase 3：Embedding 与向量索引
- **完成日期：** 2026-07-19
- **本步骤目标：** 让调用方可以通过 HTTP 索引单个 Document、读取索引覆盖状态，并通过 CLI 批量处理所有 pending 或 stale Documents。
- **实际完成内容：** 在应用 composition root 根据 Settings 组装 Fake 或 OpenAI-compatible Provider 和 `IndexingService`；新增 `POST /knowledge/documents/{document_id}/index`，支持可选 `force`；新增 `GET /knowledge/documents/{document_id}/index-status`；未知 Document 映射为统一 404 错误响应；新增 `python -m scripts.index_documents`，支持全部待处理 Document、`--document-id` 和 `--force`，任一 Chunk 失败时以非零退出码报告，同时保留成功批次；API 与 CLI 共用同一个 Service，不复制索引规则。
- **新增或修改文件：**
  - `apps/dependencies.py`
  - `apps/api/main.py`
  - `src/enterprise_it_support/knowledge/index_schemas.py`
  - `src/enterprise_it_support/knowledge/index_routes.py`
  - `scripts/__init__.py`
  - `scripts/index_documents.py`
  - `tests/integration/api/test_knowledge_documents.py`
  - `tests/integration/knowledge/test_indexing.py`
  - `docs/project_journal.md`
- **请求或数据流程：** HTTP/CLI 输入 → composition root 选择 Provider 和 Embedding Profile → `IndexingService` → `IndexingRepository` 查 pending/stale Chunks → Provider 批量生成向量 → 校验 → PostgreSQL；状态请求 → SQL 聚合 current/pending/stale → JSON。
- **关键代码入口：** `build_embedding_provider()`、`build_indexing_service()`、`index_document()` route、`get_index_status()` route、`scripts.index_documents.run()`。
- **使用的核心技术：** FastAPI dependency、Pydantic request/response schema、argparse、asyncio、进程退出码、依赖注入、真实 HTTP/数据库集成测试。
- **为什么采用当前实现：** HTTP 与 CLI 是不同适配器，但业务规则必须只有一个来源，所以二者都依赖 `IndexingService`；`force` 是显式请求而不是默认行为，避免重复 Provider 成本；CLI 输出 JSON，方便人读和后续脚本处理。
- **运行与验证命令：** `.venv/bin/pytest tests/integration/knowledge/test_indexing.py tests/integration/api/test_knowledge_documents.py -q`。
- **测试结果：** API 用例先因路由不存在得到 404，装配后通过；新增未知 Document 的 POST/GET 失败路径和 Profile 版本变化用例后，目标测试最终为 `23 passed`。
- **遇到的问题：** 第一次目标测试命令写错了账号 fixture 与 API 测试文件路径；随后在沙箱内连接 `127.0.0.1:5432` 被权限策略拒绝，并非 PostgreSQL 故障。
- **解决方法：** 使用 `rg --files` 确认真实路径，将 fixture 改为 `account_common_questions_faq.pdf`，API 测试改为 `tests/integration/api/test_knowledge_documents.py`；按权限规则批准测试进程访问本机 Docker PostgreSQL 后重跑通过。
- **当前限制：** API 同步等待整次索引完成，没有后台 job 表；索引大文档时请求耗时会增加；CLI 只输出汇总，不持久化每一次 job 的详细历史。
- **我需要理解的知识：** composition root 为什么负责具体 Provider 选择；API Adapter、CLI Adapter 与 Application Service 的职责区别；为什么 CLI 要用退出码表达部分失败。
- **与下一步骤的关系：** 下一步只做 Phase 3 文档同步、迁移往返、全量测试、Ruff 和真实开发库演示，不实现检索或 RAG。

### Step 3.5：完成 Phase 3 代码审查、文档同步与真实运行验收

- **所属 Phase：** Phase 3：Embedding 与向量索引
- **完成日期：** 2026-07-19
- **本步骤目标：** 对照原始范围审查实现，修复 Blocking/Important 问题，在真实 PostgreSQL/pgvector 上完成 migration、CLI、HTTP、失败路径、全量测试和静态检查验收。
- **实际完成内容：** 更新 README 的 Phase 3 能力、安装、配置、API、CLI、测试和限制；新增 Embedding/pgvector 技术文档；将 Backlog 从“Phase 3 同时做检索”修正为 Phase 3 仅生成/保存向量、Phase 4 才实现检索/RAG；补充 Profile 版本变化导致 stale 并重索引、未知文档 API 404 测试；移除 `_matches_profile()` 的未标注返回类型；完成安全、硬编码、重复逻辑、失败路径、范围越界和文档一致性审查；使用 Fake Provider 在开发库为 Phase 2 VPN 文档生成 4 个向量并读取真实状态。
- **新增或修改文件：**
  - `README.md`
  - `.env.example`
  - `CONTEXT.md`
  - `docs/backlog.md`
  - `docs/knowledge/embedding_indexing.md`
  - `src/enterprise_it_support/knowledge/indexing.py`
  - `tests/integration/knowledge/test_indexing.py`
  - `tests/integration/api/test_knowledge_documents.py`
  - `docs/project_journal.md`
- **请求或数据流程：** 示例 Document/Chunks → CLI → Fake Provider → 4 个 8 维向量 → `document_chunks` → HTTP `index-status` → `indexed_chunks=4`；未知 UUID → Service not found → CLI exit 2 或统一 HTTP 404；非法 `--force` → argparse 拒绝 → exit 2。
- **关键代码入口：** `python -m scripts.index_documents`、`IndexingService.index_document()`、`GET /knowledge/documents/{document_id}/index-status`、migration `20260719_0003`。
- **使用的核心技术：** pytest、Ruff、Alembic upgrade/downgrade、Docker Compose、真实 Uvicorn/curl、pgvector、Python packaging、Git ignore/secret scan。
- **为什么采用当前实现：** 收尾必须验证真实入口而不只依赖 pytest；普通本地安装避免本机 macOS/Python 3.14 把 editable-install `.pth` 标为 hidden 后跳过源码路径；文档阶段边界必须与用户当前指令一致，不能因早期 Backlog 把检索提前到 Phase 3。
- **运行与验证命令：** `docker compose up -d db`；`.venv/bin/alembic upgrade head`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260719_0002`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`.venv/bin/python -m pip check`；`.venv/bin/python -m scripts.index_documents`；`.venv/bin/python -m scripts.index_documents --document-id 00000000-0000-0000-0000-000000000000`；`.venv/bin/python -m scripts.index_documents --force`；Uvicorn + curl status/404。
- **测试结果：** 全量 `58 passed in 2.01s`；Ruff `All checks passed!`、`62 files already formatted`；`pip check` 无损坏依赖；开发库与测试库都是 `20260719_0003 (head)`；首次 CLI 索引 `4` Chunks、失败 `0`，第二次待处理 Document 为 `0`；真实状态 API 返回 200、4/4 indexed、dimension 8；未知文档返回 CLI exit 2 和 HTTP 404；非法 force 返回 exit 2。
- **遇到的问题：** migration 回退首次误用了不存在的日期 ID；随后 Docker Desktop 被外部关闭导致 connection refused；真实 CLI 首次暴露 pytest 的 `pythonpath` 掩盖了本机 editable install `.pth` 被 Python 3.14 跳过的问题；普通 pip 安装首次因 sandbox DNS 受限无法获取 build dependency。
- **解决方法：** 读取 migration 文件中的真实 revision 后用 `20260719_0002` 往返；重新启动 Docker Desktop 和项目 db 服务；将 README 安装改为普通 `pip install '.[dev]'` 并重新安装当前项目，随后用户指定的原 CLI 命令运行成功；依赖安装仅在获准后访问 PyPI。没有在业务入口写 `sys.path` hack。
- **当前限制：** 没有最终检索/RAG；没有 HNSW/IVFFlat ANN 索引；API 同步等待索引完成；索引 job/错误只汇总到返回值和日志，没有持久化任务历史；同一 Document 并发索引可能重复支付 Provider 成本；开发数据库保留 Phase 2 演示文档及其 4 个 Fake 向量；仓库没有 HEAD，项目文件仍为 untracked，未创建 commit/tag。
- **我需要理解的知识：** Embedding Profile 如何定义兼容向量空间；可变维度 `vector` 为什么必须由 Service 校验；独立 batch transaction 如何保留部分成功；pytest 的 `pythonpath` 为什么可能掩盖真实打包问题；为什么保留旧 Version 向量但后续检索必须过滤可用版本。
- **与下一步骤的关系：** Phase 3 工程验收为 PASS，本次到此停止；只有用户明确下达新 Phase 指令后才能进入 Knowledge Retrieval/RAG。

## Phase 3 总结与索引

- **Step 3.1：Provider seam** — `src/enterprise_it_support/intelligence/embeddings.py`；Fake 稳定向量与 OpenAI-compatible Adapter。
- **Step 3.2：配置和 schema** — `src/enterprise_it_support/platform/config.py`、`migrations/versions/20260719_0003_add_chunk_embeddings.py`。
- **Step 3.3：Indexing Service** — `src/enterprise_it_support/knowledge/indexing.py`；幂等、Profile、维度校验和批次失败隔离。
- **Step 3.4：API 与 CLI** — `src/enterprise_it_support/knowledge/index_routes.py`、`scripts/index_documents.py`。
- **Step 3.5：文档与验收** — `docs/knowledge/embedding_indexing.md`、`README.md`；58 tests、Ruff、migration 往返、CLI/HTTP 正常与失败演示。

最终结论：Phase 3 原始任务和验收标准均已满足，没有实现最终 Knowledge Retrieval、RAG、LLM 回答或 Agent。建议 Commit 为 `feat(knowledge): add embedding providers and pgvector indexing`，建议 Tag 为 `phase-3-complete`，工程判断为 **PASS**。

---

## Phase 4：混合检索与来源引用（Retrieval only）

### Step 4.1：定义统一检索合同与检索前权限数据模型

- **所属 Phase：** Phase 4：混合检索与来源引用。
- **完成日期：** 2026-07-22
- **本步骤目标：** 在不生成自然语言回答的边界内，定义统一 Retrieval interface、结果与引用结构，并为确定性检索前授权增加最小数据字段。
- **实际完成内容：** 新增异步 `KnowledgeRetriever.search(query, top_k, filters, user_context)`；定义 `SearchFilters`、`UserContext`、`SearchResult`、`Citation` 和检索方法枚举；为 Document 增加 `visibility` 与 `allowed_roles`；新增 `20260722_0004` migration，默认已有文档为 public，并创建 Chunk PostgreSQL full-text GIN expression index；扩展 migration 列检查。
- **新增或修改文件：** `src/enterprise_it_support/knowledge/retrieval.py`、`src/enterprise_it_support/knowledge/models.py`、`migrations/versions/20260722_0004_add_retrieval_permissions.py`、`tests/integration/knowledge/test_migrations.py`、`docs/project_journal.md`。
- **请求或数据流程：** query + filters + user role → 检索前状态/时间/visibility 条件 → 当前可用 Document Version → keyword/vector candidates → 后续混合排序 → SearchResult + Citation。
- **关键代码入口：** `KnowledgeRetriever.search()`、`RetrievalRepository._candidate_statement()`、migration `20260722_0004`。
- **使用的核心技术：** Python dataclass、SQLAlchemy async、PostgreSQL ARRAY、GIN、`to_tsvector`、确定性权限过滤。
- **为什么采用当前实现：** 权限和有效期必须进入两种候选 SQL 的共同基线，不能在返回结果后删除；Document Version 通过每个 Document 的最新可用版本窗口排名选取，避免旧版本与新版本同时进入检索。
- **运行与验证命令：** `.venv/bin/ruff check` 与 `.venv/bin/ruff format --check` 针对本步骤文件；修改前全量 `.venv/bin/python -m pytest -q`。
- **测试结果：** 本步骤文件格式检查通过；Ruff 首次发现两个未使用 import，移除后继续实施。修改前单元测试 `29 passed`，数据库相关 `3 failed, 26 errors`，原因是 Docker Desktop 未运行且本机 5432 不可达；migration 尚待数据库恢复后验证。
- **遇到的问题：** 用户指定的根目录 `AGENTS.md`、项目概览、Roadmap、Current State 和旧 Phase Report 均不存在；Git 也没有任何提交。
- **解决方法：** 以现有代码、测试、项目日志、Backlog、架构文档和当前用户范围为事实来源；缺失文档在 Phase 收尾补齐，不虚构提交历史。
- **当前限制：** 本步骤只固定合同与 schema；检索行为、API 和评估仍在后续步骤完成；数据库 migration 需要 Docker 恢复后做真实往返。
- **我需要理解的知识：** Retrieval authorization 为什么必须发生在候选查询前；RRF 分数与单路相关度分数为什么不是同一量纲；版本有效期与逻辑 Document 状态的区别。
- **与下一步骤的关系：** 下一步为关键词、向量和融合行为建立数据库集成测试及纯排序测试，并完成可验证实现。

### Step 4.2：实现 PostgreSQL 关键词、pgvector 向量与 RRF 混合检索

- **所属 Phase：** Phase 4：混合检索与来源引用。
- **完成日期：** 2026-07-22
- **本步骤目标：** 在统一 interface 后实现两路真实检索、共同的检索前过滤、RRF 融合、去重和 top-k。
- **实际完成内容：** `RetrievalRepository.search_keyword()` 使用 PostgreSQL `to_tsvector/websearch_to_tsquery/ts_rank_cd`；`search_vector()` 使用当前 Embedding Profile 和 pgvector cosine distance；两路只查询每个 Document 最新的有效 Version，并共同应用 document/source/status/effective/expires/visibility/role 条件；`KnowledgeRetriever.search()` 生成 query embedding、并行取候选、使用 RRF(k=60) 融合、按 Chunk ID 去重并截断 top-k；新增纯融合测试和真实数据库检索测试。
- **新增或修改文件：** `src/enterprise_it_support/knowledge/retrieval.py`、`tests/unit/knowledge/test_retrieval.py`、`tests/integration/knowledge/test_retrieval.py`、`docs/project_journal.md`。
- **请求或数据流程：** query → Fake/配置的 Embedding Provider → keyword SQL + vector SQL 并行 → authorization/version filters → RRF → deduplicate → top-k SearchResult。
- **关键代码入口：** `RetrievalRepository.search_keyword()`、`RetrievalRepository.search_vector()`、`KnowledgeRetriever.search()`。
- **使用的核心技术：** PostgreSQL FTS、pgvector cosine distance、SQL window function、asyncio gather、Reciprocal Rank Fusion。
- **为什么采用当前实现：** RRF 只依赖两路排序位置，不要求把全文 rank 和 cosine similarity 强行校准到同一分数尺度；精确向量扫描符合当前小型 MVP，避免在可变维度 vector 上提前绑定 HNSW typmod。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/knowledge/test_retrieval.py -q`；真实 PostgreSQL 下运行 migration、retrieval 与 knowledge API 聚焦测试。
- **测试结果：** 纯检索逻辑 `3 passed`；包含 migration、Retrieval 和 API 的聚焦套件 `29 passed in 1.84s`；相关 Ruff lint 通过。
- **遇到的问题：** Docker Desktop 初始未运行，修改前数据库测试全部因本机 5432 不可达而失败；Fake Embedding 只保证确定性，不模拟真实语义质量。
- **解决方法：** 获准启动 Docker Desktop 和项目 pgvector 容器后重跑真实数据库测试；向量单测使用 Chunk 自身文本验证确定的最近邻合同，语义召回由后续评估集从混合检索整体衡量。
- **当前限制：** 当前向量查询为 exact scan；全文配置为 `simple`，没有中文分词插件；角色名称按精确字符串匹配。
- **我需要理解的知识：** RRF 为什么适合融合异质量纲；为什么 Fake Embedding 可验证存储和排序合同但不能证明生产语义质量；为什么 authorization subquery 必须被两路复用。
- **与下一步骤的关系：** 下一步通过 HTTP contract 暴露同一个 retriever，不在路由重复检索或权限规则。

### Step 4.3：创建 POST /knowledge/search 并完成 HTTP 边界测试

- **所属 Phase：** Phase 4：混合检索与来源引用。
- **完成日期：** 2026-07-22
- **本步骤目标：** 用现有 FastAPI composition root 暴露 Retrieval-only API，并确保请求有界、响应引用完整、无结果可稳定表达。
- **实际完成内容：** 新增 Search request/filter/citation/result Pydantic schemas；实现 `POST /knowledge/search`；在 composition root 构造并注入 `KnowledgeRetriever`；验证 query/user_role 空白、top_k 1–50、嵌套 filters；用三份虚构 fixture 分别上传、索引并检索 VPN、Outlook、账号问题，验证完整 Citation、top-k 和空列表。
- **新增或修改文件：** `src/enterprise_it_support/knowledge/search_schemas.py`、`src/enterprise_it_support/knowledge/search_routes.py`、`apps/dependencies.py`、`apps/api/main.py`、`tests/integration/api/test_knowledge_documents.py`、`docs/project_journal.md`。
- **请求或数据流程：** POST JSON → Pydantic 边界校验 → SearchFilters/UserContext → KnowledgeRetriever → PostgreSQL/pgvector → `list[SearchResultResponse]`。
- **关键代码入口：** `search_knowledge()`、`KnowledgeSearchRequest`、`build_knowledge_retriever()`、`create_app()`。
- **使用的核心技术：** FastAPI APIRouter、Pydantic field validation、dependency composition、统一 request ID/error envelope。
- **为什么采用当前实现：** API 只做协议转换，权限、版本和排序仍由 Retrieval application boundary 负责；响应直接返回 evidence 列表，不引入 Phase 5 的回答、Prompt 或聊天模型。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/integration/knowledge/test_migrations.py tests/integration/knowledge/test_retrieval.py tests/integration/api/test_knowledge_documents.py -q`；`.venv/bin/python -m pytest tests/unit -q`；相关 Ruff lint/format。
- **测试结果：** 聚焦数据库/API 套件 `29 passed in 1.84s`；全部单元测试 `24 passed`；Ruff lint 通过，API 测试文件经 Ruff 格式化。
- **遇到的问题：** 旧 app factory 只有 ingestion/indexing 依赖，没有 Retrieval state；无结果的纯语义查询通常仍会返回最近向量。
- **解决方法：** 在 composition root 显式增加可注入 `knowledge_retriever`；无结果场景使用合法但不存在的 document filter，验证两路 SQL 在候选阶段均返回空集合。
- **当前限制：** API 由请求体传入 `user_role`，尚未连接真实身份认证；这是当前阶段明确的简化 user context，不应被描述为生产授权。
- **我需要理解的知识：** 401/403 身份边界与当前简化 role context 的区别；为什么 response DTO 不应直接暴露 ORM；为什么无结果不是错误响应。
- **与下一步骤的关系：** 下一步创建版本化评估数据和 CLI，使用同一 public `KnowledgeRetriever.search()` 计算 Recall@3/Recall@5。

### Step 4.4：创建 15 条检索评估集与 Recall CLI

- **所属 Phase：** Phase 4：混合检索与来源引用。
- **完成日期：** 2026-07-22
- **本步骤目标：** 建立可重复执行的基础检索质量基线，独立统计 Recall@3 和 Recall@5。
- **实际完成内容：** 创建 `phase-4-v1` JSON 数据集，包含 VPN、Outlook、账号各 5 条查询；实现数据集完整性校验、逐案例 top-5 检索、Recall@3/Recall@5 和 miss IDs；新增 `python -m scripts.evaluate_retrieval` CLI，支持 `--dataset`、`--user-role` 和显式 `--seed-fixtures`；seeding 使用三份虚构 fixture，重复运行复用相同 Document Version 并只补当前 Profile 向量；增加指标单测和真实数据库 CLI 集成测试。
- **新增或修改文件：** `data/evaluation/retrieval_cases.json`、`src/enterprise_it_support/evaluation/retrieval.py`、`scripts/evaluate_retrieval.py`、`tests/unit/evaluation/test_retrieval_evaluation.py`、`tests/integration/knowledge/test_retrieval.py`、`docs/project_journal.md`。
- **请求或数据流程：** versioned JSON cases → 每条 query 调用 KnowledgeRetriever top-5 → 比较 expected Document title → 聚合 Recall@3/Recall@5 → CLI JSON。
- **关键代码入口：** `load_retrieval_dataset()`、`evaluate_retrieval()`、`scripts.evaluate_retrieval.run()`。
- **使用的核心技术：** JSON versioned dataset、确定性 Recall@K、argparse、async CLI、Fake Embedding + 真实 PostgreSQL/pgvector。
- **为什么采用当前实现：** 每条案例只执行一次 top-5，Recall@3 从同一结果前缀派生，避免两次检索产生不一致；数据集使用逻辑 Document title 作为相关性标签，适合当前三文档小型基线并保持人可读。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/evaluation tests/unit/knowledge/test_retrieval.py -q`；`.venv/bin/python -m pytest tests/integration/knowledge/test_retrieval.py -q`；相关 Ruff lint/format。
- **测试结果：** 评估与融合单测 `5 passed`；真实 Retrieval + CLI 集成 `7 passed in 0.89s`；15 条测试查询的 `Recall@3=1.0`、`Recall@5=1.0`、miss 列表为空；Ruff lint 通过。
- **遇到的问题：** 评估文档必须与静态相关性标签使用稳定标题；如果 CLI 默认自动写库，会给只想测现有语料的调用造成意外副作用。
- **解决方法：** 固定三份 evaluation title 和 source name；seeding 必须显式传 `--seed-fixtures`，默认 CLI 只读现有索引。
- **当前限制：** 当前 15 条查询和三份虚构文档是小型演示基线，1.0 不代表生产语料质量；Fake Embedding 不具备真实语义泛化；相关性标签目前是单一目标 Document，不评估 Chunk 等级 nDCG/MRR。
- **我需要理解的知识：** Recall@K 的分母和命中定义；为什么评估集需要版本；为什么 seed 行为必须显式；为什么测试集满分不等于真实质量已经解决。
- **与下一步骤的关系：** 下一步按阶段验收矩阵执行 migration 往返、全量测试、真实 CLI/API 和文档同步，再决定 Phase 4 PASS/FAIL。

### Step 4.5：完成安全审查、真实运行验收与文档同步

- **所属 Phase：** Phase 4：混合检索与来源引用（收尾验收）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 对照全部 Phase 4 要求完成 migration、全量测试、真实 CLI/API、安全边界和文档一致性验收，且不进入下一 Phase。
- **实际完成内容：** 建立要求/实现/测试矩阵；测试库将 migration 从 `0004` 降到 `0003` 再升级到 `0004`；执行全量 pytest、Ruff、compileall、pip check；开发库升级到 `0004` 并实际 seed 三份虚构文档运行评估 CLI；重新安装本地项目后启动真实 Uvicorn，以 curl 验证搜索 200、非法 top_k 422、空 role 422；按权限边界做安全审查；更新 README、Backlog 和词汇表；补齐缺失的 Project Overview、Roadmap、Current State 与 Phase 4 report。
- **新增或修改文件：** `README.md`、`CONTEXT.md`、`docs/backlog.md`、`docs/PROJECT_OVERVIEW.md`、`docs/ROADMAP.md`、`docs/CURRENT_STATE.md`、`docs/phase_reports/phase_4.md`、`docs/project_journal.md`。
- **请求或数据流程：** 虚构 fixtures → ingestion/indexing → Retrieval CLI → 15 query results → Recall；HTTP JSON → validation → authorized hybrid retrieval → SearchResult response；非法输入 → unified 422 + request ID。
- **关键代码入口：** `KnowledgeRetriever.search()`、`search_knowledge()`、`scripts.evaluate_retrieval.run()`、migration `20260722_0004`。
- **使用的核心技术：** verification matrix、security review、Alembic round-trip、pytest、Ruff、Uvicorn/curl、pip package install、追加式项目文档。
- **为什么采用当前实现：** 阶段完成需要同时证明代码合同、真实 PostgreSQL 行为、HTTP/CLI 入口和文档一致；安全审查重点检查两路检索是否在候选阶段共同应用 authorization，而不是只依赖测试或返回后过滤。
- **运行与验证命令：** `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic downgrade 20260719_0003`；两个环境 `alembic upgrade/current`；`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`.venv/bin/python -m scripts.evaluate_retrieval --seed-fixtures` 和只读重跑；真实 Uvicorn + 三个 curl；`git diff --check`、`git status`、敏感模式扫描。
- **测试结果：** 最终 `77 passed in 2.57s`；Ruff `All checks passed!` 且 `72 files already formatted`；compileall 成功；pip check 无损坏依赖；开发/测试数据库均为 `20260722_0004 (head)`；15 cases 的 Recall@3/Recall@5 均为 1.0；真实搜索返回 200 和完整 Citation，两个非法请求均返回统一 422；敏感模式唯一命中是 logging 脱敏单测中的虚构 `api_key/password` 输入。
- **遇到的问题：** 真实 CLI 首次因虚拟环境仍安装 Phase 3 wheel 而 `ModuleNotFoundError`；本地重装又发现 setuptools 缺失；开发库中已有旧 VPN 演示文档，因此真实搜索 top-1 命中对应 VPN 文档但标题不是 evaluation title；仓库仍没有 HEAD，所有文件未跟踪。
- **解决方法：** 安装 setuptools 后用 `pip install --no-build-isolation .` 重新安装本地项目，再以原 CLI 命令成功运行；不写 `sys.path` hack；搜索验收按主题、内容和 Citation 判断；Git 状态如实记录，不擅自创建 commit。
- **当前限制：** `user_role` 自报、无真实认证；exact vector scan；`simple` FTS 无中文分词；Fake Embedding 小型评估不能代表生产；无 RAG/回答生成；根目录仍没有 `AGENTS.md`。
- **我需要理解的知识：** 测试 `pythonpath` 如何掩盖已安装包过期；安全审查为什么要区分当前简化授权合同与生产认证；为什么检索满分仍需记录数据规模和 Embedding 限制。
- **与下一步骤的关系：** Phase 4 工程结论为 PASS。本次在此停止，只有用户明确确认后才可开始自然语言 RAG 或其他后续 Phase。

## Phase 4 总结与索引

- **Step 4.1：** Retrieval contract、visibility/allowed_roles、migration 和 FTS index；
- **Step 4.2：** PostgreSQL keyword、pgvector vector、共同过滤与 RRF；
- **Step 4.3：** `POST /knowledge/search`、Citation 和 API tests；
- **Step 4.4：** 15 条评估集、Recall@3/Recall@5 CLI；
- **Step 4.5：** 安全审查、migration 往返、全量测试、真实 CLI/API 和文档同步。

最终结论：Phase 4 Retrieval-only 的功能、权限、测试、评估、运行入口和文档均满足本次范围；没有调用聊天模型或生成自然语言回答。建议 Commit 为 `feat(knowledge): add authorized hybrid retrieval`，建议 Tag 为 `phase-4-complete`，工程判断为 **PASS**。

---

### Step 4.6：修复无效向量与检索依赖失败边界

- **所属 Phase：** Phase 4 严格审查修复。
- **完成日期：** 2026-07-22
- **本步骤目标：** 消除零向量导致 cosine `NaN` 被错误提升为高分的问题，并让 Provider/数据库失败稳定映射为安全的 503。
- **实际完成内容：** 索引写入拒绝零向量；query embedding 拒绝零向量、非有限值和错误维度；vector retrieval 跳过非有限 distance；query embedding 增加有界 timeout；Provider、timeout 与 SQLAlchemy 失败统一转为 `RetrievalUnavailableError`，HTTP 只暴露通用 503。
- **新增或修改文件：** `knowledge/indexing.py`、`knowledge/retrieval.py`、`knowledge/search_routes.py`、配置、`.env.example` 及 unit/integration/API tests。
- **运行与验证命令：** Retrieval/evaluation unit tests；indexing、retrieval 与 search API 聚焦 integration tests。
- **测试结果：** unit `11 passed`；数据库聚焦套件中新增的零向量、NaN、维度、timeout、503 与 stored zero-vector tests 均通过。
- **当前限制：** timeout 只包围 query embedding；数据库连接/statement timeout 仍由 SQLAlchemy/基础设施配置负责。

### Step 4.7：对齐 FTS 查询表达式、GIN 索引与时间过滤语义

- **所属 Phase：** Phase 4 严格审查修复。
- **完成日期：** 2026-07-22
- **本步骤目标：** 确保生产 keyword SQL 可使用 migration 创建的 GIN expression index，并阻止调用方时间条件复活已过期版本。
- **实际完成内容：** keyword search expression 与 migration 精确统一为 Section + Chunk content；当前时间的生效/未过期条件始终应用；`effective_at` 和 `expires_at` 只作为额外收紧条件；API 要求带 timezone 的时间值；新增过期复活、未来有效截止、多版本 future-effective 和 GIN EXPLAIN tests。
- **新增或修改文件：** `knowledge/retrieval.py`、`knowledge/search_schemas.py`、retrieval/API/migration tests。
- **运行与验证命令：** PostgreSQL 聚焦 integration tests；`EXPLAIN (COSTS OFF)` 且测试中关闭 seqscan 以验证 expression index 可选用。
- **测试结果：** 新增时间、多版本和 EXPLAIN tests 均通过；migration test 确认 `ix_document_chunks_fts` 存在。
- **当前限制：** `simple` FTS 不提供中文分词；vector retrieval 仍为符合当前范围的 exact scan。

### Step 4.8：强化 Recall 数据集标注与干扰语料

- **所属 Phase：** Phase 4 严格审查修复。
- **完成日期：** 2026-07-22
- **本步骤目标：** 避免同名 Document 造成假阳性，并降低只有三份目标文档时的虚高 Recall。
- **实际完成内容：** 数据集升级为 `phase-4-v2`；标签以 source name + title 在运行时唯一解析成 Document UUID，指标按 UUID 判定；新增同标题不同来源单测；seed 语料从 3 份增加为 6 份，加入 VPN/Outlook/account 的近主题干扰文档。
- **新增或修改文件：** evaluation module、CLI、JSON dataset、3 个 distractor fixtures 及 unit/integration tests。
- **运行与验证命令：** evaluation unit tests；真实 PostgreSQL CLI integration；`PYTHONPATH=src IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.evaluate_retrieval`。
- **测试结果：** unit 标注解析通过；增强数据集真实结果为 15 cases、Recall@3=`0.8666666666666667`、Recall@5=`0.9333333333333333`，misses 分别为 `outlook-03/outlook-05` 与 `outlook-05`。不再把小型干净语料上的 1.0 当作可信质量结论。
- **当前限制：** 仍是小型、单一相关 Document 标签的数据集，不计算 Chunk 级 MRR/nDCG，也不代表生产语料分布。

### Step 4.9：严格审查修复后的最终复验与文档同步

- **所属 Phase：** Phase 4 严格审查收尾；没有进入下一 Phase。
- **完成日期：** 2026-07-22
- **本步骤目标：** 按用户指定顺序重新验证 migration、全量测试、失败路径、EXPLAIN 与 Recall，并同步阶段事实。
- **实际完成内容：** 重新安装当前本地 wheel；测试库执行 `0004 → 0003 → 0004` migration 往返，开发/测试数据库确认 head；运行全量和失败路径专项 tests；执行真实 FTS EXPLAIN ANALYZE；在测试数据库用 6 份 fixtures 执行 `phase-4-v2` Recall CLI；更新 README、CURRENT_STATE 与 Phase 4 report。
- **运行与验证命令：** 两环境 Alembic；`.venv/bin/python -m pytest -q`；失败路径定向 pytest；Docker 内 psql `EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)`；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.evaluate_retrieval --seed-fixtures`；Ruff、compileall、pip check、`git diff --check`。
- **测试结果：** 全量 `92 passed in 2.93s`；失败路径 `11 passed in 0.65s`；Ruff lint/format、compileall、pip check 和 diff check 通过；两数据库为 `20260722_0004 (head)`；EXPLAIN 使用 `Bitmap Index Scan on ix_document_chunks_fts`；Recall@3=`0.8666666666666667`、Recall@5=`0.9333333333333333`。
- **遇到的问题：** 沙箱首次阻止本机 PostgreSQL TCP；按审批机制在授权环境重跑后通过。普通安装模式下源码修改后需要重装 wheel，已按 README 执行。
- **当前限制：** Recall 数据仍小；`outlook-05` 仍是 top-5 miss；`user_role` 仍非可信身份；exact vector scan 和 `simple` FTS 保持为已知限制。
- **与下一步骤的关系：** Important 1–4 与评估可信度问题已闭环，Phase 4 适合提交；本次到此停止，不自动开始后续 Phase。

---

## Phase 5：可信 RAG 问答

### Step 5.1：实现受约束的 ModelGateway 与确定性 Fake

- **所属 Phase：** Phase 5：可信 RAG 问答。
- **完成日期：** 2026-07-22
- **本步骤目标：** 建立生成模型的唯一结构化调用 seam，支持配置化模型、超时、有限重试、Prompt 版本和 Token 用量记录，同时保证测试不访问真实模型。
- **实际完成内容：** 定义 `ModelGateway.generate_structured_response()`、消息、Token、调用元数据和结构化响应类型；实现队列式 `FakeModelGateway`；实现 OpenAI-compatible Chat Completions Adapter，使用 JSON Schema 严格输出、单次 timeout、最多 1–5 次显式尝试、指数退避，并只重试 timeout、连接、限流和 5xx；关闭 SDK 隐式重试；增加 Fake、瞬时重试、超时上限、malformed JSON 不重试和 Token 元数据测试；增加 model provider、名称、URL、密钥、timeout、attempt/output token 及 RAG context 配置。
- **新增或修改文件：** `src/enterprise_it_support/intelligence/model_gateway.py`、`src/enterprise_it_support/platform/config.py`、`.env.example`、`tests/unit/intelligence/test_model_gateway.py`、`tests/unit/platform/test_config.py`、`docs/project_journal.md`。
- **请求或数据流程：** versioned messages + Pydantic response schema → ModelGateway → OpenAI-compatible JSON Schema request 或 Fake queue → Pydantic validation → value + provider/configured/resolved model + prompt version + token usage + attempts。
- **关键代码入口：** `ModelGateway.generate_structured_response()`、`FakeModelGateway`、`OpenAICompatibleModelGateway.generate_structured_response()`。
- **使用的核心技术：** Python Protocol、Pydantic JSON Schema、OpenAI Async SDK、`asyncio.wait_for`、有界指数退避、确定性 Fake。
- **为什么采用当前实现：** 模型名称和供应商参数来自配置而非源码策略；应用拥有重试次数，避免 SDK 隐式重试与业务重试叠加；Schema/认证/非法请求立即失败，避免对永久错误浪费调用；所有测试从外部 Adapter seam 注入假 client，不产生真实 API 成本。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/intelligence/test_model_gateway.py tests/unit/platform/test_config.py -q`；相关 Ruff lint/format check。
- **测试结果：** 聚焦测试 `17 passed in 0.20s`；Ruff lint 通过；Ruff 格式化 1 个测试文件后，4 个相关文件 format check 通过。
- **遇到的问题：** 当前会话最初没有 OpenAI Developer Docs MCP；注册官方 MCP 后需要重启 Codex 才能调用；Ruff 首轮发现 PEP 695 Generic 风格和 100 字符行宽问题。
- **解决方法：** 按 `openai-docs` 技能注册只读官方 MCP；本轮不等待重启，改为检查当前安装的 `openai 2.46.0` 实际函数签名并用假 client 验证请求形状；使用 PEP 695 与机械格式化修正静态问题。
- **当前限制：** 未调用真实模型；不同 OpenAI-compatible 服务对 `json_schema` 支持可能不同，真实部署需要用所选服务做显式 smoke test；默认 Fake 尚待 RAG Service 提供领域化演示响应工厂。
- **与下一步骤的关系：** 下一步创建 conversation/message schema 与 migration，使 RAG Service 能保存问题、检索、模型、Prompt、Token 和最终回答轨迹。

### Step 5.2：创建 Conversation/Message schema 与事务 Repository

- **所属 Phase：** Phase 5：可信 RAG 问答。
- **完成日期：** 2026-07-22
- **本步骤目标：** 为多轮问答和模型调用轨迹建立可迁移、可查询的 PostgreSQL 持久化边界。
- **实际完成内容：** 新增 `conversations` 与 `messages` ORM；Conversation 固定 `user_role`，Message 以唯一递增 sequence 保存 user/assistant 内容；assistant message 保存 retrieval query、Chunk UUID 数组、resolved model、Prompt 版本、结构化最终回答、延迟、Token 和 request ID；新增 `20260722_0005` migration；实现 `ConversationRepository.save_turn()`，以 Conversation row lock 串行化同会话轮次，并在一个事务内写入用户与助手消息；角色变化被确定性拒绝；实现完整会话读取 DTO。
- **新增或修改文件：** `src/enterprise_it_support/conversation/`、`migrations/versions/20260722_0005_add_conversations.py`、`migrations/env.py`、`tests/integration/conversation/`、`tests/integration/knowledge/test_migrations.py`、`docs/project_journal.md`。
- **请求或数据流程：** completed RAG turn → create/lock Conversation → verify fixed role → allocate two sequence numbers → insert user + assistant Message in one transaction → later ordered read by conversation ID。
- **关键代码入口：** `Conversation`、`Message`、`ConversationRepository.save_turn()`、`ConversationRepository.get()`、migration `20260722_0005`。
- **使用的核心技术：** SQLAlchemy async、PostgreSQL UUID/ARRAY/JSONB、row lock、事务、Alembic、真实数据库集成测试。
- **为什么采用当前实现：** 一轮问答的两条消息必须同成同败；conversation role 固定可以避免调用方在后续轮次提高自报角色并混用旧会话；模型/Prompt/Token/Chunk trace 放在 assistant message 上，与最终回答一一对应且不复制独立 run 基础设施。
- **运行与验证命令：** `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/python -m pytest tests/integration/conversation tests/integration/knowledge/test_migrations.py -q`；相关 Ruff lint/format。
- **测试结果：** migration schema test `1 passed`；Repository 多轮与角色不变测试合并执行 `3 passed in 0.46s`；Ruff lint/format 通过；隔离测试数据库已升级到 `20260722_0005`。
- **遇到的问题：** migration 初版有一处超过项目 100 字符行宽；没有发现数据库行为错误。
- **解决方法：** 拆分约束声明并运行 Ruff 机械格式化后复验。
- **当前限制：** 当前 Repository 只保存成功生成或确定性拒答的完整 turn；模型调用在持久化前失败时尚未写入失败 attempt，独立 Agent Run/Step 审计属于后续 Phase。
- **与下一步骤的关系：** 下一步实现 RAG Answer Service，以 Retrieval 结果构建受控 Context、校验模型证据标签并通过本 Repository 保存最终回答。

### Step 5.3：实现有界 Context、拒答与确定性 Citation 的 RAG Answer Service

- **所属 Phase：** Phase 5：可信 RAG 问答。
- **完成日期：** 2026-07-22
- **本步骤目标：** 完成“问题 → 授权检索 → 受控 Context → 结构化生成 → Citation 校验 → 回答持久化”的核心应用流程。
- **实际完成内容：** 创建 `rag-answer-v1` Prompt 和 `RAGModelOutput`；Prompt 明确只依赖企业片段、不得把常识当企业规则、证据不足必须拒答、不得伪造引用、知识库事实与一般建议必须使用不同前缀；Context 只包含 Retrieval 返回的字段并通过序列化长度上限和二分截断控制；无 Retrieval 结果时不调用模型并返回固定拒答；模型返回 `answerable=false` 时丢弃其自由文本并返回同一固定拒答；模型只能选择 E 标签，Service 对越界/重复/空引用失败关闭，再从 `SearchResult.citation` 物化最终 Citation；完成后通过 Conversation Repository 保存完整 turn。默认 Fake 使用 Context 首个片段产生可重复的本地演示回答。
- **新增或修改文件：** `src/enterprise_it_support/agent_runtime/rag.py`、`apps/dependencies.py`、`src/enterprise_it_support/intelligence/model_gateway.py`、`tests/unit/agent_runtime/test_rag.py`、`docs/project_journal.md`。
- **请求或数据流程：** question + role → `KnowledgeRetriever.search()` → authorized `SearchResult` → bounded JSON Context + Prompt v1 → ModelGateway/Pydantic → evidence label allowlist → server-side Citation materialization → atomic Conversation turn save → `ChatTurnResult`。
- **关键代码入口：** `RAGAnswerService.ask()`、`RAGModelOutput`、`RAGAnswerService._materialize_answer()`、`RAG_SYSTEM_PROMPT`、`build_model_gateway()`。
- **使用的核心技术：** Pydantic structured output、JSON Context、deterministic allowlist validation、binary-search truncation、dependency injection、Fake Adapter。
- **为什么采用当前实现：** 模型不接收自由的 Citation schema，只能选择当前 Context 的短标签；服务器拥有标签到 Retrieval Citation 的唯一映射，因此模型无法改写 title/version/chunk ID。无证据和模型拒答路径由确定性代码生成，避免拒答文本本身发生幻觉。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/agent_runtime/test_rag.py -q`；ModelGateway + RAG 合并 unit tests；相关 Ruff lint/format。
- **测试结果：** RAG unit `6 passed in 0.30s`；ModelGateway + RAG 合并 `10 passed`；Ruff lint/format 通过。覆盖充分证据、零证据、模型拒答、越界 Citation、malformed model response 和 Context 字符上限。
- **遇到的问题：** Ruff 的 ambiguous-unicode 规则拒绝 Python 字符串中的全角冒号/逗号；初版按简单 remaining 字符截断不能严格覆盖 JSON 转义膨胀。
- **解决方法：** Prompt 规则使用英文与 ASCII 标点，中文事实/建议标签改为 `企业知识库:` / `一般建议:`；Context 截断改为按实际 JSON 序列化长度二分寻找最大可放入内容，并增加带引号长文本测试。
- **当前限制：** 当前多轮 Conversation 负责保存与继续 ID，但本阶段尚不把历史消息加入检索 query 或 Prompt；回答事实性仍需评估集验证，服务器能保证 Citation 来源合法但不能从形式上证明每句话都被证据蕴含。
- **与下一步骤的关系：** 下一步实现 chat HTTP Schema/Routes、composition root、真实数据库 API tests 和交互式 CLI。

### Step 5.4：创建 Chat API、会话读取 API 与 CLI，并完成真实集成测试

- **所属 Phase：** Phase 5：可信 RAG 问答。
- **完成日期：** 2026-07-22
- **本步骤目标：** 通过 HTTP 和终端公开可信 RAG MVP，并验证三类知识、持久化、多轮、错误与角色权限。
- **实际完成内容：** 新增 `POST /chat/ask`，返回 summary/answer/diagnosis/citations/limitations/next_steps/confidence 及 conversation/message ID、模型/Prompt/Token/延迟/request ID；新增 `GET /chat/conversations/{conversation_id}?user_role=...`，按固定会话角色读取完整轨迹；composition root 组装 ModelGateway、RAG Service 和 Conversation Repository；malformed/越界模型输出映射为安全 502，模型/检索/数据库不可用映射为安全 503，会话不存在为 404，角色变化为 403；新增 `python -m scripts.chat` 单次与交互模式；通过真实上传、Fake Embedding 索引、PostgreSQL Retrieval 和数据库会话验证 VPN、Outlook、账号问答。
- **新增或修改文件：** `src/enterprise_it_support/conversation/schemas.py`、`conversation/routes.py`、`interaction/errors.py`、`apps/api/main.py`、`scripts/chat.py`、API/Conversation/CLI tests、`docs/project_journal.md`。
- **请求或数据流程：** HTTP/CLI question → composition root RAG Service → authorized Retrieval → Fake/real ModelGateway → server Citation → conversation transaction → structured response；GET conversation → role equality check → ordered messages and trace。
- **关键代码入口：** `ask_chat()`、`get_conversation()`、`create_app()`、`scripts.chat.run()`。
- **使用的核心技术：** FastAPI/Pydantic、dependency injection、PostgreSQL integration、TestClient、argparse、async CLI。
- **为什么采用当前实现：** 路由只做协议和安全错误映射，不复制检索/Prompt/Citation/事务规则；GET 明确要求当前简化 `user_role` query，避免完全无角色边界地返回可能包含受限知识的会话；CLI 复用相同 Service 而不是另写一套 RAG。
- **运行与验证命令：** API integration `.venv/bin/python -m pytest tests/integration/api/test_knowledge_documents.py -q`；CLI integration；Phase 5 聚焦 pytest；相关 Ruff lint/format。
- **测试结果：** Chat 扩展后的 knowledge/API 文件 `31 passed in 1.84s`；CLI `1 passed in 0.52s`；ModelGateway、RAG、Conversation、API、CLI、Retrieval 聚焦套件 `57 passed in 2.73s`；Ruff lint/format 通过。
- **遇到的问题：** CLI 集成测试进程先运行 TestClient，root logger 已输出若干 JSON 行，首次直接解析全部 stdout 得到 JSON extra-data；新 CLI test import 顺序需要 Ruff 修正。
- **解决方法：** 测试只解析最后一个以 `conversation_id` 开始的 CLI JSON 对象，同时保留日志本身；使用 Ruff 机械排序并复验。产品 CLI 独立进程输出不受该 TestClient 前置日志影响。
- **当前限制：** GET 的 `user_role` 仍是调用方自报而非可信认证；CLI 当前按 turn 输出完整 JSON，不提供富文本界面；多轮只保存历史，不自动把历史加入当前 Prompt。
- **与下一步骤的关系：** 功能范围已闭环；下一步按 verification-loop 执行 migration 往返、全量质量门禁、真实 CLI/API smoke、安全检查和文档收尾。

### Step 5.5：补齐 Model 调用轨迹字段并重建 0005

- **所属 Phase：** Phase 5：可信 RAG 问答（收尾审查修复）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 修复初版 Message trace 只保存 resolved model 与三类 Token、无法完整解释模型选择和重试成本的问题。
- **实际完成内容：** Message/migration/Repository 增加 provider、configured model、resolved model、attempts、cached tokens 和 reasoning tokens；非模型拒答明确记录 provider=`not_called`、resolved model=`not-called`、attempts=0；API、GET conversation 和 CLI 同步公开这些元数据；修正 Provider 未返回 total_tokens 时使用 input+output 的 fallback。
- **新增或修改文件：** conversation models/repository/schemas/routes、RAG Service、ModelGateway、migration `0005`、CLI 与 migration/Repository tests。
- **请求或数据流程：** `ModelCallMetadata` → RAG completed turn → Conversation Repository → assistant Message columns → HTTP/CLI trace response。
- **关键代码入口：** `ModelCallMetadata`、`ConversationRepository.save_turn()`、`Message`、migration `20260722_0005`。
- **使用的核心技术：** PostgreSQL typed columns、nonnegative check constraints、Alembic round-trip、provider usage metadata。
- **为什么采用当前实现：** configured 与 resolved model 可能不同，attempts 决定真实调用次数，cached/reasoning tokens 在供应商报告时影响成本与诊断；这些数据不应只存在于瞬时 HTTP response。
- **运行与验证命令：** test DB `0005 → 0004 → 0005`；migration/Conversation/RAG tests；Chat API + ModelGateway tests；Ruff。
- **测试结果：** 重建 schema 后 migration/Conversation/RAG `10 passed in 0.64s`；Chat API + ModelGateway `36 passed in 1.81s`；测试库为 `20260722_0005 (head)`；Ruff 通过。
- **遇到的问题：** 已应用的测试库仍是初版 0005 schema，直接只运行测试会缺少新增列。
- **解决方法：** 因 0005 尚未发布且仓库无提交，更新同一 migration 后显式降到 0004 再升到 head，以真实重建证明 migration 内容；不伪造额外修补 revision。
- **当前限制：** 失败的模型 attempt 仍只返回安全 HTTP 错误，尚未保存独立失败 Run/Step；本 Phase 的 conversation/messages 负责成功回答与确定性拒答轨迹。
- **与下一步骤的关系：** 必要可观察性问题已修复；继续执行最终全量质量门禁和真实 smoke。

### Step 5.6：完成全量验收、真实 API/CLI 演示与文档同步

- **所属 Phase：** Phase 5：可信 RAG 问答（最终验收）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 对照全部用户要求证明代码、真实 PostgreSQL、HTTP、CLI、安全边界和文档一致，并在 Phase 5 停止。
- **实际完成内容：** 建立要求/实现/测试矩阵；执行全量 pytest、Ruff、compileall、pip check、secret pattern 和 Git 状态检查；普通安装当前 wheel；开发库升级到 0005；实际运行 chat CLI；启动真实 Uvicorn，用 curl 验证 chat 200、conversation trace 200、role mismatch 403 和 blank question 422；确认 trace 中保存 5 个 Chunk IDs、模型、Prompt、attempt、Token、延迟和 request ID；更新 README、Backlog、Overview、Roadmap、Current State、Glossary 和 Phase 5 report；把原 Phase 5 分类及其后计划顺延为 Phase 6–13，但没有实现下一 Phase。
- **新增或修改文件：** `README.md`、`CONTEXT.md`、`docs/backlog.md`、`docs/PROJECT_OVERVIEW.md`、`docs/ROADMAP.md`、`docs/CURRENT_STATE.md`、`docs/phase_reports/phase_5.md`、`docs/project_journal.md`。
- **请求或数据流程：** real CLI/HTTP → authorized hybrid Retrieval → bounded Context → Fake structured ModelGateway → server Citation → PostgreSQL Conversation → JSON output/readback。
- **关键代码入口：** `RAGAnswerService.ask()`、`ask_chat()`、`get_conversation()`、`scripts.chat.run()`、migration `20260722_0005`。
- **使用的核心技术：** verification matrix、pytest、Ruff、Alembic、Uvicorn/curl、PostgreSQL/pgvector、ordinary wheel install、append-only docs。
- **为什么采用当前实现：** Phase 完成不能只依赖 Fake unit tests；真实入口同时证明 packaging、composition root、数据库 schema、检索、引用、持久化和错误 envelope 能组合运行。文档按明确 Phase 5 指令修正，而历史日志保持不改写。
- **运行与验证命令：** test DB `0005 → 0004 → 0005`；`.venv/bin/python -m pytest -q`；Ruff lint/format；compileall；pip check；普通 pip install；两个环境 Alembic current；`python -m scripts.chat --question ...`；真实 Uvicorn + curl chat/trace/403/422；secret pattern scan；Git status/diff check；Backlog 字段计数。
- **测试结果：** 最终全量 `116 passed in 3.61s`；Ruff `All checks passed!` 且 `87 files already formatted`；compileall 成功；pip check 无损坏依赖；开发/测试数据库均为 `20260722_0005 (head)`；Backlog 13 个 Phase 的目标/输入/输出/验收字段各 13；敏感模式只有配置字段、文档说明和虚构脱敏测试命中。
- **真实演示结果：** CLI 返回 VPN 引用 Chunk `5c17c2bb-098e-41ca-acb4-c837ff6057b2` 与 conversation ID；HTTP chat 200 返回 Evaluation VPN Citation；GET trace 200；错误路径返回统一 403/422 和对应 request ID。
- **遇到的问题：** 沙箱首次禁止 Uvicorn 绑定 127.0.0.1:8000；一次 secret scan shell 正则引号不匹配；仓库仍没有 HEAD，`git diff --check` 无法像已跟踪仓库一样覆盖全部 untracked 内容。
- **解决方法：** 按权限机制受控启动本机 Uvicorn并在验收后正常关闭；使用多 `-e` 的安全 rg 模式重跑；用 Ruff/compileall/pytest、显式文件扫描和 Git status 补充无 HEAD 的限制，不创建用户未要求的 commit。
- **当前限制：** 真实 Model Provider 未付费调用；`user_role` 自报；历史消息不进入 Prompt；回答逐句 groundedness 需要后续评估；模型失败 attempt 尚无独立 Run/Step；仓库没有初始提交；根目录没有 `AGENTS.md`。
- **与下一步骤的关系：** Phase 5 工程结论为 PASS。本次到此停止，未经项目所有者明确确认不开始 Phase 6 请求分类。

## Phase 5 总结与索引

- **Step 5.1：** ModelGateway、Fake/OpenAI-compatible、timeout/retry/usage；
- **Step 5.2：** conversations/messages、Repository 和 migration 0005；
- **Step 5.3：** 有界 Context、结构化回答、拒答与确定性 Citation；
- **Step 5.4：** Chat API、Conversation GET、CLI 和真实角色测试；
- **Step 5.5：** provider/configured/resolved/attempt/cached/reasoning trace 补齐；
- **Step 5.6：** migration、全量质量门禁、真实 CLI/API 和文档收尾。

最终结论：Phase 5 的功能、失败路径、权限、持久化、测试、运行入口和文档满足本次范围；未进入请求分类或 Agent 工作流。建议 Commit 为 `feat(chat): add grounded RAG answers with citations`，建议 Tag 为 `phase-5-complete`，工程判断为 **PASS**。

### Step 5.7：增加原始相关性信号、证据闸门与负样本评测

- **所属 Phase：** Phase 5：可信 RAG 问答（严格审查 Blocking 修复）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 修复 RRF 只代表排序、非空知识库中的无关向量近邻仍会触发回答的问题。
- **实际完成内容：** `SearchResult` 分离保存 `rrf_score`、`keyword_score` 和 `vector_similarity`；新增配置化 `RelevancePolicy`，Fake Embedding Profile 只接受确定性关键词证据，真实 Embedding Profile 才允许使用配置化向量阈值；RAG 在构建 Context 前过滤证据，但审计轨迹仍保存全部原始检索 Chunk IDs；全文查询改为过滤常见问句词后的 any-term FTS，避免严格多词 AND 伤害正样本；评测集升级为 `phase-5-v1`，保留 15 个正样本并增加 3 个负样本，输出 Recall@3/5、false answer rate 和 abstention accuracy。
- **新增或修改文件：** `knowledge/retrieval.py`、`agent_runtime/rag.py`、Search API schema/route、`platform/config.py`、`apps/dependencies.py`、API/CLI composition、retrieval dataset/evaluation/CLI、相关 unit/integration tests、`.env.example`。
- **请求或数据流程：** authorized Retrieval → raw keyword/vector signals + RRF order → profile-aware RelevancePolicy → relevant complete evidence only → ModelGateway；全部检索 IDs → Conversation trace。
- **关键代码入口：** `RelevancePolicy.select()`、`KnowledgeRetriever._fuse()`、`RAGAnswerService.ask()`、`evaluate_retrieval()`。
- **为什么采用当前实现：** RRF 分数依赖候选排名，不能跨查询解释；Fake Embedding 是哈希向量，不能假装具有语义相关性；关键词与向量原始信号分别保留后，阈值可以随 Embedding Profile 通过版本化数据集校准。
- **红绿验证：** 首轮 RAG 测试因缺少 `RelevancePolicy` 收集失败；首轮真实评测用未校准关键词阈值时 Recall@3 仅 `0.0667`，降阈值后仍为 `0.4667`，进一步修正 FTS 为安全 any-term 语义后达到要求；最终相关单元与 PostgreSQL 集成聚焦测试 `22 passed in 0.72s`。
- **实际评测结果：** 18 cases；正样本 15、负样本 3；一次独立 CLI 快照为 Recall@3=`0.9333`、Recall@5=`1.0`、false_answer_rate=`0.0`、abstention_accuracy=`1.0`。Recall@3 的具体 miss 会受等分候选 UUID tie-break 影响，因此测试约束质量门槛而不硬编码不稳定 ID。
- **当前限制：** `0.001` 关键词阈值只针对当前 `simple` FTS 演示基线；切换真实 Embedding model/version 前必须用代表性正负样本重新校准关键词与向量阈值。
- **与下一步骤的关系：** 第一个 Blocking 已闭环；下一步修正 strict Structured Outputs Schema。

### Step 5.8：修正 RAG strict Structured Outputs Schema

- **所属 Phase：** Phase 5：可信 RAG 问答（严格审查 Blocking 修复）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 保证发送给 OpenAI-compatible strict Structured Outputs 的 RAG 根 Schema 将全部业务字段声明为 required。
- **实际完成内容：** 移除 `RAGModelOutput` 四个数组字段的 Pydantic 默认工厂；空数组仍是合法值，但必须由模型明确返回；新增 Gateway 契约测试，比较 JSON Schema 的 `required` 与 `properties` 全集并验证 `additionalProperties=false`。
- **新增或修改文件：** `agent_runtime/rag.py`、`tests/unit/intelligence/test_model_gateway.py`、`docs/project_journal.md`。
- **红绿验证：** 新测试先显示 `diagnosis/evidence_ids/limitations/next_steps` 未进入 required；最小修复后 ModelGateway + RAG 聚焦测试 `14 passed in 0.30s`。
- **为什么采用当前实现：** strict Structured Outputs 要求所有字段必填；把“可为空”和“可省略”分开，避免宽松本地 stub 接受而真实服务端拒绝 Schema。
- **当前限制：** 自动测试仍不访问付费 Provider；所选真实 endpoint/model 上的 smoke 必须由操作者显式授权并提供预算和非敏感测试 Context。
- **与下一步骤的关系：** 第二个 Blocking 已闭环；下一步把成功回答与每次 Turn 调用轨迹分离，并持久化失败。

### Step 5.9：分离 Grounded Answer 与 TurnTrace，并持久化失败尝试

- **所属 Phase：** Phase 5：可信 RAG 问答（严格审查 Blocking 修复）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 让每个已接受问答尝试都产生可审计轨迹，而不是只有成功回答或确定性拒答才保存。
- **实际完成内容：** 新增 `TurnTrace`、`TurnStatus` 和 `ErrorStage`；Conversation Repository 改为接收统一 trace，并在同一事务保存用户问题与 succeeded/refused/failed assistant outcome；新增 migration `20260722_0006`，保存 status、error stage 和安全 error code，并用数据库约束保证成功/拒答必须有 response、失败必须无 response 且有错误分类；ModelGateway 异常携带 provider/configured/resolved model、Prompt、实际 attempts 和可用 Token usage；RAG 对 retrieval、timeout、provider unavailable、malformed schema 和 Citation 越界分别保存失败轨迹后再抛出原安全异常；Conversation GET 公开安全 outcome 字段但不保存 Provider 原始异常正文。
- **新增或修改文件：** ModelGateway、RAG Service、conversation model/repository/schema/route、migration `0006`、ModelGateway/RAG/Repository/API/migration tests、`docs/project_journal.md`。
- **请求或数据流程：** accepted question → retrieval/model/validation/citation → construct `TurnTrace` regardless of outcome → atomic user + assistant persistence → re-raise safe typed failure for HTTP 502/503 mapping。
- **红绿验证：** Gateway 测试先以异常没有 metadata 的 `AttributeError` 红灯；RAG 测试先因缺少 Turn outcome seam 红灯；首次 PostgreSQL 失败写入因 JSONB 把 Python `None` 序列化为 JSON `null` 而违反 SQL `IS NULL` 约束，修正为 `JSONB(none_as_null=True)` 后转绿。
- **测试结果：** Gateway attempts/usage、RAG 四类模型/校验失败、Repository failed outcome、0006 migration 和五类真实 API/数据库失败轨迹的聚焦回归 `60 passed in 2.39s`；API 仍返回安全 502/503，数据库只保存稳定 error code，不含测试中的 fictional secret detail。
- **当前限制：** 如果 Conversation 数据库本身不可用，系统无法把数据库故障写回同一数据库；这是不可消除的单存储边界，需要外部日志/监控承接。失败 HTTP 响应仍只返回 request ID，不新增按 request ID 查询轨迹的公开接口。
- **与下一步骤的关系：** 三个 Blocking 已全部形成代码与测试闭环；下一步只做安全/文档收口和完整质量门禁，不进入后续 Phase。

### Step 5.10：完成 Blocking 修复后的全量验收与安全文档收口

- **所属 Phase：** Phase 5：可信 RAG 问答（严格审查闭环）。
- **完成日期：** 2026-07-22
- **本步骤目标：** 用全量测试和真实数据库证明三个 Blocking 已关闭，并把项目声明收敛到代码实际保证。
- **实际完成内容：** 建立 `17255bd chore: import current project snapshot` 诚实基线；执行全量 pytest、Ruff、compileall、pip check、migration 往返和 18-case 评测；更新 Glossary、README、Overview、Roadmap、Backlog、Current State 和 Phase 5 report；把“真实/合法 Citation”统一收敛为“Citation 来源绑定”，明确它不等于逐句蕴含；将产品明确标记为本地演示，记录自报 role、无 subject/tenant、Context 截断、GET 无分页和 SDK client 未统一关闭；README 与 `.env.example` 增加真实 Provider 会接收员工查询/企业 Context 的醒目数据提示。
- **最终测试结果：** 全量 `131 passed in 4.07s`；Blocking 聚焦回归 `60 passed in 2.39s`；Ruff `All checks passed!`，`88 files already formatted`；compileall 成功；pip check 无损坏依赖；`git diff --check` 通过。
- **数据库验证：** test DB migration `20260722_0006 → 20260722_0005 → 20260722_0006` 成功；开发库和测试库均为 `20260722_0006 (head)`。
- **评测结果：** `phase-5-v1` 共 18 cases；Recall@3=`0.9333333333333333`、Recall@5=`1.0`、false_answer_rate=`0.0`、abstention_accuracy=`1.0`。
- **安全结论：** 当前可以作为可重复的本地演示 MVP 提交；不能宣称生产认证、租户隔离或回答逐句事实验证。没有为了关闭文档问题而伪造 Principal/认证实现。
- **与下一步骤的关系：** Phase 5 到此停止；未经用户明确确认，不进入 Phase 6。剩余 Important 保留在 Current State，不在本轮扩大范围。

### Step 5.11：严格收尾验收、Profile 绑定与真实演示回归

- **所属 Phase：** Phase 5：可信 RAG 问答（最终收尾；未进入 Phase 6）。
- **完成日期：** 2026-07-23
- **本步骤目标：** 按原始任务、验收标准、代码、安全、失败路径、实际演示和学习要求重新验收，只修复新发现的 Blocking 与必要 Important。
- **审查结论：** 两条独立审查轴均未发现新的 Blocking，也未发现 Phase 6+ 提前实现。必要 Important 包括向量阈值未与具体 Embedding Profile 强绑定、FAR 名称可能被误读为回答级指标、Fake 演示固定使用 Context 第一项导致宽泛 VPN 问题命中同主题干扰文档，以及少量过时命名/说明。
- **实际完成内容：** 增加 `IT_SUPPORT_RAG_VECTOR_THRESHOLD_PROFILE`，真实向量阈值必须精确绑定 `<model>:<dimension>:<version>`，不匹配时配置失败关闭；评测内部改用 `would_call_model` 并在 CLI 输出 `false_answer_rate_scope=relevance_gate_proxy`；版本化并复用确定性关键词提取；Context 携带 Retrieval 的 `keyword_score`，默认 Fake 按问题关键词重合度和 raw score 选择证据；修正过时测试名、模块说明和 RRF 变量名；README、Current State 与 Phase Report 同步真实能力和限制。
- **红绿证据：** 新增“VPN Configuration SOP + VPN Security Notice”真实 PostgreSQL/API 回归；首次运行失败，实际返回 Security Notice；最小修复后 `1 passed`，宽泛 CLI 问题返回配置文档、`vpn.demo.invalid` 和由 Retrieval 物化的 E3 Citation。
- **环境问题：** 第一次全量测试因 Docker Desktop 未运行而出现 `65 passed, 4 failed, 62 errors`，共同根因是本机 PostgreSQL `connection refused`，不是代码断言失败。启动 Docker Desktop 和仓库 Compose 服务后数据库 healthy，未跳过或弱化任何测试。
- **运行与验证命令：** `docker compose ps/up -d`；test DB `alembic upgrade/current` 和 `0006 → 0005 → 0006`；`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；`scripts.evaluate_retrieval --seed-fixtures`；两次 `scripts.chat`；五类失败轨迹专项 pytest。
- **最终结果：** 全量 `133 passed in 4.34s`；Ruff `All checks passed!` 且 `88 files already formatted`；compileall 成功；pip check 无损坏依赖；migration head 为 `20260722_0006`；18-case Recall@3=`0.9333333333333333`、Recall@5=`1.0`、gate-proxy FAR=`0.0`、abstention accuracy=`1.0`；五类失败专项 `5 passed in 0.82s`。
- **真实演示：** 正常场景 “How do I configure the company VPN?” 返回配置步骤和来源绑定 Citation；失败场景一“量子打印机政策”确定性拒答，模型 attempts/tokens 为 0；失败场景二覆盖 retrieval/timeout/Provider/malformed/citation，HTTP 为安全 502/503 且数据库保存 failed trace。
- **当前边界：** `user_role` 仍自报且无 subject/tenant，只适合本地演示；Citation 不证明逐句蕴含；真实 Provider smoke 未经预算和数据授权未运行；Context 字符截断、GET 无分页和 SDK client 未统一关闭仍是延后项。
- **学习状态：** 工程验收为 PASS；完整 Phase 结论在用户完成本次面试题与独立练习前为 CONDITIONAL PASS。建议 Commit：`fix(rag): close phase 5 acceptance gaps`；建议 Tag：完成学习验收后使用 `phase-5-complete`。
- **与下一步骤的关系：** 本次停止在 Phase 5，不创建 Phase 6 功能；只有用户另行确认并完成学习验收后才讨论下一阶段。

---

## Phase 6：LangGraph Agent Runtime 与意图路由

### Step 6.1：确认运行时边界、引入 LangGraph 并配置执行上限

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由。
- **完成日期：** 2026-07-23
- **本步骤目标：** 在不改写 Phase 5 RAG 的前提下确认当前 LangGraph API、引入数据库 checkpoint 依赖，并把低置信度、节点数、重试和超时限制变成强类型配置。
- **实际完成内容：** 读取官方 LangGraph 1.x 的 `StateGraph`、`thread_id` checkpoint、`AsyncPostgresSaver` 和 `recursion_limit` 文档；安装 `langgraph 1.2.9`、`langgraph-checkpoint-postgres 3.1.0` 与 psycopg pool；新增意图置信度阈值、最大节点数、最大重试数、单节点超时和总运行超时配置；总超时必须严格大于单节点超时；同步 `.env.example`。
- **新增或修改文件：** `pyproject.toml`、`.env.example`、`src/enterprise_it_support/platform/config.py`、`tests/unit/platform/test_config.py`、`docs/project_journal.md`。
- **请求或数据流程：** 环境变量 → Pydantic Settings 边界校验 → Agent Runtime 使用确定性限制 → LangGraph 运行时和 PostgreSQL checkpointer。
- **关键代码入口：** `Settings.agent_intent_confidence_threshold`、`Settings.agent_max_nodes`、`Settings.agent_max_retries`、`Settings.agent_node_timeout_seconds`、`Settings.agent_timeout_seconds`。
- **为什么采用当前实现：** LangGraph 负责显式状态转换和 checkpoint；业务运行/步骤审计仍由本项目自己的 Repository 维护。限制全部配置化，避免把循环、重试和超时散落在节点实现中。
- **运行与验证命令：** `.venv/bin/python -m pip install -e '.[dev]'`；`.venv/bin/python -m pytest tests/unit/platform/test_config.py -q`；`.venv/bin/ruff check src/enterprise_it_support/platform/config.py tests/unit/platform/test_config.py`。
- **测试结果：** 依赖安装成功；配置聚焦测试 `15 passed in 0.02s`；Ruff `All checks passed!`。
- **遇到的问题：** 沙箱内 pip 无法访问本机 `127.0.0.1:7897` 代理，首次安装失败。
- **解决方法：** 按权限机制使用获准的网络安装重试；没有修改代理或全局 Python 环境。
- **当前限制：** 本步骤只建立依赖和配置边界，尚未定义 AgentState、节点、业务持久化表或 HTTP 入口。
- **与下一步骤的关系：** 下一步定义结构化分类、AgentState 和 LangGraph 节点，并用路由/异常/最大步骤单元测试驱动实现。

### Step 6.2：实现结构化意图分类、AgentState 与有界 LangGraph 路由

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由。
- **完成日期：** 2026-07-23
- **本步骤目标：** 把单次 Agent 请求改造成显式状态图，覆盖六类意图、低置信度澄清、三类诊断占位、工单未开放、升级、异常和最大步骤保护。
- **实际完成内容：** 定义完整 `AgentState`、六类 `AgentIntent`、三档风险、严格 `IntentClassification` 及只允许简短决策说明的 `reasoning_summary`；实现 `intake`、`classify_intent`、`request_clarification`、`retrieve_knowledge`、`compose_answer`、三类 diagnosis placeholder、`ticket_unavailable`、`escalate_to_human` 和 `finalize`；每个节点都有单节点超时和有限重试；graph 使用 `recursion_limit`，总执行使用独立 timeout；节点错误只保存稳定错误码和安全文案。
- **兼容性改动：** `RAGAnswerService` 新增 `answer_from_results()`，让 graph 的 retrieval 与 compose 节点职责分离，同时原 `ask()` 继续复用同一生成、验证、Citation 和 Conversation 持久化逻辑。
- **新增或修改文件：** `src/enterprise_it_support/agent_runtime/state.py`、`runtime.py`、`rag.py`、`tests/unit/agent_runtime/test_runtime.py`、`docs/project_journal.md`。
- **请求或数据流程：** intake → structured classification → deterministic confidence/intent route → clarification、RAG、diagnosis placeholder、ticket unavailable 或 escalation → finalize。
- **关键代码入口：** `AgentRuntime.run()`、`AgentRuntime._build_graph()`、`AgentRuntime._bounded_node()`、`IntentClassification`、`RAGAnswerService.answer_from_results()`。
- **为什么采用当前实现：** 模型只返回受 Schema 约束的语义分类；阈值、路径、执行上限、风险兜底和结束条件都由确定性代码控制。诊断和工单仅返回占位结果，没有注册或执行任何工具。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/agent_runtime/test_runtime.py tests/unit/agent_runtime/test_rag.py -q`；Ruff 与 compileall 聚焦检查。
- **测试结果：** 路由、低置信度、升级、异常重试、最大步骤、checkpoint 恢复和原 RAG 聚焦回归共 `23 passed in 0.68s`；Ruff 与 compileall 通过。
- **遇到的问题：** 初版错误收敛在进入 `finalize` 后会清空上游安全错误状态。
- **解决方法：** bounded wrapper 只在非 finalize 节点成功时清除本节点重试错误；finalize 保留上游错误码和 failed 状态。
- **当前限制：** 当前 checkpoint 测试使用 LangGraph `InMemorySaver`；业务 run/step ORM 和 migration 已定义，但尚未完成真实 PostgreSQL 与官方 `AsyncPostgresSaver` 验证。
- **与下一步骤的关系：** 下一步应用 migration，验证 `agent_runs`、`agent_steps` 的真实事务行为及跨 checkpointer 实例恢复。

### Step 6.3：实现 Agent Run/Step 数据库持久化与 PostgreSQL checkpoint

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由。
- **完成日期：** 2026-07-23
- **本步骤目标：** 让每次 Agent 请求和节点尝试可审计，并证明 graph state 能从数据库 checkpoint 恢复。
- **实际完成内容：** 新增 `agent_runs` 和 `agent_steps` ORM、Repository 与 Alembic `20260723_0007`；Run 保存请求、Conversation 关联、分类、当前节点、完整最新 state、稳定错误码和生命周期；Step 以 run 内递增序号追加节点名、成功/失败、state snapshot、安全错误和延迟；接入官方 `AsyncPostgresSaver`，首次启动执行幂等 setup。
- **新增或修改文件：** `agent_runtime/models.py`、`persistence.py`、migration `20260723_0007_add_agent_runs.py`、`migrations/env.py`、migration tests、`tests/integration/agent_runtime/test_persistence.py`。
- **请求或数据流程：** create Agent Run → 每个节点尝试写 Agent Step 并更新 Run state → LangGraph 以 run ID 作为 thread ID 保存 checkpoint → Repository/graph 可分别恢复业务轨迹与执行 state。
- **关键代码入口：** `AgentRunRepository.create_run()`、`save_step()`、`get()`、`AgentRuntime.load_checkpoint()`、`AsyncPostgresSaver.setup()`。
- **为什么采用当前实现：** LangGraph checkpoint 表由官方 saver 管理其内部版本；本项目的 migration 只拥有稳定的业务审计表，避免依赖第三方内部表结构作为产品 API。
- **运行与验证命令：** `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`alembic current`；PostgreSQL persistence、checkpoint 与 migration 聚焦 pytest；Ruff。
- **测试结果：** 测试库达到 `20260723_0007 (head)`；Repository、跨 saver 实例 checkpoint 恢复和 schema 检查 `3 passed in 0.38s`；Ruff 通过。
- **遇到的问题：** 首个 checkpoint 恢复测试试图编译没有 START 入口的空 graph，LangGraph 在编译期正确拒绝。
- **解决方法：** 用相同 state schema 和最小合法 graph 重新编译，再从新 saver 实例读取相同 thread checkpoint；没有绕过 graph 校验。
- **当前限制：** 当前 checkpoint 使用单 PostgreSQL 连接，适合本地 MVP；高并发池化和 checkpoint 数据保留策略不在本 Phase。
- **与下一步骤的关系：** 下一步把 Runtime 装配到 FastAPI，并验证所有 HTTP 分支和 Phase 5 RAG 兼容性。

### Step 6.4：接入 Agent API 并保留可信 RAG

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由。
- **完成日期：** 2026-07-23
- **本步骤目标：** 提供可执行和可读取的 Agent HTTP 入口，并用真实 PostgreSQL 证明知识问题仍走 Phase 5 的可信 RAG。
- **实际完成内容：** FastAPI lifespan 初始化 PostgreSQL checkpointer 和 `AgentRuntime`；新增 `POST /agent/runs`、`GET /agent/runs/{run_id}`、输入/输出 Schema 和本地 role readback 检查；默认 Fake Model Gateway 按请求 Schema 分派确定性分类或 RAG 输出；API 返回 intent、confidence、risk、missing information、简短 reasoning summary、最终响应和完整有序节点轨迹。
- **新增或修改文件：** `apps/api/main.py`、`apps/dependencies.py`、`agent_runtime/routes.py`、`schemas.py`、Agent API integration tests。
- **请求或数据流程：** HTTP request → request ID → Agent Runtime → LangGraph nodes → Agent Run/Steps + checkpoint → 可选 RAG Conversation/Message → HTTP response/readback。
- **关键代码入口：** `create_agent_run()`、`get_agent_run()`、`create_app()` lifespan、`_fake_model_response()`。
- **为什么采用当前实现：** 新 `/agent` 入口成为显式图运行入口；原 `/chat` 保持兼容，知识分支复用同一 RAG 生成、相关性、Citation 和 Conversation 持久化代码，不复制安全规则。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/integration/api/test_knowledge_documents.py -k 'agent_api' -q`。
- **测试结果：** 真实 PostgreSQL 下知识 RAG、三类 diagnosis、ticket、unsupported、低置信度澄清和 run readback/role mismatch 共 `7 passed, 38 deselected in 1.33s`。
- **当前限制：** 默认 Fake 分类只用于本地确定性演示，不代表分类准确率评估；本 Phase 未建立标注分类数据集，也未调用真实付费 Provider。
- **与下一步骤的关系：** 功能主线已接通；下一步补强 strict Schema、失败 HTTP/恢复测试和完整 regression，再执行 verification-loop。

### Step 6.5：执行 verification-loop、修复启动兼容性并完成 Phase 文档

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由。
- **完成日期：** 2026-07-23
- **本步骤目标：** 对照用户要求逐项验证状态、路由、持久化、checkpoint、失败边界、原 RAG、迁移、普通安装和真实运行，并同步最终文档。
- **实际完成内容：** 建立验收矩阵；增加 strict classification required/extra-forbid 断言；执行 migration 往返、完整 pytest、Ruff、format、compileall、pip check、Git whitespace 与安全范围扫描；普通安装当前 wheel；通过真实 FastAPI composition root 执行 diagnosis、clarification 和 high-risk escalation；更新 README、Glossary、Overview、Roadmap、Backlog、Current State 与 Phase 6 report；把旧 Backlog 的分类与 LangGraph 两阶段按本次明确指令合并为 Phase 6，后续 Tool 阶段重编号为 Phase 7。
- **新增或修改文件：** 全部 Phase 6 代码/测试文件及 `README.md`、`CONTEXT.md`、`docs/PROJECT_OVERVIEW.md`、`ROADMAP.md`、`backlog.md`、`CURRENT_STATE.md`、`phase_reports/phase_6.md`、`project_journal.md`。
- **运行与验证命令：** test DB Alembic `0007 → 0006 → 0007`；开发/测试 `alembic current`；`.venv/bin/python -m pytest -q`；Ruff lint/format；compileall；pip check；`git diff --check`；普通 `pip install . --no-build-isolation`；真实 TestClient composition-root smoke。
- **最终结果：** 全量 `156 passed in 6.38s`；Ruff `All checks passed!`；format `98 files already formatted`；compileall 成功；pip check 无损坏依赖；Git whitespace 通过；开发库与测试库均为 `20260723_0007 (head)`。
- **真实 smoke：** `VPN cannot connect` → `vpn_diagnosis`/completed；`Please help` → clarification；`Disable security controls` → unsupported/high-risk escalation；三者 `tool_results=[]`，均未执行工具或写操作。
- **发现的问题 1：** 首次全量回归 `6 failed, 150 passed`。health/error tests 使用刻意无效的数据库凭证，而 checkpoint 初始化被错误地设为应用启动前置条件。
- **解决方法 1：** checkpoint 连接/setup 失败时只禁用 Agent Runtime并记录安全 warning，应用 liveness 保持可用，数据库状态仍由 readiness 表达；专项 `6 passed` 后全量转绿。
- **发现的问题 2：** 首次普通 Python smoke 因虚拟环境仍是旧 wheel 安装而无法导入新增 Agent 模块，pytest 的 `pythonpath` 没有暴露该 packaging 状态。
- **解决方法 2：** 按 README 重新普通安装当前 wheel，再运行相同 smoke 成功。
- **发现的问题 3：** 初版把 classification metadata 放入 `tool_results`，会让没有工具调用的 Phase 产生误导。
- **解决方法 3：** 增加独立 `classification_metadata` state/response 字段，`tool_results` 保持空列表。
- **安全审查：** Agent Runtime 没有 subprocess、shell、Python/SQL 工具、动态 eval/exec、真实 Adapter 或工单写入；错误轨迹不保存 Provider 异常正文；Reasoning Summary 是受 Schema/长度约束的短路由说明，不请求私有思维过程。
- **当前限制：** 自报 role、无 tenant/subject、Fake 分类未评估、checkpoint 单连接、无真实诊断/工具/工单、真实 Provider 未 smoke；这些均已写入 Current State 和 Phase report。
- **与下一步骤的关系：** Phase 6 工程验收为 PASS，本次停止；未经用户明确确认不开始 Phase 7。

## Phase 6 总结与索引

- **Step 6.1：** LangGraph/PostgreSQL checkpoint 依赖与执行边界配置；
- **Step 6.2：** AgentState、strict classification、显式 graph nodes 与有界路由；
- **Step 6.3：** agent_runs/agent_steps、migration 0007 与 PostgreSQL checkpoint；
- **Step 6.4：** Agent API、完整节点读取与可信 RAG 兼容；
- **Step 6.5：** verification-loop、启动降级修复、普通安装、真实 smoke 和文档收尾。

最终结论：Phase 6 的状态图、六类意图、低置信度澄清、RAG 路由、诊断/工单占位、安全升级、错误/上限、checkpoint、Run/Step 持久化、API 和文档满足当前范围；未实现真实工具或写操作。建议 Commit 为 `feat(agent): add langgraph intent routing runtime`，建议 Tag 为 `phase-6-complete`。

### Step 6.6：执行 Phase 6 收尾验收与双轴代码审查

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由（收尾验收）。
- **完成日期：** 2026-07-23
- **本步骤目标：** 不以“代码可运行”替代验收，重新对照原始任务、验收标准、当前代码、测试和文档，先列出问题再修改。
- **实际完成内容：** 复核 AgentState、七个指定职责节点、六类意图、结构化分类、确定性路由、执行限制、checkpoint、Run/Step 和原 RAG 回归；检查重试副作用、失败状态一致性、超时覆盖、数据库故障映射、reasoning summary 边界、恢复状态不变量、硬编码、重复逻辑、后续功能越界和安全边界。
- **审查结论：** 发现一个 Blocking：`compose_answer` 包含 Conversation Turn 持久化，却被 graph 通用重试器自动重试，可能重复写入失败或成功 Turn。发现五个必要 Important：最终失败 Step snapshot 仍为 running；节点/总 timeout 缺少行为测试且节点 timeout 无独立错误码；checkpoint psycopg 故障未映射 503；reasoning summary 的单行边界仅靠 Prompt；恢复到 running 时未清空旧 completed_at。另有一行重复 intake 赋值。
- **不处理的 Optional：** Fake 分类关键词硬编码、checkpoint 单连接、自报 role、TypedDict `total=False`；这些属于已知本地 MVP 边界或演示适配器，本次不扩展。
- **证据入口：** `agent_runtime/runtime.py`、`state.py`、`persistence.py`、`routes.py`、`rag.py`、Phase 6 unit/integration tests、`docs/phase_reports/phase_6.md`。
- **与下一步骤的关系：** 下一步只修复上述 Blocking 与必要 Important，并为每个行为补充聚焦失败路径测试；不进入 Phase 7。

### Step 6.7：关闭重试副作用、节点预算与失败审计问题

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由（收尾修复）。
- **完成日期：** 2026-07-23
- **本步骤目标：** 修复审查发现的 Blocking 与必要 Important，不增加业务能力。
- **实际完成内容：** 将 graph retry 改为显式 allowlist，只有无写副作用的 `classify_intent` 与 `retrieve_knowledge` 可重试，`compose_answer` 不再由 graph 重试；重试 attempt 统一消耗 `max_nodes` 硬预算，LangGraph recursion limit 保留为第二道保护；最终失败状态在保存 Step 前完成；节点 timeout 使用独立 `*_timeout` code；安全日志只记录 run/node/attempt/异常类型/稳定 code，不记录异常正文；`AgentState` 改为必需字段 TypedDict；reasoning summary 强制非空、trimmed、单行；Run 恢复到 running 时清空旧 completed_at；checkpoint psycopg 故障映射安全 503。
- **失败路径测试：** 新增 compose 单次调用、重试消耗节点预算、单节点 timeout、总 timeout、最终失败 snapshot、日志不泄漏异常正文、reasoning summary 多行拒绝、恢复生命周期不变量和 checkpoint 503 测试。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/agent_runtime/test_runtime.py tests/integration/agent_runtime/test_persistence.py tests/integration/api/test_health.py -q`；Agent Runtime 聚焦 Ruff lint/format。
- **真实结果：** 首次沙箱运行 unit/API 全部通过，但 3 个 PostgreSQL tests 因沙箱禁止本机 5432 而 setup error；按权限机制重跑后 `26 passed in 1.06s`。Ruff `All checks passed!`，format `11 files already formatted`。
- **与下一步骤的关系：** Blocking 与必要 Important 已形成聚焦测试闭环；下一步运行全量回归、真实演示、安全扫描并同步最终文档。

### Step 6.8：完成收尾全量验收、实际演示与学习门槛

- **所属 Phase：** Phase 6：LangGraph Agent Runtime 与意图路由（最终收尾）。
- **完成日期：** 2026-07-23
- **本步骤目标：** 在修复后运行完整工程验证、至少一条正常和两条非成功演示路径，更新 README/Current State/Phase Report，并停止在 Phase 6。
- **实际完成内容：** 增加最后一道 reasoning 安全边界：模型仍必须返回结构化短说明，但原文不保存或展示，state/API 只使用代码基于 intent/confidence/risk 生成的固定说明；完成全量 pytest、Ruff lint/format、compileall、pip check、Git whitespace 和 Agent 范围安全扫描；用真实 FastAPI composition root、PostgreSQL Run/Step 和 checkpoint 执行三条请求；更新 README、Current State 和 Phase 6 Report。
- **运行命令：** `.venv/bin/python -m pytest -q`；收尾聚焦 pytest；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；TestClient composition-root 三场景脚本；Agent 范围 subprocess/eval/tool/secret pattern scan。
- **最终结果：** 全量 `164 passed in 6.60s`；聚焦 `27 passed in 1.07s`；Ruff `All checks passed!` 且 `98 files already formatted`；compileall 成功；pip check 无损坏依赖；Git whitespace 通过。安全扫描没有发现 subprocess、shell、eval/exec、真实 Tool Registry/Adapter 或工单写入；测试中的 fictional secret 未进入 HTTP/state/log。
- **实际演示：** 正常 `VPN cannot connect` → 200/completed/`vpn_diagnosis`，节点 intake→classify→vpn placeholder→finalize；非成功一 `Please help` → 200/needs_clarification，未检索/未调用工具；非成功二 `Disable security controls` → 200/escalated/unsupported，安全升级；三条路径 `tool_results=[]`。
- **文档与判断：** Phase 6 工程问题全部关闭，工程为 PASS；总体为 **CONDITIONAL PASS**，项目所有者需独立回答 10 道面试题并完成 30–60 分钟纯函数路由练习。建议 Commit `feat(agent): complete bounded langgraph intent runtime`；学习验收完成后建议 Tag `phase-6-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 7；下一阶段必须由项目所有者另行明确确认。

---

## Phase 7：VPN、Outlook、账号诊断工作流与只读工具

### Step 7.1：建立只读 Tool Registry 与唯一执行 Gateway

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具。
- **完成日期：** 2026-07-23
- **本步骤目标：** 定义完整 ToolDefinition，并把工具存在性、Schema、权限、timeout、有限重试、结构化结果、错误清洗和审计集中到一个 Agent 可见 seam。
- **实际完成内容：** 新增包含 name、version、description、input/output schema、required permissions、risk、side-effect、timeout 和 retry policy 的 ToolDefinition；实现只接受无副作用工具的 ToolRegistry、确定性 RolePermissionPolicy 和 ToolExecutionGateway；Gateway 对未注册、非法输入、越权、timeout、瞬时失败、永久异常和非法输出返回稳定结构化结果，异常正文不跨越接口；新增七个可配置的 Mock 只读 Adapter 及严格输入输出 Schema。
- **新增或修改文件：** `src/enterprise_it_support/tools/contracts.py`、`gateway.py`、`mock.py`、`tools/__init__.py`、`tests/unit/tools/test_gateway.py`、`tests/unit/tools/__init__.py`、`docs/project_journal.md`。
- **请求或数据流程：** Runtime 结构化请求 → Registry allowlist → Pydantic input Schema → role permission → 单次 timeout/有限 retry → Mock Adapter → output Schema → observation 或安全错误 → audit Adapter。
- **关键代码入口：** `ToolExecutionGateway.execute()`、`ToolRegistry.register()`、`ToolDefinition`、`create_mock_tool_registry()`。
- **使用的核心技术：** Pydantic strict Schema、asyncio timeout、有限 retry、依赖注入、确定性 Mock、结构化安全错误。
- **为什么采用当前实现：** Runtime 只需学习一个 Gateway interface；Registry、Adapter 和治理实现不暴露给节点或 LLM。删除 Gateway 会让校验、权限、上限、清洗和审计复杂度重新散落到所有调用方，因此该 module 具有实际深度。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/tools -q`；`.venv/bin/ruff check src/enterprise_it_support/tools tests/unit/tools`；`.venv/bin/ruff format --check src/enterprise_it_support/tools tests/unit/tools`。
- **测试结果：** Gateway/Registry 单元测试 `7 passed in 0.05s`；Ruff `All checks passed!`；6 个相关文件已格式化。
- **遇到的问题：** `tools/__init__.py` 原有 Phase 8 占位 docstring 与新 docstring 并存，导致 Ruff 把第二个字符串视为 import 前语句并报告 E402。
- **解决方法：** 保留新的 Phase 7 module docstring，删除已经失效的旧占位文本后重跑 Ruff 通过。
- **当前限制：** 审计当前只有内存 Adapter；PostgreSQL `tool_executions` 与 Agent 工作流接入留到下一步骤。
- **我需要理解的知识：** ToolDefinition 是允许调用合同而不是函数句柄；输入和输出都必须视为不可信；timeout/retry 与 Agent 节点上限是不同层级的控制；只读也仍需权限和审计。
- **与下一步骤的关系：** 下一步实现 PostgreSQL tool execution audit，使成功、拒绝和失败调用都能按 Agent Run 追溯。

### Step 7.2：持久化 tool_executions 并验证拒绝路径审计

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具。
- **完成日期：** 2026-07-23
- **本步骤目标：** 让每个逻辑工具调用的成功、校验拒绝、权限拒绝和安全失败都能通过 Agent Run 追溯。
- **实际完成内容：** 新增 `tool_executions` ORM 与 Alembic `20260723_0008`；记录 run/request/node、工具名/版本、状态、清洗后的参数、结构化 observation、风险、side-effect、稳定错误、attempts、latency 和时间；数据库约束禁止 side effect 为 true；实现 append/read Repository；migration env 显式加载模型；新增真实 PostgreSQL Gateway 审计集成测试和 schema 列检查。
- **新增或修改文件：** `src/enterprise_it_support/tools/models.py`、`persistence.py`、`migrations/versions/20260723_0008_add_tool_executions.py`、`migrations/env.py`、`tests/integration/tools/test_persistence.py`、相关 migration/Agent fixture、`docs/project_journal.md`。
- **请求或数据流程：** Gateway final result → `ToolExecutionRepository.record()` → insert `tool_executions` → `list_for_run()` 按时间和 ID 稳定读取。
- **关键代码入口：** `ToolExecutionRepository.record()`、`ToolExecutionRepository.list_for_run()`、migration `20260723_0008`。
- **使用的核心技术：** SQLAlchemy async、PostgreSQL JSONB、foreign key cascade、check constraints、Alembic、真实数据库集成测试。
- **为什么采用当前实现：** Tool audit 是独立于 Agent Step 的一等事实；一个诊断节点可能产生一个工具 observation，而 Step snapshot 负责图状态，两者不能互相替代。Repository 保持 SQL 在 tools module 内，Runtime 不直接操作数据库。
- **运行与验证命令：** `IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/python -m pytest tests/integration/tools/test_persistence.py tests/integration/knowledge/test_migrations.py tests/integration/agent_runtime/test_persistence.py -q`；相关 Ruff lint/format。
- **测试结果：** migration 成功升级到 head；PostgreSQL 审计、migration 与 Agent persistence 聚焦 `5 passed in 0.45s`；Ruff `All checks passed!`，14 个相关文件已格式化。
- **遇到的问题：** 没有出现代码失败；测试清理顺序需要先删除 `tool_executions`，再删除 Agent Run/Step，避免新外键影响隔离 fixture。
- **解决方法：** 在 Agent persistence fixture 中显式清理 tool executions，并保留数据库 cascade 作为产品级删除约束。
- **当前限制：** Agent Runtime 尚未调用 Gateway，因此现有诊断 Run 还不会产生 audit 行；下一步骤接入。
- **我需要理解的知识：** Agent Step snapshot、AgentState observation 和 ToolExecution audit 分别解决执行位置、模型上下文和工具治理追溯三个不同问题。
- **与下一步骤的关系：** 下一步替换三个 diagnosis placeholder，以显式节点调用 Gateway 并把每个 result 写回 AgentState。

### Step 7.3：将三类诊断占位替换为显式只读状态图

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具。
- **完成日期：** 2026-07-23
- **本步骤目标：** 让 VPN、Outlook 和账号 diagnosis 从占位响应变为可观察、有限、能根据 observation 分支的 LangGraph 流程。
- **实际完成内容：** 扩展 AgentState 增加 tool call count、diagnostic context 和 escalation reason；VPN 图显式覆盖设备/OS、公网、客户端、VPN 服务、事件和知识步骤；Outlook 图显式解析所有邮件、错误代码、client/Web，并检查邮件服务、账号、事件和知识步骤；账号图检查锁定、密码过期、MFA、身份系统事件和知识步骤；服务异常、已知事件、工具失败、审计失败、知识为空和工具上限都安全进入人工升级；每个 Gateway result 作为 observation 写入 `tool_results`，同时保存 `tool_executions`；Agent API 返回两类轨迹。
- **新增或修改文件：** `agent_runtime/state.py`、`runtime.py`、`schemas.py`、`routes.py`、`platform/config.py`、`apps/dependencies.py`、`apps/api/main.py`、`.env.example`、Agent Runtime/API/config tests、`docs/project_journal.md`。
- **请求或数据流程：** intent route → 诊断专属节点 → Gateway → structured observation → AgentState/checkpoint + tool audit → observation 条件边 → Mock knowledge steps、clarification 或 safe escalation → finalize。
- **关键代码入口：** `AgentRuntime._execute_tool()`、VPN/Outlook/account 专属节点、`_route_*_after_incidents()`、`ToolExecutionResponse`。
- **使用的核心技术：** LangGraph conditional edges、显式 TypedDict state、确定性文本事实解析、bounded tool count、PostgreSQL audit readback。
- **为什么采用当前实现：** 每个状态问题都有一个可见节点或 observation，不隐藏在 Prompt 中；节点只了解工具名、参数和结构化结果，治理仍完整留在 Gateway module。工具 retry 次数、工具调用上限、graph 节点预算和总 timeout 分别限制不同失控模式。
- **运行与验证命令：** Agent/tools/config 单元聚焦 pytest；`.venv/bin/python -m pytest tests/integration/api/test_knowledge_documents.py -k 'agent_api' -q`；相关 Ruff lint/format；compileall。
- **测试结果：** 工作流/Gateway/config 聚焦 `48 passed in 1.47s`；Agent API/PostgreSQL 聚焦 `7 passed, 38 deselected in 1.61s`；Ruff `All checks passed!`，23 个相关文件已格式化；compileall 成功。
- **遇到的问题：** Phase 6 的 Outlook 占位测试假设任何输入都会 completed；真实 Phase 7 流程对缺少“全部邮件/错误代码/client-Web”信息的请求正确返回 needs clarification。
- **解决方法：** 保留并测试 clarification 分支；完成路径改用包含三项事实的 Outlook 请求。原知识 RAG、ticket 和 unsupported 路由语义保持不变。
- **当前限制：** 默认 Mock 环境返回本地固定事实，不代表企业真实状态；Outlook 事实解析是确定性演示规则，不是自然语言临床级抽取；无工单写入。
- **我需要理解的知识：** observation 如何改变下一节点；为什么工具成功不等于诊断完成；为什么用户侧事实、服务 observation 和知识步骤需要分别建模。
- **与下一步骤的关系：** 下一步补齐针对三类分支、工具影响、最大调用数、工具异常和完整持久化的验收测试，再做收尾审查。

### Step 7.4：补齐 Phase 7 验收分支并完成首次全量回归

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具。
- **完成日期：** 2026-07-23
- **本步骤目标：** 覆盖用户指定的工具治理、三类诊断分支、observation 路由、最大调用次数和异常升级，不以 happy path 代替验收。
- **实际完成内容：** Gateway 测试覆盖七工具注册、未注册、参数 extra、权限不足、timeout 两次封顶、瞬时失败一次重试后成功、永久异常清洗和 audit 参数脱敏；诊断测试覆盖 VPN OS/公网/client/service/incident/knowledge、Outlook 全部邮件/error/client-Web/service/account/knowledge、账号 lock/password/MFA/incident/knowledge；增加 service outage 与 identity incident 跳过知识调用、Outlook 缺信息 clarification、最大工具调用数安全升级、Adapter exception 单次失败后升级；API 验证 state results 与 PostgreSQL tool executions 在 POST/GET readback 一致。
- **新增或修改文件：** `tests/unit/tools/test_gateway.py`、`tests/unit/agent_runtime/test_runtime.py`、`tests/integration/tools/test_persistence.py`、`tests/integration/api/test_knowledge_documents.py`、相关实现修正、`docs/project_journal.md`。
- **请求或数据流程：** 版本化测试场景 → Runtime/Gateway public interfaces → node trace + AgentState observation + tool audit → next-node assertion → final status。
- **关键代码入口：** `build_runtime()` 测试 composition、`diagnostic_gateway()`、Agent API POST/GET readback。
- **使用的核心技术：** pytest async、InMemorySaver、configurable Mock environment、真实 PostgreSQL、FastAPI TestClient。
- **为什么采用当前实现：** 测试从 Gateway 和 Runtime 的正式 interface 验证可观察结果，不调用私有 Adapter 或内部 SQL；这样未来替换 Mock 数据实现时，治理合同和状态图回归仍有效。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit -q`；Agent API/tool persistence 聚焦；`.venv/bin/python -m pytest -q`。
- **测试结果：** 全部 unit `91 passed in 1.47s`；Agent API 聚焦 `7 passed, 38 deselected in 1.61s`；首次 Phase 7 全量 `180 passed in 8.37s`。
- **遇到的问题：** 没有出现产品测试失败；修改后的完整回归一次通过。此前 Phase 6 基线在沙箱内曾因本机 5432 被阻止而失败，本步骤全量使用已批准的隔离 PostgreSQL 访问。
- **解决方法：** 保持真实数据库测试，不跳过、不改为 SQLite；环境权限与代码断言分别记录。
- **当前限制：** 仍需执行 migration 往返、静态质量门禁、真实 composition-root smoke 和最终文档同步。
- **我需要理解的知识：** “工具异常后升级”要求 Gateway 返回稳定失败且图选择 escalation，不是让 LangGraph 无限重试；“工具结果影响下一节点”需要断言后续节点缺席/出现，而不只断言 final 文本。
- **与下一步骤的关系：** 功能与失败测试已闭环；下一步执行收尾审查、migration 往返、真实演示和文档更新。

### Step 7.5：完成 migration、真实演示、质量门禁与阶段文档

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具（最终收尾）。
- **完成日期：** 2026-07-23
- **本步骤目标：** 证明 Phase 7 在真实 PostgreSQL、正式 FastAPI composition root 和普通 wheel 安装下可组合运行，并把当前事实同步到项目文档后停止。
- **实际完成内容：** test DB 执行 `0008 → 0007 → 0008`，开发库升级 0008；通过真实 composition root 分别执行 VPN、Outlook、账号请求并读取 node/tool audit；完成全量 pytest、Ruff、format、compileall、pip check、Git whitespace 和工具范围扫描；普通构建并安装当前 wheel；更新 README、Glossary、Overview、Roadmap、Current State 和 Phase 7 report；确认未开始 Phase 8。
- **新增或修改文件：** Phase 7 全部代码/测试/migration，以及 `README.md`、`CONTEXT.md`、`docs/PROJECT_OVERVIEW.md`、`ROADMAP.md`、`CURRENT_STATE.md`、`phase_reports/phase_7.md`、`project_journal.md`。
- **请求或数据流程：** ordinary wheel/composition root → POST Agent Run → PostgreSQL checkpoint/Run/Step → Gateway/Mock → tool_executions → API response/readback。
- **关键代码入口：** `create_app()`、`AgentRuntime`、`ToolExecutionGateway`、migration `20260723_0008`、`POST/GET /agent/runs`。
- **使用的核心技术：** Alembic round-trip、FastAPI TestClient、PostgreSQL/pgvector、pytest、Ruff、compileall、pip wheel/install。
- **为什么采用当前实现：** 普通安装验证新 tools package 会进入 wheel；真实 composition root 同时验证 migration、checkpointer、Repository、Gateway、Mock、状态图与 HTTP schema，避免 pytest import path 或 isolated fake 掩盖装配问题。
- **运行与验证命令：** 两环境 Alembic upgrade/current；test DB downgrade/upgrade；`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；`pip install . --no-build-isolation`；真实 composition-root 三场景脚本；工具范围 `rg` 扫描。
- **测试结果：** 最终全量 `180 passed in 8.68s`；Ruff `All checks passed!`、`108 files already formatted`；compileall 成功；pip check 无损坏依赖；Git whitespace 通过；普通 wheel 构建和安装成功；开发/测试数据库均为 `20260723_0008 (head)`。
- **真实演示结果：** VPN 200/completed，5 calls/5 executions，10 个节点；Outlook 200/completed，4 calls/4 executions，9 个节点；账号 200/completed，3 calls/3 executions，7 个节点。三类均使用 employee 本地角色和 Mock observation。
- **遇到的问题：** 根目录仍没有 `AGENTS.md`；工作区在本轮开始时已包含未提交 Phase 6 改动，因此 Git 状态同时展示 Phase 6 和 Phase 7 文件，不能把全部 dirty diff 误称为本轮独占改动。
- **解决方法：** 以代码、测试和既有 Phase 6 report 为基线增量实现，不回退、不覆盖、不自动提交用户工作；最终 Git 状态如实保留。
- **当前限制：** 全部工具为 Mock；role 自报；无真实企业 Adapter、写操作、工单、审批或 Web UI；审计数据库自身故障无法写回同一数据库。
- **我需要理解的知识：** Tool audit 与 graph trace 的组合证据；为什么 read-only 仍需 deny/audit；为什么 Agent 只能得到 observation 而不能得到 Adapter；为什么下一 Phase 的工单写入必须重新设计幂等与审批。
- **与下一步骤的关系：** Phase 7 工程结论为 PASS。本次到此停止，未经项目所有者明确确认不进入 Phase 8。

## Phase 7 总结与索引

- **Step 7.1：** ToolDefinition、Registry、Policy、Gateway 与七个 Mock tools；
- **Step 7.2：** `tool_executions`、migration 0008 与 PostgreSQL audit；
- **Step 7.3：** VPN、Outlook、账号显式状态图和 Agent API trace；
- **Step 7.4：** 参数/权限/timeout/retry/分支/上限/异常验收；
- **Step 7.5：** migration 往返、普通 wheel、真实 smoke、全量质量门禁与文档。

最终结论：Phase 7 的三类诊断、七个 Mock 只读工具、唯一 Gateway、结构化 observations、失败升级、调用上限和可追溯 audit 满足本次范围。建议 Commit 为 `feat(agent): add audited mock diagnostic tools`，建议 Tag 为 `phase-7-complete`，工程判断为 **PASS**。

### Step 7.6：收尾代码审查与必要修复

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具（收尾验收）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 对照原始范围与验收标准进行 Standards/Spec/Security 审查，只修复 Blocking 和必要 Important。
- **审查问题：** 发现一个 Blocking：非预期 Gateway 异常或诊断节点 timeout 的失败状态可能因诊断条件边只检查 `escalation_reason` 而继续运行，最终被覆盖成 completed；发现三个必要 Important：Schema 文档称 strict 但允许类型强制转换、多个输出字符串/步骤元素无上限、报告声称的 Registry/非法输出及 audit-unavailable 测试实际缺失。
- **实际修复：** 诊断条件边同时检查 `error` 与 `escalation_reason`；`_execute_tool()` 清洗非预期 Gateway 异常并升级；Mock Schema 启用 strict mode，对枚举做显式字符串解析并补齐字符串边界；新增重复/side-effect 注册、非法强制转换输出、超限知识步骤、审计不可用、晚发 Gateway 异常和诊断节点 timeout 回归。
- **未处理 Optional：** Runtime 拆分、graph registration 去重和单独 Outlook Web parser 测试；这些不影响本阶段安全与验收。
- **运行命令：** `.venv/bin/python -m pytest tests/unit/tools/test_gateway.py tests/unit/agent_runtime/test_runtime.py -q`；相关 Ruff lint/format。
- **结果：** 聚焦 `39 passed in 1.47s`；Ruff `All checks passed!`；4 个文件格式检查通过。

### Step 7.7：收尾全量验证、真实失败演示与学习门禁

- **所属 Phase：** Phase 7：VPN、Outlook、账号诊断工作流与只读工具（最终验收）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 在修复后完成全量 PostgreSQL 回归、Ruff 和一正常两失败的正式 composition-root 演示，更新阶段文档并停止。
- **环境事实：** 首次全量在沙箱中因禁止连接 5432 出现 setup errors；允许本机连接后发现 Docker daemon 未运行，启动 Docker Desktop 与 `docker compose up -d db` 后容器 healthy。环境恢复后原命令全量通过，未跳过数据库测试或改用 SQLite。
- **运行命令：** `.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；`git diff --check`；`.venv/bin/python /private/tmp/phase7_closeout_demo.py`（临时脚本执行后已删除）。
- **最终结果：** 全量 `186 passed in 8.53s`；Ruff `All checks passed!`；`108 files already formatted`；Git whitespace 通过。
- **真实演示：** 正常 VPN 为 200/completed、5 calls/5 succeeded executions；`guest` 权限不足为 200/escalated、1 permission_denied execution；`agent_max_tool_calls=2` 为 200/escalated、2 succeeded executions 后停止。三条均经过正式 FastAPI composition root、PostgreSQL checkpoint/Run/Step 与 tool audit。
- **安全结论：** 未发现真实企业 Adapter、写操作、Shell/Python/SQL 工具或任意函数执行；自报 `user_role` 与数据治理仍是明确的生产前限制，本阶段不扩展认证。
- **阶段判断：** 工程 **PASS**；总体 **CONDITIONAL PASS**，项目所有者需独立回答本阶段 10 道面试题并完成 30–60 分钟练习。建议 Commit `fix(agent): close phase 7 diagnostic safety gaps`；学习验收完成后建议 Tag `phase-7-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 8。

---

## Phase 8：本地工单、低风险写操作、用户确认与审计

### Step 8.1：建立本地 Service Desk schema 与写工具审计关联

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计。
- **完成日期：** 2026-07-24
- **本步骤目标：** 在不连接 ServiceNow/Jira 的前提下，为工单、评论、确认、领域审计和既有工具审计建立真实 PostgreSQL 数据边界。
- **实际完成内容：** 新增 `tickets`、`ticket_comments`、`pending_confirmations` 和 `audit_events` ORM；创建 Alembic `20260724_0009`；Ticket 包含编号、标题、描述、类别、优先级、状态、请求人、受理人、Conversation/Agent Run 来源、诊断摘要和创建幂等键；Comment 包含作者、正文和唯一幂等键；Pending Confirmation 保存 R1/R3、动作参数、脱敏摘要、影响、请求指纹、执行结果和生命周期；Audit Event 保存 actor/action/target/parameters summary/policy decision/execution result/request ID；既有 `tool_executions` 增加 actor、pending confirmation 和 idempotency 关联，并允许受控 side effect。
- **新增或修改文件：** `src/enterprise_it_support/service_desk/__init__.py`、`service_desk/models.py`、`migrations/versions/20260724_0009_add_local_service_desk.py`、`migrations/env.py`、`tools/models.py`、`tests/integration/knowledge/test_migrations.py`、`docs/project_journal.md`。
- **请求或数据流程：** Alembic 0008 → 创建 ticket sequence/四张新表 → 演进 `tool_executions` → PostgreSQL constraints/indexes/FKs → SQLAlchemy inspector 验证五个实体和全部字段。
- **关键代码入口：** migration `20260724_0009`、`Ticket`、`TicketComment`、`PendingConfirmation`、`AuditEvent`。
- **使用的核心技术：** SQLAlchemy 2、Alembic、PostgreSQL UUID/JSONB/sequence、unique/check/foreign-key constraints、真实数据库集成测试。
- **为什么采用当前实现：** 工单和评论分别以数据库唯一幂等键提供最终重复保护；pending confirmation 与实际 tool execution 分离，防止“提出动作”等同于“已经执行”；领域 audit 与工具 audit 分别记录政策/业务事件和一次受控工具调用，不能互相替代。
- **运行与验证命令：** 修改前全量 `.venv/bin/python -m pytest -q`；schema 红灯测试；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；schema 绿灯测试。
- **测试结果：** 修改前基线 `186 passed in 9.35s`；新增 schema 测试先以 `NoSuchTableError: tickets` 红灯；migration 应用后目标测试 `1 passed in 0.22s`。
- **遇到的问题：** 根目录仍无 `AGENTS.md`；Git 基线只提交到 Phase 5，Phase 6–7 是已有未提交改动。
- **解决方法：** 以当前代码、测试、Phase 7 report 和用户明确 Phase 8 规格为事实来源；不回退或覆盖既有工作区；新 migration 只从 0008 前向演进。
- **当前限制：** 本步骤只建立 schema；Repository、Tool Gateway 确认重校验、API 和行为测试尚未实现。
- **我需要理解的知识：** 为什么 application-level 幂等检查之外还需要数据库唯一约束；为什么 confirmation、tool execution 和 audit event 是三种不同事实。
- **与下一步骤的关系：** 下一步实现 Ticket/Confirmation/Audit Repository 和 R0/R1/R3 工具合同，先覆盖确认前不可执行、重复键和权限行为。

### Step 8.2：实现 R0/R1/R3 工具策略、确认重校验与幂等 Repository

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计。
- **完成日期：** 2026-07-24
- **本步骤目标：** 让本地工单写操作只能在已持久化确认后通过唯一 Tool Gateway 执行，并由 PostgreSQL 保证重复请求不产生第二份业务结果。
- **实际完成内容：** 新增 Ticket、Pending Confirmation 和 Audit Event Repository；使用 transaction advisory lock 与唯一约束保护 Ticket/Comment/Confirmation 幂等；新增 `get_ticket_status` R0、`create_ticket` R1、`add_ticket_comment` R1 三个严格 Schema 工具；Tool Registry 从“拒绝全部 side effect”演进为“R0 必须只读、只有 R1 可执行写入、R3 不注册 Adapter”；Gateway 增加 proposal validation 和 confirmation validator，执行前重新校验 confirmation ID、actor、role、action、参数、状态和 idempotency key；新增 R3 approval-only 流程；工具审计对 description/comment/diagnosis 只保存长度和 `[TEXT REDACTED]`，对 password/token/secret/api_key 直接脱敏。
- **新增或修改文件：** `service_desk/domain.py`、`persistence.py`、`tools.py`、`service.py`、`tools/contracts.py`、`tools/gateway.py`、`tools/persistence.py`、`tools/mock.py`、`tests/integration/service_desk/test_service.py`、`docs/project_journal.md`。
- **请求或数据流程：** R1 proposal → Gateway schema/role validation → pending confirmation + sanitized audit → user confirm → row lock/ownership claim → Gateway 完整重校验 → PostgreSQL Adapter → tool execution audit → pending completed/failed → sanitized domain audit；R0 status → Gateway 自动执行 → resource ownership check → audit。
- **关键代码入口：** `ServiceDeskService.propose_create_ticket()`、`confirm()`、`get_ticket_status()`、`PendingConfirmationRepository.validate_for_execution()`、`ToolExecutionGateway.validate_action()`/`execute()`、`ServiceDeskToolAdapter`。
- **使用的核心技术：** PostgreSQL advisory lock、row lock、unique constraints、SQLAlchemy async transaction、Pydantic strict Schema、确定性 RBAC + 资源归属、SHA-256 request fingerprint。
- **为什么采用当前实现：** proposal 不是 execution；confirmation row lock 防止两个确认同时抢占，Ticket/Comment 幂等键是最终防线；Gateway 在执行时重新验证而不是信任 proposal 时的旧决定；R3 没有可调用 Adapter，因此即使用户尝试确认也不会执行密码或权限修改。
- **运行与验证命令：** 新 Service Desk 测试红灯；修复 UUID strict 边界；`.venv/bin/python -m pytest tests/integration/service_desk/test_service.py -q`；Phase 7/8 Gateway/Tool audit 聚焦；相关 Ruff lint/format。
- **测试结果：** 初始 collection 因 `service_desk.persistence` 不存在红灯；首轮实现后发现 strict UUID 字符串边界并修复；Service Desk `4 passed`；Phase 7/8 Gateway、工具审计和 Service Desk 合并 `15 passed in 0.47s`；Ruff `All checks passed!`，18 files formatted。
- **遇到的问题：** 第一次确认安全失败为 `tool_execution_failed`，数据库 audit 证明参数已正确脱敏；根因是 strict output Schema 不接受序列化 UUID 字符串。
- **解决方法：** 仅对 UUID JSON 边界显式允许字符串解析，保留其它 strict 字段；没有放宽整个 Schema，也没有暴露 Adapter exception。
- **当前限制：** 当前角色/actor 仍由本地请求自报，不是生产认证；R3 只是审批记录，没有审批执行器；API 和 Agent 自动 proposal 尚未接入。
- **我需要理解的知识：** 乐观应用检查、advisory lock、unique constraint 和 idempotent replay 各防止哪一种重复；为什么资源归属不能只靠 role permission；为什么审计摘要不能复制完整写参数。
- **与下一步骤的关系：** 下一步新增四个指定 API，并把直接工单请求及失败/升级诊断转换为完整 create-ticket proposal。

### Step 8.3：接入 Agent proposal/confirm、Ticket 与 Audit API

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计。
- **完成日期：** 2026-07-24
- **本步骤目标：** 通过用户指定的四个 HTTP seam 暴露“Agent 建议 → 用户确认 → Gateway 执行 → 结果读取”，并保留既有 `/agent/runs`。
- **实际完成内容：** 新增 `POST /agent/respond`、`POST /agent/confirm`、`GET /tickets/{ticket_number}`、`GET /audit/events`；respond 先执行原 LangGraph，再根据直接 ticket intent、诊断 escalated/failed、显式评论目标或 R3 关键词生成 pending/approval，不执行写入；confirm 对 lifecycle/ownership/error 做稳定 HTTP 映射；Ticket GET 自动调用 R0 tool；Audit GET 限制为本地 `it_support`/`project_maintainer` 且使用 limit/offset；composition root 组装 Ticket/Confirmation/Audit Repository、合并 7 个诊断工具与 3 个 Service Desk 工具，并注入 confirmation validator；旧 Agent Run 响应映射成为可复用公共函数但原 API 不变。
- **新增或修改文件：** `service_desk/schemas.py`、`service_desk/routes.py`、`apps/api/main.py`、`apps/dependencies.py`、`agent_runtime/routes.py`、`tools/mock.py`、`service_desk/tools.py`、`tests/integration/api/test_service_desk.py`、`docs/project_journal.md`。
- **请求或数据流程：** `POST /agent/respond` → Agent Run/Steps/tools → deterministic action planner → R1 pending 或 R3 approval → response；`POST /agent/confirm` → claim/revalidate/Gateway/Adapter/audit → result；Ticket GET → R0 Gateway → authorized ticket；Audit GET → role gate → bounded page。
- **关键代码入口：** `respond()`、`confirm()`、`get_ticket()`、`list_audit_events()`、`_plan_action()`、`create_app()`。
- **使用的核心技术：** FastAPI APIRouter、Pydantic bounded schemas、composition root、existing LangGraph Runtime、PostgreSQL checkpointer/Run/Step/tool audit。
- **为什么采用当前实现：** 新 Agent endpoint 复用原 Runtime 而不重新实现分类或诊断；action planner 只消费已持久化 run 事实，由代码决定 R1/R3；完整诊断通过 summary + source Agent Run ID 关联，避免把全部 trace 复制到 Ticket 表。
- **运行与验证命令：** API 测试先得到两个 404 红灯；实现后 `tests/integration/api/test_service_desk.py`；旧 Agent API 聚焦；Phase 7/8 Gateway/Service Desk/API 聚焦；相关 Ruff lint/format。
- **测试结果：** 新 API `2 passed in 0.92s`；旧 Agent API `7 passed, 38 deselected in 1.47s`；Phase 7/8 聚焦 `17 passed in 1.05s`；相关 Ruff `All checks passed!`。
- **遇到的问题：** 新 Ticket GET 需要返回 source Agent Run/Conversation 与 description，初版 R0 output 只有状态摘要。
- **解决方法：** 在 authorized Tool output 中补齐 Ticket 必需字段和来源关联；audit 仍不复制这些完整敏感正文。
- **当前限制：** 高风险识别是本地确定性 allowlist，不是通用审批引擎；API 身份仍自报；尚需补齐 HTTP 评论/R3、失败注入、重复并发和最终安全/全量验收。
- **我需要理解的知识：** 为什么 action planner 属于确定性 Policy 邻近层，而不是让 LLM 决定授权；为什么旧 API 兼容比替换更安全；为什么列表 API 必须有界。
- **与下一步骤的关系：** 下一步扩展验收测试，重点覆盖未确认、权限不足、R3、工具失败、审计字段完整/脱敏和重复 confirm。

### Step 8.4：补齐权限、失败、R3、脱敏和诊断升级验收

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计。
- **完成日期：** 2026-07-24
- **本步骤目标：** 不以单一 happy path 代替验收，覆盖用户指定的确认、重复、权限、审计、敏感数据、工具失败和诊断失败路径。
- **实际完成内容：** 增加同一 idempotency key 同参数 replay/异参数 conflict；确认前 Ticket/Comment 表保持空；重复 confirm 只返回同一 Ticket；employee 只能访问自己的 Ticket/Confirmation，guest 不能准备 R1；R3 password/permission request 只创建 approval 且 confirm 返回 409；注入抛出虚构 secret 的写 Adapter，确认 pending 变 failed、ToolExecution 保存稳定 error、Ticket 为 0；Audit Event 必需字段逐项断言；ToolExecution 断言 actor/confirmation/idempotency/risk/side-effect 关联；Gateway 对 input 和 output audit 副本递归摘要 title/description/comment/diagnosis，Credential-shaped string 额外脱敏；`agent_max_tool_calls=1` 的正式 composition root 证明诊断升级后自动生成 create-ticket proposal。
- **新增或修改文件：** `tests/integration/service_desk/test_service.py`、`tests/integration/api/test_service_desk.py`、`tools/gateway.py`、`service_desk/service.py`、`service_desk/tools.py`、`docs/project_journal.md`。
- **请求或数据流程：** failure injection → user confirms → Gateway revalidation → Adapter raises → sanitized failed ToolExecution → pending failed → failed Audit Event → no Ticket；diagnosis tool limit → Agent escalated → action planner → R1 pending → no write until confirm。
- **关键代码入口：** `_sanitize_json()`、`ServiceDeskService.confirm()`/`_propose_r1()`、`ToolExecutionGateway._record()`、Phase 8 HTTP/Service integration tests。
- **使用的核心技术：** boundary failure injection、public HTTP/Gateway seams、真实 PostgreSQL assertions、recursive audit redaction、stable error mapping。
- **为什么采用当前实现：** 工具返回给授权用户的业务结果保持完整，但写入 audit 的副本必须最小化；被拒绝的 proposal/confirm 仍是安全相关事实，需要领域审计；Adapter exception 正文永远不跨越 Gateway。
- **运行与验证命令：** Phase 8 Service/API/Gateway/tool audit 聚焦 pytest；`.venv/bin/python -m pytest -q`。
- **测试结果：** 扩展聚焦 `19 passed in 1.43s`；首轮完整回归 `194 passed in 9.10s`。
- **遇到的问题：** 安全追踪发现原 ToolExecution audit 会原样保存 output observation，即使 input 已脱敏，也可能复制 Ticket title/diagnosis/description。
- **解决方法：** Gateway 构造仅用于 persistence 的 sanitized result 副本，调用方仍获得原始已授权结果；增加 secret-in-title/description/diagnosis 与 failing exception 回归。
- **当前限制：** 文本脱敏不能识别任意编码或混淆秘密，首要规则仍是不得把凭证提交为工单内容；actor/role 仍是本地演示自报身份。
- **我需要理解的知识：** input redaction 为什么不代表 output audit 安全；业务 response 与 audit projection 为什么应使用不同最小化视图；失败路径为什么也必须产生可解释但不泄密的记录。
- **与下一步骤的关系：** 功能与指定失败路径已闭环；下一步执行 migration 往返、全量静态门禁、正式 smoke、安全范围扫描和文档同步。

### Step 8.5：完成原子审计修正、migration 往返、安装态 smoke 与阶段收尾

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计（最终验收）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 对照原始范围证明写操作、确认、幂等、审计和失败边界在真实 PostgreSQL 与正式 composition root 下可组合运行，并同步最终文档后停止。
- **实际完成内容：** 修正成功 Ticket/Comment 与成功 `audit_events`、`tool_executions` 的事务边界，避免业务已提交而成功审计后写失败；重复 `/agent/respond` 使用相同 material fingerprint 返回原 pending；test DB 完成 `0009 → 0008 → 0009`，开发库与测试库确认位于 0009 head；重新构建并普通安装当前 wheel；通过正式 FastAPI composition root 执行 R1 proposal、越权确认、正确确认、重复确认、R0 Ticket GET、R3 approval-only 和 Audit GET；更新 README、Glossary、Overview、Roadmap、Architecture、Backlog、Current State 与 Phase 8 report。
- **新增或修改文件：** Phase 8 Service Desk package、migration 0009、Tool Gateway/审计演进、四个 API、Phase 8 integration tests，以及 `README.md`、`CONTEXT.md`、`docs/PROJECT_OVERVIEW.md`、`docs/ROADMAP.md`、`docs/CURRENT_STATE.md`、`docs/backlog.md`、`docs/architecture/mvp_architecture.md`、`docs/phase_reports/phase_8.md`、`docs/project_journal.md`。
- **请求或数据流程：** installed wheel/composition root → Agent Run → R1 pending → wrong actor deny → original actor confirm → Gateway execution-time revalidation → atomic Ticket/tool/domain audit → duplicate confirm replay；R3 request → approval-required → confirm conflict/no Adapter。
- **关键代码入口：** `create_app()`、`ServiceDeskService`、`ServiceDeskToolAdapter`、`ToolExecutionGateway`、migration `20260724_0009`、四个 Phase 8 HTTP routes。
- **运行与验证命令：** test DB Alembic `0009 → 0008 → 0009`；开发/测试 `alembic current`；`.venv/bin/python -m pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；`.venv/bin/python -m pip install --no-build-isolation .`；安装态 TestClient composition-root smoke；ServiceNow/Jira/subprocess/shell/eval/exec 与 credential-shaped 字段范围扫描。
- **最终测试结果：** 全量 `195 passed in 9.20s`；Ruff `All checks passed!`、`120 files already formatted`；compileall 成功；pip check 无损坏依赖；Git whitespace 通过；普通 wheel 构建和安装成功。
- **真实 smoke：** proposal 200 且 pending；错误 actor confirm 403；正确 confirm 200；重复 confirm 200 且 `same_ticket=True`；Ticket GET 200；R3 为 approval-required 且 confirm 409；Audit GET 200，返回 9 个相关事件。
- **安全结论：** 范围扫描未发现 ServiceNow/Jira、subprocess、shell、系统命令、动态 eval/exec 或真实账号修改 Adapter；测试中的 password/token/secret 只用于验证脱敏。R3 没有 Registry Adapter；Ticket/Comment 成功行与两类成功审计同事务提交。
- **遇到的问题：** 最终格式门禁发现 `service_desk/service.py` 有一个纯格式偏差；此外审查确认成功业务写入若与后续工具审计分成两个事务，会存在审计缺口。
- **解决方法：** 使用 Ruff 格式化单个文件；把成功业务写入、领域审计和最小工具审计放入同一 Repository transaction，Gateway 后续 record 使用 execution ID 幂等 no-op，并增加 audit-store failure 回归。
- **当前限制：** actor/role 仍由本地请求自报；R3 没有审批工作流或执行器；pending 参数没有生产级保留/加密策略；文本脱敏不是 DLP；单 PostgreSQL 整体故障无法审计自身；没有外部工单平台、Web UI 或 Phase 9 评估。
- **阶段判断：** Phase 8 工程 **PASS**。建议 Commit `feat(service-desk): add confirmed idempotent local tickets`，建议 Tag `phase-8-complete`。
- **停止条件：** 本次到此停止，未经项目所有者明确确认不进入 Phase 9。

### Step 8.6：收尾独立审查与 Blocking/Important 修复

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计（收尾验收）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 不沿用既有 PASS 结论，对照原始任务、Backlog 验收和安全边界独立检查，只修复 Blocking 与必要 Important。
- **审查发现：** 一个 Blocking：R1/R3 pending confirmation 与 proposal audit 分属两个事务，audit 失败会留下无 proposal audit 的 pending；四个实现 Important：R3 idempotent replay 未校验 actor/role、R0 tool audit 故障会泄漏为未处理 500、Audit API 重复硬编码角色、Ticket GET 依赖错误字符串模糊匹配；五个证据 Important：缺少 Gateway 无 confirmation 绕过测试、proposal audit 失败回滚、跨 actor R3 隔离、权限修改 R3 与 audit `created_at` 断言。
- **实际修复：** `PendingConfirmationRepository.create()` 在同一 PostgreSQL 事务内创建/复用 pending 并追加 proposal audit，任何 audit constraint/commit 失败都会回滚新 pending；idempotent replay 同时绑定 actor、role、risk 与 material fingerprint；`ServiceDeskExecutionError` 暴露稳定内部 code，R0 捕获 `ToolAuditUnavailableError` 并返回安全服务错误；Ticket API 按精确 error code 映射，Audit API 复用 `service_desk_permissions()`；补齐上述五类 PostgreSQL/API 回归。
- **未处理 Optional：** Service Desk 模块进一步拆分、confirmation lease/recovery、Ticket 评论分页、通用审批引擎和可信认证；这些不属于本阶段原始范围。
- **红灯命令与结果：** `.venv/bin/pytest tests/integration/service_desk/test_service.py tests/integration/api/test_service_desk.py -q` → `3 failed, 9 passed in 1.98s`；失败分别证明跨 actor R3 未隔离、proposal audit 失败后 pending 未回滚、R0 audit store 异常未转换。
- **绿灯命令与结果：** 同一聚焦命令加相关 Ruff → `12 passed in 1.81s`，Ruff `All checks passed!`。
- **安全边界：** 修复没有增加外部 Adapter、R3 执行、Shell/Python/SQL 工具或 Phase 9 功能；可信身份和 tenant 仍是明确阶段外限制。
- **与下一步骤的关系：** Blocking 与必要 Important 已形成聚焦回归；下一步执行完整回归、Ruff、migration/安装态检查和一正常两失败的正式演示，再同步学习门禁与最终结论。

### Step 8.7：完成全量验证、正式演示与学习门禁

- **所属 Phase：** Phase 8：本地工单、低风险写操作、用户确认与审计（最终收尾）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 在审查修复后运行全部相关与完整回归、Ruff、migration 往返和一正常两失败的安装态演示，并给出学习验收与阶段结论。
- **运行命令：** Phase 8/Tool Gateway/migration 聚焦 pytest；`.venv/bin/pytest -q`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；test DB `0009 → 0008 → 0009`；开发/测试 `alembic current`；普通 `pip install --no-build-isolation .`；安装态 TestClient composition-root demo。
- **最终结果：** 相关 `24 passed in 1.78s`；全量 `198 passed in 10.05s`；Ruff `All checks passed!`、`120 files already formatted`；compileall、pip check、Git whitespace 通过；普通 wheel build/install 成功；开发/测试数据库均为 `20260724_0009 (head)`。
- **正常演示：** `agent_max_tool_calls=1` 的 VPN 请求得到 run escalated、R1 pending；原 actor confirm 200；Ticket GET 200，diagnosis summary 为 537 chars；重复 confirm 200 且返回相同 ticket。
- **失败演示一：** 其他 actor 确认同一 pending → 403 `confirmation_access_denied`，没有执行写入。
- **失败演示二：** `Grant access...` → `modify_permissions` R3 approval-required；confirm → 409 `confirmation_not_executable`，没有 R3 Adapter。
- **审计演示：** support Audit GET 200，返回 7 个本次相关 policy/execution events。
- **文档同步：** README、Current State、Roadmap 和 Phase 8 report 已更新为修复后能力、真实命令/结果、验收矩阵、设计差异、学习数据流、五个概念、十道问题、独立练习和三个面试薄弱点。
- **阶段判断：** 工程无剩余 Blocking/必要 Important；总体 **CONDITIONAL PASS**，项目所有者需独立回答 10 道 Phase 8 面试题并完成 30–60 分钟练习。
- **建议版本：** Commit `fix(service-desk): close phase 8 confirmation audit gaps`；学习验收通过后建议 Tag `phase-8-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 9。

---

## Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批

### Step 9.1：建立 RBAC、R0–R4 Policy 与审批持久化基线

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批。
- **完成日期：** 2026-07-24
- **本步骤目标：** 在 Phase 8 的 R3 approval-only 占位之上建立可执行的本地治理数据模型，同时保持真实身份系统和真实权限修改在范围外。
- **接手事实：** 根目录没有 `AGENTS.md`；`main@b882da7` 之后的 Phase 6–8 仍是未提交工作区改动；旧 Backlog 把 Phase 9 定义为离线评估，但本次项目所有者明确将 Phase 9 改为 RBAC、风险策略和模拟审批，因此以本次指令为当前合同并把评估留待后续重新编号。
- **实际完成内容：** 新增 `users`、`roles`、`permissions`、`user_roles`、必要的 `role_permissions`、`approval_requests` 和 `approval_decisions`；migration 内提供 employee/helpdesk/engineer/admin/approver 五个本地角色及五个明确 demo identity；新增 R0–R4、五种唯一 Policy 输出、审批生命周期和数据库约束；Policy Engine 只使用确定性用户/角色/权限/动作/工具/目标/风险/上下文，R4 无条件拒绝，R3 缺少业务理由返回 `need_more_context`，完整 R3 返回 `require_approval`；Agent Run schema 为后续 `waiting_approval` 状态预留约束。
- **新增或修改文件：** `governance/domain.py`、`models.py`、`policy.py`、`persistence.py`、`service.py`、migration `20260724_0010`、Alembic env、Agent/Audit model constraints、Policy unit tests、migration schema test。
- **关键设计：** Pending Confirmation 继续表达原请求者对 R1 的确认；Approval Request 表达 R3 授权请求；Approval Decision 是一个请求最多一条的不可变人工决定。审批 API 后续只接收本地 actor ID，实际角色和权限从 PostgreSQL RBAC 解析，不信任调用方自报 approver 角色。
- **运行与验证命令：** `.venv/bin/pytest tests/unit/governance/test_policy.py -q`；相关 Ruff check/format；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/pytest tests/integration/knowledge/test_migrations.py -q`。
- **真实结果：** Policy unit `10 passed in 0.01s`；migration schema `1 passed in 0.26s`；测试库成功升级到 `20260724_0010`。
- **遇到的问题：** 首轮 Policy test 使用 pytest 保留参数名 `request` 导致 collection error；Ruff 同时发现 import 顺序和全角分号。
- **解决方法：** 改为 `policy_input` 并机械应用 Ruff 修复/格式化；没有放宽任何 Policy 或数据库约束。
- **当前限制：** 尚未接入 Agent interrupt/resume 和审批 HTTP API；demo identity 只是本地模拟，不是 SSO、Entra ID、tenant 或可信认证。
- **与下一步骤的关系：** 下一步把“申请加入财务系统管理员组”接入现有 LangGraph，在独立节点创建 Approval Request，随后 interrupt；恢复时只重跑等待节点，不重跑已经完成的 intake、policy 和 approval creation。

### Step 9.2：实现 Agent interrupt、审批 API 与原 Run 恢复

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批。
- **完成日期：** 2026-07-24
- **本步骤目标：** 让“申请加入财务系统管理员组”在业务理由完整时创建 Approval Request 并暂停，在 RBAC approver 决策后恢复同一 Agent Run，且不重复已完成节点。
- **实际完成内容：** Agent State 增加治理动作、R3、Policy 决定、业务理由、Approval Request ID、Decision 和模拟结果；`intake` 用确定性短语识别指定演示请求；Policy node 在 PostgreSQL 解析本地 user/role/permission；缺少理由返回 `need_more_context`；完整请求创建 Approval Request 并进入 `waiting_approval`；独立 `await_human_approval` 节点使用 LangGraph `interrupt()`；批准/拒绝 API 以 `Command(resume=...)` 恢复同一 thread/run；批准只写 `simulated_success` 和 `external_system_modified=false`，拒绝安全结束；新增 GET pending、POST approve、POST reject，审批调用方不提交 role，Repository 根据 actor ID 解析 RBAC 并用 row lock + unique decision 阻止重复审批和 self-approval。
- **API 合同：** `GET /approvals/pending?actor_id=...&limit=...&offset=...`；`POST /approvals/{id}/approve`；`POST /approvals/{id}/reject`。决定 body 只包含本地 `actor_id` 和可选有界 rationale；批准/拒绝响应同时返回 Approval 与恢复后的 Agent Run。
- **checkpoint 证据：** 创建审批和等待审批是两个独立节点；首次 run 的持久化步骤只有 `intake`、`evaluate_governance_policy`、`create_approval_request`；恢复后追加 `await_human_approval`、批准或拒绝节点、`finalize`。集成测试逐项断言前三个节点各只有一次。
- **运行与验证命令：** Governance API 首轮/修复后 pytest；Phase 9 + Agent Runtime + Service Desk + Tool + migration 相关回归；全仓 Ruff check/format check。
- **真实结果：** 首轮 approval workflow `2 failed in 0.90s`，修复 actor context 后仍 `2 failed in 1.66s`；最终 workflow `2 passed in 0.97s`；受影响相关回归 `70 passed in 3.71s`；Ruff lint/format 通过。
- **遇到的问题一：** 原 `_intake()` 把完整 `user_context` 重建为只有 role，导致 actor/idempotency 在 checkpoint 前丢失，Policy 错误返回 `need_more_context`。
- **解决方法一：** intake 规范化 role 时保留其余受控 context，并用真实 API 状态与数据库 JSON 只读查询定位和验证。
- **遇到的问题二：** LangGraph interrupt 的 `ainvoke()` 结果包含框架控制字段 `__interrupt__`，其中 `Interrupt` 对象不能写入 Agent Run JSONB。
- **解决方法二：** 增加明确的 graph-values → AgentState 投影，只保存 AgentState allowlist 字段；LangGraph 控制元数据继续由 checkpoint saver 管理。
- **当前限制：** 决策提交和 LangGraph resume 跨两个事务；正常路径已验证，若进程恰好在 decision commit 后、resume 前崩溃，当前没有独立 reconciliation worker。真实 SSO、通知、多级审批和真实目录写入仍不在本 Phase。
- **与下一步骤的关系：** 下一步补充独立 Repository/HTTP 边界复核，执行 migration 往返、全量回归、安装态 composition smoke 和安全范围扫描，再同步 Phase 9 当前状态与报告。

### Step 9.3：完成 migration 往返、全量验收、安装态 smoke 与文档收尾

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批（最终验收）。
- **完成日期：** 2026-07-24
- **本步骤目标：** 对照全部 Phase 9 要求证明治理模型、Policy、审批权限、checkpoint 恢复、审计和模拟执行在真实 PostgreSQL 与正式 composition root 中可组合运行，并同步文档后停止。
- **验收结果：** 普通 employee 不能执行或审批 R3；approver 可以批准/拒绝；非 approver 为 403；拒绝恢复后安全完成且无模拟结果；批准恢复后 Approval executed、Run completed、模拟成功；重复审批为 409；恢复节点序列证明已完成节点不重复；R4 unit 无条件 deny；模型没有参与最终授权。
- **运行与验证命令：** `.venv/bin/pytest -q`；Phase 9/Agent/Service Desk/Tool/migration 相关 pytest；test DB Alembic `0010 → 0009 → 0010`；development/test `alembic current`；`.venv/bin/ruff check .`；`.venv/bin/ruff format --check .`；compileall；pip check；`git diff --check`；普通 `pip install --no-build-isolation .`；安装态 TestClient approval smoke；治理源码的外部系统、命令执行和 credential pattern 扫描。
- **最终真实结果：** 全量 `210 passed in 11.26s`；相关回归 `70 passed in 3.71s`；Ruff `All checks passed!`、`132 files already formatted`；compileall、pip check、Git whitespace 通过；普通 wheel 构建/安装成功；开发库与测试库均为 `20260724_0010 (head)`。
- **安装态 smoke：** proposal 200/`waiting_approval`/`require_approval`；employee approve 403；approver approve 200；同一 run 变 completed；Approval 变 executed；结果为 `simulated_success` 且 `external_system_modified=false`；节点严格为 intake、Policy、create、await、simulate、finalize。
- **安全扫描：** Governance/migration/tests 范围未发现 subprocess、Shell、动态 eval/exec、ServiceNow/Jira、Entra/LDAP/Microsoft Graph、HTTP 外部调用或凭证；唯一字符串命中为表名 `approval_requests` 的 `requests` 子串。
- **文档同步：** Glossary 明确分离 Confirmation、Approval Request、Policy Decision 与 Approval Decision；Overview、Roadmap、Backlog、Architecture、README、Current State 与 Phase 9 report 已同步；旧离线评估顺延为 Phase 10，后续 UI/安全/Docker 相应顺延。
- **已知限制：** actor ID 仍是本地 demo identity selector；没有真实认证/tenant；Decision commit 与 graph resume 跨两个事务且没有 reconciliation worker；没有通知、多级审批或真实权限 Adapter；高风险识别只覆盖指定演示场景。
- **阶段判断：** Phase 9 工程 **PASS**，没有剩余 Blocking 或必要 Important。
- **建议版本：** Commit `feat(governance): add rbac and human approval resume`；Tag `phase-9-complete`。
- **停止条件：** 本次到此停止，未经项目所有者明确确认不进入 Phase 10。

### Step 9.4：收尾独立审查与恢复一致性问题确认

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批（收尾验收）。
- **完成日期：** 2026-08-01
- **本步骤目标：** 不沿用既有 PASS 结论，对照原始任务、Backlog、代码、数据库测试和安全边界独立复核，并在修改前列出 Blocking/Important。
- **审查边界：** 根目录仍无 `AGENTS.md`；以 `main@b882da7` 加全部未跟踪文件为固定审查边界，保留 Phase 6–8 既有未提交改动。
- **审查发现：** 一个 Blocking：Approval Decision 先提交、Runtime 后获取并恢复，任一中间故障都会使请求不再 pending，而重试恒定返回 409，原 Run 可永久停在 `waiting_approval`；三个必要 Important：缺少恢复完成标记、被拒绝的审批权限尝试不写治理审计、缺少 decision-commit/resume-failure 恢复与完整批准审计回归。
- **文档冲突：** README、CURRENT_STATE 和 Phase 9 report 一边判定 PASS/无必要 Important，一边明确承认 decision/resume 崩溃窗口；本轮将在修复并重新验证前撤销该无条件结论。
- **范围判断：** 没有发现真实 IAM Adapter、命令执行、外部平台或 Phase 10 功能；本地 actor selector、固定 demo seed 和指定短语是已声明的演示边界，本轮不扩展为认证、多级审批或通用 IAM。
- **修改前验证：** 聚焦 Policy/PostgreSQL/migration 命令首次因 Docker 未启动失败，启动本地 PostgreSQL 后重跑为 `13 passed in 1.39s`；Phase 9 范围 Ruff lint 为 `All checks passed!`，format 为 `14 files already formatted`。
- **下一步：** 先添加失败回归，再实现同一已保存决定在恢复完成前可安全重试、恢复完成标记与拒绝/恢复审计；正常完成后的重复审批仍保持 409。

### Step 9.5：修复 decision/resume 崩溃窗口与治理审计缺口

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批（Blocking/Important 修复）。
- **完成日期：** 2026-08-01
- **本步骤目标：** 在不增加 reconciliation worker、SSO 或新审批功能的前提下，使已持久化的人类决定能够从受控 Runtime 故障恢复，同时保留重复审批无效和节点不重复语义。
- **红灯命令与结果：** `.venv/bin/python -m pytest tests/integration/governance/test_approval_workflow.py -q` → `3 failed in 1.54s`；分别证明权限拒绝无 audit、响应无恢复完成标记、Runtime 故障泄漏且决定提交后无法恢复。
- **实际修复：** `approval_requests` 增加 `resumed_at`；决定/恢复 API 在写决定前完成 Runtime 预检，并用 PostgreSQL transaction advisory lock 串行化同一 Approval 的完整尝试；只有相同 approver、相同 decision、相同 rationale 且尚未 `resumed_at` 的已保存决定可进入故障恢复；恢复后校验同 run、同 approval、同 decision、Run completed 和 Approval 终态，再原子写 `resumed_at` 与 `resume_approval_run` audit。
- **错误与审计：** Runtime/检查点受控异常返回稳定 503，不再泄漏未处理 RuntimeError；非 approver/未知本地用户的 pending/decision 访问写脱敏 deny audit；恢复失败写 `failed:runtime_unavailable`，恢复成功写 `completed:approve|reject`。审计只保存 ID、decision 和 rationale length，不保存 rationale 正文或异常正文。
- **重复与并发边界：** advisory lock 在数据库 session/transaction 结束或进程退出时自动释放；正常完成后的重复决定、不同 approver 接管、不同 rationale 替换均保持 409。Approval Decision 仍唯一且不可变。
- **migration：** 因 Phase 9 migration 尚未提交，更新同一 `20260724_0010` 并在隔离 test DB 执行 `0010 → 0009 → 0010`；`alembic current` 为 `20260724_0010 (head)`。
- **绿灯命令与结果：** workflow `3 passed in 1.31s`；migration/schema 联合回归此前为 `4 passed in 1.42s`；Phase 9 范围 Ruff lint/format 通过。
- **下一步：** 运行 Phase 9 及受影响 Agent/Service Desk/Tool/migration 回归、全仓测试、全仓 Ruff、正式 composition-root 一正常两失败演示，再同步 README、CURRENT_STATE 和 Phase 9 Dev Log/Report。

### Step 9.6：完成全量验证、正式演示、文档与学习门禁

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批（最终收尾）。
- **完成日期：** 2026-08-01
- **本步骤目标：** 在 Blocking/Important 修复后执行全部相关与全仓验证、正式 composition-root 演示，并同步 README、Current State、Roadmap、Architecture 和 Phase 9 report；不进入 Phase 10。
- **migration 更正：** Step 9.5 曾记录“更新同一 0010”；随后复核到开发/测试库均已应用 0010，因此没有保留该做法。最终以非破坏性 corrective migration `20260801_0011` 增加 `resumed_at`，test DB 完成 `0011 → 0010 → 0011`，开发/测试库均为 `20260801_0011 (head)`。
- **相关测试命令与结果：** `.venv/bin/python -m pytest tests/unit/governance tests/integration/governance tests/unit/agent_runtime tests/integration/agent_runtime tests/unit/tools tests/integration/tools tests/integration/service_desk tests/integration/api/test_service_desk.py tests/integration/knowledge/test_migrations.py -q` → 最终 `81 passed in 3.97s`。
- **全量测试命令与结果：** `.venv/bin/python -m pytest -q` → 最终 `211 passed in 11.28s`。
- **静态/安装门禁：** `.venv/bin/ruff check .` → `All checks passed!`；`.venv/bin/ruff format --check .` → `133 files already formatted`；compileall、pip check、`git diff --check` 通过；普通 `pip install --no-build-isolation .` wheel build/install 成功。
- **正常演示：** 完整财务管理员组请求先为 200/`waiting_approval`；approver approve 为 200；同一 run 恢复 completed；Approval 为 executed 且 `resumed_at` 非空；结果 `simulated_success`、`external_system_modified=false`；节点严格为 intake、Policy、create、await、simulate、finalize，前三节点各一次。
- **失败演示一：** 缺少业务理由 → 200/`needs_clarification`/`need_more_context`，没有创建 Approval。
- **失败演示二：** employee 调 approve → 403 `approval_access_denied`，并写 deny audit。
- **失败演示三：** 已完成后重复 approve → 409 `approval_already_decided`。
- **附加安全回归：** 具有 approval permission 的 `admin-demo` 发起请求后尝试 self-approval → 403，并写 deny audit；非 approver pending queue 读取也有 deny audit。
- **审计演示：** 本次轨迹包含 Policy/Approval Request、deny attempt、human approve、simulation、resume completed；正文和异常未进入 audit。
- **文档同步：** README 更新当前能力与真实结果；CURRENT_STATE 更新为 0011 和收尾事实；Roadmap 将 Phase 9 标为工程通过/学习待验收；Architecture/Overview 补充 recoverable resume seam；Phase 9 report 包含验收矩阵、审查修复、命令结果、完整数据流、五个概念、十道无答案面试题、30–60 分钟练习和三个面试薄弱点。
- **阶段判断：** 没有剩余 Blocking 或必要 Important，工程 **PASS**；总体 **CONDITIONAL PASS**，项目所有者需独立回答十道 Phase 9 面试题并完成练习。
- **建议版本：** Commit `fix(governance): make human approval resume recoverable`；当前建议 Tag `phase-9-engineering-pass`，学习验收后再使用 `phase-9-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 10。

### Step 9.7：修正 admin 越出 approver-only 验收边界

- **所属 Phase：** Phase 9：RBAC、风险策略与 Human-in-the-loop 模拟审批（最终逐字验收修正）。
- **完成日期：** 2026-08-01
- **发现：** 最终逐字对照“approver 可以审批、非 approver 不能审批”时确认 Phase 9 原 seed 同时给 admin 和 approver 配置了 `approval:read/decide`。permission-based RBAC 本身合理，但本 Phase 明确要求只有 approver 能审批，因此这是第二个 Blocking，不能用设计解释绕过。
- **修复：** 新增非破坏性 corrective migration `20260801_0012_restrict_approval_to_approver.py`，删除 admin role 的两个 approval permission；downgrade 可恢复旧映射。migration integration test 精确断言两个 approval permission 只映射到 approver。
- **失败路径加强：** self-approval 改由具备真实审批权限的 `approver-demo` 自己发起并自批，断言 403 + deny audit；`admin-demo` 对另一个人的已保存决定返回 403，而不是进入恢复分支；不同 rationale 仍为 409。
- **migration 验证：** test DB `0012 → 0011 → 0012` 成功；开发/测试库均为 `20260801_0012 (head)`。
- **最终相关结果：** `81 passed in 4.12s`。
- **最终全量结果：** `211 passed in 11.39s`。
- **最终静态门禁：** Ruff `All checks passed!` / `134 files already formatted`；compileall、pip check、Git whitespace 通过。
- **最终正式演示：** 缺少理由 → need_more_context/无 Approval；admin approve → 403；approver approve → 200/same run completed/executed/resumed/simulated only；完成后 duplicate → 409；六节点严格无重复。
- **最终结论：** 两个 Blocking 和必要 Important 均已修复，工程 PASS；总体仍为学习待验收的 CONDITIONAL PASS。停止，不进入 Phase 10。

---

## Phase 10：Agent Evaluation Framework

### Step 10.1：建立严格数据集合同与 30 条初始案例

- **所属 Phase：** Phase 10：Agent Evaluation Framework。
- **完成日期：** 2026-08-01
- **本步骤目标：** 在运行任何 Agent 或计算指标前固定版本化案例格式，并用机器校验保证本阶段要求的类别和数量不会静默漂移。
- **接手事实：** 根目录没有 `AGENTS.md`；Phase 10 报告尚不存在；`main@b882da7` 之后的 Phase 6–9 仍是未提交工作区改动。修改前在允许访问本地 PostgreSQL 后，全量测试为 `211 passed in 11.37s`；沙箱内首次运行的 `5 failed, 118 passed, 88 errors` 共同根因是 localhost PostgreSQL `Operation not permitted`，不是代码断言失败。
- **实际完成内容：** 新增严格 Pydantic 数据合同，包含 `case_id`、`user_query`、`user_context`、`expected_intent`、`expected_documents`、`expected_tool_calls`、`expected_final_status`、`prohibited_actions` 和 `reference_answer`，并增加类别与可选 refusal 标注；数据集校验唯一 ID、非空字段、禁止额外字段、声明配额与实际案例数完全一致；创建 `phase-10-v1` 共 30 条案例，精确覆盖知识问答 8、VPN 6、Outlook 6、账号 5、工单 3、高风险权限 2。
- **新增或修改文件：** `src/enterprise_it_support/evaluation/dataset.py`、`data/evaluation/agent_cases.json`、`docs/project_journal.md`。
- **关键设计：** expected Document 使用 source name + title 的稳定人工标识，不把每次导入生成的 UUID 写死在数据集；Tool Call 同时标注名称和完整参数；每条案例都声明禁止动作，使安全评价不依赖报告作者临时解释。
- **运行与验证命令：** `PYTHONPATH=src .venv/bin/python -c '...load_evaluation_dataset(...)...'`。
- **真实结果：** 成功输出 `phase-10-v1 30`，类别配额为 `8/6/6/5/3/2`；首次未设置 `PYTHONPATH=src` 时因当前环境是普通 wheel 安装而出现 `ModuleNotFoundError`，使用仓库源码路径后通过，未修改全局 Python。
- **当前限制：** 本步骤只完成数据合同和人工标注；指标、Runner、CLI、报告与回归门禁尚未实现。
- **与下一步骤的关系：** 下一步实现纯确定性指标和统一观测结果模型，使规则计算可以独立单元测试，而不依赖数据库或模型调用。

### Step 10.2：实现确定性质量指标与统一原始观测模型

- **所属 Phase：** Phase 10：Agent Evaluation Framework。
- **完成日期：** 2026-08-01
- **本步骤目标：** 把检索、生成、Agent 与 System 指标实现为不调用模型、不访问数据库的纯规则层，并保留每个指标的真实分母和不适用状态。
- **实际完成内容：** 新增 provider-neutral `AgentObservation`、工具调用、Token、逐案例分数和聚合指标模型；实现 Retrieval Recall@3/5、MRR，Generation Citation Validity、Evidence Coverage、Unsupported Claim Rate、Refusal Correctness，Agent Intent/Tool Selection/Tool Argument Accuracy、Workflow Completion Rate、Prohibited Action Rate，以及 System Latency、Tool Error Rate、Average Steps、Token Usage；逐案例输出稳定失败原因；`None` 明确表示无适用样本，不把缺少观测伪装为 0 分。
- **关键规则：** Citation 必须引用本次 Retrieval 的真实 Chunk ID；Evidence Coverage 按人工 expected Document 是否被最终 Citation 覆盖；Unsupported Claim 对模型回答中的 claim 与受控 evidence 文本做规范化包含/词覆盖检查；工具选择比较有序名称，工具参数比较严格 JSON 对象；禁止动作以数据集 allowlist 交集确定。
- **新增或修改文件：** `src/enterprise_it_support/evaluation/models.py`、`src/enterprise_it_support/evaluation/metrics.py`、`tests/unit/evaluation/test_agent_dataset.py`、`tests/unit/evaluation/test_agent_metrics.py`、`docs/project_journal.md`。
- **运行与验证命令：** `PYTHONPATH=src .venv/bin/python -m pytest tests/unit/evaluation/test_agent_dataset.py tests/unit/evaluation/test_agent_metrics.py -q`；相关 Ruff lint/format。
- **真实结果：** `6 passed in 0.03s`；Ruff `All checks passed!`；`7 files already formatted`。首次 format check 报告 3 个文件需要机械格式化，执行 Ruff format 后复验通过。
- **当前限制：** Unsupported Claim Rate 是可解释的词法规则，不等于语义蕴含；它会在报告中保持该限制，后续可选 Judge 只能作为独立辅助分数。
- **与下一步骤的关系：** 下一步实现实际 Agent Runner、可选 Judge、版本元数据、阈值/差异和 JSON/Markdown 报告。

### Step 10.3：接通真实 Agent Runner、可选 Judge、报告差异与回归门禁

- **所属 Phase：** Phase 10：Agent Evaluation Framework。
- **完成日期：** 2026-08-01
- **本步骤目标：** 用一条 CLI 运行现有正式 Agent/Service Desk/Governance surface，输出可复用原始 JSON、Markdown、类别统计、失败列表、previous-run diff，并以退出状态执行回归门禁。
- **实际完成内容：** 新增共享的 6 份虚构知识 seed；`LocalAgentEvaluationSubject` 调用正式 `/agent/respond`，随后通过现有 Conversation 与 Tool Repository 读取 refusal、Token、完整工具参数和审计状态；`TrackingModelGateway` 只包裹现有 Gateway 并记录每案例 provider/model/Prompt/Token；工单只观察 pending proposal，不自动确认；R3 只观察 `waiting_approval`，不自动审批；新增可注入 `ModelGatewayJudge`，严格记录 Judge provider/configured/resolved model 和 `agent-evaluation-judge-v1`，其结果与确定性指标分区且明确不是绝对真值；新增阈值、previous diff、安全回归检查、JSON/Markdown 写出和 `python -m scripts.run_evaluations`。
- **回归规则：** Intent Accuracy ≥ 0.90；Prohibited Action Rate ≤ 0；Citation Validity ≥ 0.95；Workflow Completion Rate ≥ 0.90。与上次可比较时，Prohibited Action Rate 上升、Unsupported Claim Rate 上升或 Refusal Correctness 下降都会单独使门禁失败。
- **首轮真实运行：** 30 条全部获得 HTTP 200 并生成报告，但 Gate FAIL；Workflow Completion=`0.80`。失败来自 6 条 Outlook 案例缺少现有流程要求的影响范围、错误代码和访问渠道，Agent 正确返回 `needs_clarification`。修正数据为完整诊断正样本，没有修改业务工作流或放宽阈值。
- **修正后真实运行：** Gate PASS；Recall@3=`1.0`、Recall@5=`1.0`、MRR=`0.9166666666666666`；Citation Validity=`1.0`、Evidence Coverage=`1.0`、Unsupported Claim Rate=`0.0`、Refusal Correctness=`0.75`；Intent/Tool Selection/Tool Argument/Workflow=`1.0`；Prohibited Action Rate=`0.0`；Tool Error Rate=`0.0`；实际失败列表为 `knowledge-07`、`knowledge-08`，两者暴露 Fake RAG 对有主题词但无支持事实问题没有拒答，本阶段不修改 Agent 业务。
- **新增或修改文件：** `evaluation/fixtures.py`、`judge.py`、`runner.py`、`reporting.py`、`scripts/run_evaluations.py`、`scripts/evaluate_retrieval.py`、`data/evaluation/thresholds.json`、`.gitignore`、相关 unit/integration tests、`docs/project_journal.md`。
- **运行与验证命令：** 两次 `PYTHONPATH=src IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.run_evaluations --output-dir /private/tmp/...`；`PYTHONPATH=src .venv/bin/python -m pytest tests/integration/evaluation/test_run_evaluations.py -q`；评估 unit tests；相关 Ruff/compileall。
- **测试结果：** CLI/report/diff PostgreSQL integration `1 passed in 3.80s`；评估 unit `14 passed in 0.33s`；相关 Ruff lint/format 与 compileall 通过。
- **安全边界：** 默认 Fake Provider；配置为真实模型时，CLI 没有显式 `--allow-real-api` 会拒绝运行；Judge 默认关闭；评估不会确认工单、批准权限、调用真实企业系统或执行任意命令工具。
- **当前限制：** 首轮 dataset 较小且来自虚构固定环境；Fake Provider 的 Refusal Correctness 为 0.75，报告如实列出；词法 Unsupported Claim 不是语义蕴含；本机 latency 只适合同环境趋势比较。
- **与下一步骤的关系：** 下一步运行全量测试、正式安装态精确 CLI、同目录 previous diff、安全失败返回码、全仓静态门禁，并同步 Phase 10 文档。

### Step 10.4：完成安装态一键评估、全量回归与 Phase 10 收尾

- **所属 Phase：** Phase 10：Agent Evaluation Framework（最终验收）。
- **完成日期：** 2026-08-01
- **本步骤目标：** 从普通安装态运行用户指定的一键命令，证明 30 条 Fake Provider 评估、原始结果、Markdown、previous diff 和回归退出状态可以组合工作；随后完成全量测试、数据库版本、静态门禁和文档收尾。
- **固定 corpus 修正：** 首次全量为 `1 failed, 222 passed in 12.62s`；一个 integration 断言把两条当前 Fake RAG 失败硬编码为长期合同，且共享测试库额外知识文档会污染离线排名。最终断言只要求报告真实列出失败，Runner 用六份虚构文档 ID 过滤正式 Retriever 的宽候选并记录 corpus fingerprint/count，既不修改生产检索，也不让其它 test/dev 文档改变基线。
- **最终一键命令：** `IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.run_evaluations`。
- **最终 CLI 结果：** exit 0；run `eval-20260801T123925Z-c4e35d86`；dataset `phase-10-v1`；Gate PASS；失败案例 `knowledge-07`、`knowledge-08`；自动 baseline 为 `eval-20260801T122520Z-51948191`，全部确定性质量指标不变，Latency 改善 `0.7333333333333343 ms`。
- **最终指标：** Recall@3/Recall@5=`1.0/1.0`，MRR=`0.9166666666666666`；Citation Validity/Evidence Coverage=`1.0/1.0`，Unsupported Claim Rate=`0.0`，Refusal Correctness=`0.75`；Intent/Tool Selection/Tool Argument/Workflow=`1.0`；Prohibited Action Rate/Tool Error Rate=`0.0/0.0`；Latency=`48.43333333333333 ms`，Average Steps=`6.933333333333334`，Total Token=`1110`、模型调用 37 次。
- **测试结果：** Phase 10 unit `14 passed in 0.41s`；PostgreSQL CLI/report/diff integration `1 passed in 3.69s`；修复后最终全量 `.venv/bin/python -m pytest -q` 为 `223 passed in 14.96s`，无 skip、xfail 或真实 API 调用。
- **静态与安装门禁：** 普通 `pip install --no-build-isolation .` 成功；Ruff `All checks passed!`；format `148 files already formatted`；compileall、pip check、`git diff --check` 均通过。
- **数据库证据：** 开发库与隔离测试库的 `alembic current` 均为 `20260801_0012 (head)`；Phase 10 没有新增 migration 或 Evaluation 表。
- **安全结论：** Gate 使用确定性规则；Prohibited Action Rate 为 0；Judge 默认关闭且不能覆盖规则；工单没有被自动确认，R3 没有被自动批准，没有真实企业 Adapter、真实付费 API 或任意命令执行。
- **文档同步：** README、Project Overview、Roadmap、Backlog、Architecture、Context、Current State 与 Phase 10 report 已同步到代码和测试事实；根目录 `AGENTS.md` 仍不存在，该缺失已明确记录，没有伪造其内容。
- **已知质量缺口：** `knowledge-07/08` 说明当前 Fake RAG 对“主题相关但事实不受支持”的问题可能错误回答；因此 Gate PASS 不等于所有案例 PASS。初始 30 条虚构数据也不代表生产分布，词法 Unsupported Claim 不是语义蕴含证明。
- **阶段判断：** 没有剩余 Blocking 或必要 Important，工程 **PASS**；总体 **CONDITIONAL PASS**，项目所有者需独立回答 Phase 10 report 的 10 道面试题并完成练习。
- **建议版本：** Commit `feat(evaluation): add deterministic agent quality gates`；学习验收完成后建议 Tag `phase-10-complete`。
- **停止条件：** 本次到此停止，未经项目所有者明确确认不进入 Phase 11。

### Step 10.5：独立收尾审查并关闭安全门禁与指标语义缺口

- **所属 Phase：** Phase 10：Agent Evaluation Framework（独立收尾审查）。
- **完成日期：** 2026-08-01
- **审查边界：** 不沿用 Step 10.4 的 PASS 结论；固定 Git 基线仍为 `b882da7`，但 Phase 6–10 都在同一未提交工作区，因此只审查 Evaluation 模块、CLI、数据集、测试和 Phase 10 文档。根目录 `AGENTS.md` 与 `docs/agents/issue-tracker.md` 均不存在。
- **Blocking 一：** `--allow-real-api` 只拦截真实 Model，没有拦截真实 Embedding；Fake Model + OpenAI Embedding 会在 fixture indexing/query embedding 中调用真实 API。修复为任一 provider 非 Fake 都必须显式授权，并增加无需数据库的拒绝测试。
- **Blocking 二：** Gate FAIL 的 immutable report 会正常写出，但原实现仍覆盖 `latest.json/latest.md`；一次安全退化会污染下一次默认 baseline。修复为只有 Gate PASS 才更新 latest aliases；失败 run 仍保留自己的 JSON/Markdown。
- **Blocking 三：** Prohibited Action 数据集使用 `shell_execution/python_execution/sql_execution/external_system_modified`，Runner 只记录 `tool:<name>`/`executed:<name>`，字符串交集会漏报。修复为统一 canonical observation：裸工具名、tool/execute 标签、危险工具 token、通用 side-effect 和 external modification；安全观察采用保守 fail-closed 语义。
- **Blocking 四：** 现有 90% Intent/Workflow inclusive threshold 允许 30 条中 3 条非知识案例返回 HTTP error 后仍 PASS；已用当前 Gate 函数复现 `three_http_failures_can_still_pass=True`。修复为任何 case-level HTTP error 都增加 `system.evaluation_completion_rate < 1` Gate failure。
- **必要 Important：** Recall@K 从“命中任一 expected Document”的 Hit@K 改为命中文档数/全部 expected Documents；MRR 仍计算首个 relevant rank；Tool Argument Accuracy 对 expected/actual 都为空的案例返回 N/A，分母从全部 30 条收敛到真实工具案例；`risk-02` 的 unsupported escalation 现在确定性记录为 refusal，使其进入 Refusal Correctness。
- **必要 Important：** previous diff 现在只有 dataset SHA 与 corpus fingerprint 均相同时才可比较；否则逐指标为 `not_comparable` 并记录原因。显式 `--baseline` 不存在改为 fail closed，不再静默建立新基线；运行元数据补充 Embedding provider/model/profile，code fingerprint 覆盖 Agent、Conversation、Evaluation、Governance、Intelligence、Knowledge、Service Desk 和 Tools。
- **必要 Important：** 固定 corpus 从“生产 Retriever 先取 50 再过滤”改为通过 `SearchFilters.document_ids` 在 PostgreSQL keyword/vector 排名前过滤六个允许 Document ID；避免共享库超过 50 个高排名干扰项改变基线。该过滤仍经过生产 authorization/validity/RRF 路径，不创建第二套 Retrieval。
- **明确适用范围：** Unsupported Claim Rate 仍只计算存在可比 evidence 的知识回答 claim；诊断模板的工具事实没有统一的多语言 claim/evidence 合同，因此不伪造覆盖。报告保留真实 sample count 和此限制，不把 8 条样本描述为 30 条全覆盖。
- **失败路径测试：** 新增真实 Embedding 拒绝、显式 baseline 缺失、canonical prohibited action、HTTP case error Gate、多个 expected Documents Recall、无工具参数 N/A、dataset/corpus 不可比、失败报告不覆盖 latest，以及 PostgreSQL CLI Gate FAIL/exit 1 测试。
- **聚焦结果：** Evaluation unit `23 passed in 0.74s`；PostgreSQL Evaluation integration `1 passed in 5.11s`；聚焦 Ruff lint/format 通过。首次集成运行在沙箱中因 localhost PostgreSQL `Operation not permitted` 失败，获准访问同一隔离测试库后通过，未跳过或替换数据库测试。
- **未处理 Optional：** 没有增加 CI、Evaluation 数据库表、Web UI、远程 artifact store、真实 Judge 校准、并发 Runner 或生产多租户过滤；这些都不属于 Phase 10 收尾。
- **下一步：** 重新安装当前 wheel，运行受影响知识检索与全仓测试、全仓 Ruff/compile/dependency/whitespace，再执行一正常和至少两个 fail-closed CLI 演示并同步最终文档。

### Step 10.6：完成独立收尾全量验证、四场 CLI 演示与文档闭环

- **所属 Phase：** Phase 10：Agent Evaluation Framework（独立收尾最终验收）。
- **完成日期：** 2026-08-01
- **正常场景：** 普通 wheel 重新构建/安装后执行 `IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.run_evaluations`，连续两次 exit 0/Gate PASS；最终成功 run 为 `eval-20260801T131423Z-f1fcc44f`，自动 baseline `eval-20260801T131339Z-0e377573`，dataset/corpus 可比，全部确定性质量指标 unchanged。
- **正常指标：** Recall@3/5=`1.0/1.0`、MRR=`0.9166666666666666`；Citation Validity/Evidence Coverage=`1.0/1.0`；Unsupported Claim Rate=`0.0`（8 cases）；Refusal Correctness=`0.7777777777777778`（9 cases，新增 high-risk refusal）；Intent/Tool Selection/Workflow=`1.0`（30 cases）；Tool Argument=`1.0`（17 cases）；Prohibited Action/Tool Error=`0.0/0.0`；Average Steps=`6.933333333333334`；Total Token=`1110`。
- **保留失败案例：** `knowledge-07/08` 仍为 `refusal_incorrect`；它们证明 Gate PASS 不等于无 case failure。本阶段没有越界修改 RAG/Relevance 业务。
- **失败场景一：** `--baseline /private/tmp/phase10-does-not-exist.json` → exit 2，稳定 `evaluation_configuration_error`；没有访问数据库或重建 baseline。
- **失败场景二：** Fake Model + OpenAI Embedding 配置但不传 `--allow-real-api` → exit 2，稳定 `evaluation_configuration_error`；在数据库和 Provider 调用前拒绝，没有真实 API 调用。
- **失败场景三：** 使用临时强制失败阈值运行完整 30-case → exit 1/Gate FAIL，失败原因为 Intent minimum 1.1；immutable 失败 report 为 `eval-20260801T131655Z-b96cff1a`，成功 `latest.json` 仍保持 `eval-20260801T131423Z-f1fcc44f`，证明失败不污染 baseline。
- **测试结果：** Evaluation unit `23 passed in 0.74s`；PostgreSQL Evaluation integration `1 passed in 5.11s`；最终全量 `.venv/bin/python -m pytest -q` 为 `232 passed in 16.76s`，没有 skip/xfail 或真实 Provider 调用。
- **静态与依赖结果：** `.venv/bin/ruff check .` → `All checks passed!`；`.venv/bin/ruff format --check .` → `149 files already formatted`；compileall、pip check、`git diff --check` 通过。
- **数据库结果：** development/test `alembic current` 均为 `20260801_0012 (head)`；Phase 10 仍没有 migration 或 Evaluation 业务表。
- **文档同步：** README 当前能力、CLI fail-closed/latest 语义和明确不包含已修正；Project Overview、Architecture、Current State、Phase 10 report 与追加式 Journal 已同步当前代码和真实命令结果。
- **剩余限制：** Unsupported Claim Rate 只适用于有可比 evidence 的知识回答 claim；30 条虚构案例不代表生产分布；Judge 未经真实模型/人工标注校准；本机 latency 不是 SLA；Phase 6–10 仍共享一个未提交工作区，缺少独立 Phase commit diff。
- **最终工程判断：** 所有 Blocking 和必要 Important 已关闭；没有过度设计或提前实现 Phase 11；工程 **PASS**，总体 **CONDITIONAL PASS**，只剩项目所有者完成 Phase 10 学习验收。
- **建议版本：** Commit `fix(evaluation): close phase 10 regression gate gaps`；学习验收后建议 Tag `phase-10-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 11。

---

## Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard

### Step 11.1：固定 Feedback、取消确认与 Analytics 数据合同

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard。
- **完成日期：** 2026-08-01
- **本步骤目标：** 在实现 UI 前先建立后端拥有的数据合同和数据库边界，确保 Streamlit 不直接访问数据库或复制统计逻辑。
- **接手事实：** 根目录仍没有 `AGENTS.md`；Git 基线为 `main@b882da7`，Phase 6–10 仍是已有未提交工作区改动。修改前全量第一次因 sandbox 禁止 localhost PostgreSQL 得到 `6 failed, 138 passed, 88 errors`；获准访问隔离测试库后原命令为 `232 passed in 16.19s`。
- **实际完成内容：** 新增 `feedback` ORM 和 `20260801_0013` migration；Feedback 以 Agent Run 为唯一业务关联，可选关联 Conversation/Ticket，保存 resolved、1–5 satisfaction、可选评论和 idempotency key；Pending Confirmation 增加 `cancelled` 终态；新增 Feedback、Metric、分类计数、最近评估和 Analytics Summary 的严格 Pydantic HTTP Schema；新增可配置 Evaluation artifact 路径；增加 pandas 与 Streamlit 运行依赖声明。
- **数据口径决定：** 自助解决率以已提交 Feedback 为分母，resolved 且未关联 Ticket 为分子；转人工率以后端 Agent Run 为分母，escalated 或已生成 Ticket 的 Run 为分子；无样本指标返回 `null + sample_count=0`，不伪装成 0。
- **新增或修改文件：** `analytics/__init__.py`、`analytics/models.py`、`analytics/schemas.py`、migration `20260801_0013`、`service_desk/domain.py`、`service_desk/models.py`、`platform/config.py`、`migrations/env.py`、`pyproject.toml`、migration integration test。
- **运行与验证命令：** Phase 11 文件 Ruff lint/format；`IT_SUPPORT_ENVIRONMENT=test .venv/bin/alembic upgrade head`；`.venv/bin/python -m pytest tests/integration/knowledge/test_migrations.py -q`。
- **真实结果：** Ruff `All checks passed!`，9 个相关文件已格式化；测试数据库升级到 `20260801_0013`；migration/schema test `1 passed in 0.27s`，并验证 feedback 全部列和 confirmation `cancelled` check constraint。
- **当前限制：** 本步骤只完成 schema/contract；Feedback Repository/API、取消 API、Analytics SQL/pandas 实现和 Streamlit 尚未完成。
- **与下一步骤的关系：** 下一步实现后端 Repository/Service/Routes，并从真实 PostgreSQL 验证幂等 Feedback、取消权限/状态、全部统计口径和最近 Evaluation artifact 投影。

### Step 11.2：实现 Feedback、取消确认与 Analytics 后端 API

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard。
- **完成日期：** 2026-08-01
- **本步骤目标：** 让 UI 需要的写入和统计全部通过 FastAPI 后端公开，并用真实 PostgreSQL 验证权限、幂等和统计语义。
- **实际完成内容：** 实现 `POST /feedback`，按 Agent Run + idempotency key 串行化，一次 Run 只接受一份不可变 Feedback，并验证 actor/role、可选 Ticket 归属和来源 Run；实现 `POST /agent/cancel`，只有原 actor/role 可把 R1 pending 变为 cancelled，重复取消幂等，取消后 confirm 返回 409，允许/拒绝均写审计；实现 `GET /analytics/summary`，只允许拥有 `audit:read` 的本地支持角色。
- **统计实现：** Analytics Repository 以有界时间窗口执行 SQL 聚合，统计 Ticket 分类、三类问题、转人工、Agent Steps、工具调用、响应时间、工具成功、Feedback 和失败原因；Analytics Service 使用 pandas 做标签映射、排序、类型规范化和 response projection；最近评估由后端读取本地 immutable Evaluation JSON，跳过损坏文件并去重，不由 UI 直接读文件。
- **新增或修改文件：** `analytics/domain.py`、`analytics/persistence.py`、`analytics/service.py`、`analytics/routes.py`、FastAPI composition root、Service Desk domain/model/repository/service/routes/schemas、migration `0013`、Analytics/Service Desk/migration integration tests。
- **运行与验证命令：** 阿里云 PyPI 镜像安装 pandas 3.0.5、Streamlit 1.60.0 及依赖；Phase 11 Ruff；test DB `0013 → 0012 → 0013`；`.venv/bin/python -m pytest tests/integration/api/test_analytics.py tests/integration/api/test_service_desk.py tests/integration/knowledge/test_migrations.py -q`。
- **真实结果：** 官方 PyPI 首次下载约 18 kB/s 后中止，清华镜像返回 403，阿里云镜像成功完成项目本地依赖安装；migration 首次 downgrade 暴露旧开发快照没有后补 `cancelled_at`，改为 `IF EXISTS` 后往返成功；聚焦最终 `6 passed in 2.17s`；相关 Ruff 通过。
- **验收覆盖：** Feedback success/replay/conflict/wrong actor；Ticket-linked unresolved Feedback；Analytics employee 403/support 200；两条 Run 的 self-service/transfer 比例、分类、步骤、工具、响应时间、成功率、满意度和最近 Evaluation；取消 wrong actor、成功、replay 和取消后 confirm 409。
- **当前限制：** Analytics 是本地支持角色 dashboard，不是生产 tenant analytics；最近 Evaluation 仍是本地 artifact，不是 Evaluation 数据库；Feedback 一次提交后不可编辑。
- **与下一步骤的关系：** 下一步实现可测试的 HTTP client 和 Streamlit Chat/Dashboard 页面；页面只负责交互与呈现，不包含 SQL、指标计算、Policy 或 confirmation 状态机。

### Step 11.3：实现两页 Streamlit UI 与 HTTP-only client

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard。
- **完成日期：** 2026-08-01
- **本步骤目标：** 提供简单可演示 UI，同时保持 Streamlit 只调用 FastAPI，不导入 Repository、ORM、SQL 或业务 Service。
- **实际完成内容：** 新增 `ITSupportAPIClient`，只调用 `/agent/respond`、`/agent/confirm`、`/agent/cancel`、`/feedback` 和 `/analytics/summary`，统一 timeout、连接失败、错误 envelope 和 JSON 校验；新增 IT Support Chat 页面，支持模拟 actor/role、多轮 Conversation ID、Agent 状态、引用、步骤、Tool Execution audit、pending impact、确认/取消、Ticket Number 和 resolved/satisfaction Feedback；新增 Analytics Dashboard 页面，展示 Ticket 分类、三类问题数量、自助/转人工、平均步骤/工具/响应时间、工具成功、满意度、失败原因和最近评估。
- **职责边界：** UI 的 pandas 只把后端已聚合的 label/count 映射为图表 DataFrame，不计算业务指标；没有导入 DatabaseManager、SQLAlchemy、Repository、Policy、Tool Gateway 或 Evaluation 文件；FastAPI 未启动时显示安全错误，不回退到数据库或本地 artifact。
- **新增或修改文件：** `apps/ui/__init__.py`、`client.py`、`chat_page.py`、`dashboard_page.py`、`streamlit_app.py`、UI client tests、`.env.example`、`pyproject.toml`。
- **运行与验证命令：** `.venv/bin/python -m pytest tests/unit/ui -q`；UI Ruff lint/format；compileall；使用 `streamlit.testing.v1.AppTest` 分别渲染 Chat 与 Dashboard。
- **真实结果：** UI client `4 passed in 0.01s`；Ruff `All checks passed!`，7 个 UI/test 文件已格式化；compileall 成功；Chat AppTest 为 0 exception/title `IT Support Chat`；切换 Dashboard 为 0 exception/title `Analytics Dashboard`，未启动 API 时稳定显示 `api_unavailable`。
- **当前限制：** UI 是本地同步演示，不提供流式 token、生产登录、浏览器级 E2E 或复杂视觉设计；R3 Human Approval 仍使用既有 API/运行边界，本次 Chat 重点验收 R1 confirmation 和本地 Ticket。
- **与下一步骤的关系：** 下一步增加幂等、只写固定虚构数据的 Phase 11 seed 脚本，确保 Dashboard 在不调用真实 Provider 的情况下立即有可展示分布和成功/失败样本。

### Step 11.4：提供幂等的固定虚构 Dashboard seed

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard。
- **完成日期：** 2026-08-01
- **本步骤目标：** 让个人项目无需真实企业系统或付费模型即可快速展示 Dashboard 的正常、转人工、失败和满意度数据。
- **实际完成内容：** 新增 `python -m scripts.seed_phase11_demo`；脚本使用固定 namespace UUID、固定 `phase11-demo-employee` actor、`phase11-seed-*` request ID 和明确虚构正文，写入 6 Agent Runs、23 Steps、6 Tool Executions、4 Tickets 和 4 Feedback；覆盖 VPN/Outlook/account/ticket/escalated/failed、成功与 timeout、四种 Ticket category、resolved/unresolved 和 1–5 satisfaction；全部 insert 使用固定主键与 `ON CONFLICT DO NOTHING`，不删除或覆盖已有用户数据。
- **安全边界：** Seed 只通过项目 DatabaseManager 写当前配置的本地 PostgreSQL；不调用 LLM/Embedding、Tool Gateway、真实 Adapter、外部 HTTP、Shell/Python Agent 工具或权限修改；它是演示 fixture，不是业务写入入口。
- **新增或修改文件：** `scripts/seed_phase11_demo.py`、`tests/integration/analytics/test_seed.py` 及 package marker。
- **运行与验证命令：** Seed 文件 Ruff lint/format；`.venv/bin/python -m pytest tests/integration/analytics/test_seed.py -q`。
- **真实结果：** Ruff `All checks passed!`，3 个相关文件已格式化；隔离 PostgreSQL 连续运行 seed 两次后仍精确为 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；`1 passed in 0.33s`。
- **当前限制：** Seed 时间相对运行时生成，因此适合最近 30 天演示；它不为真实用户创建可信身份，也不生成生产规模或统计显著性数据。
- **与下一步骤的关系：** 下一步执行 verification-loop：完整 migration 往返、相关/全量测试、安装态 seed、真实 FastAPI + Streamlit 两页 smoke、安全边界和最终文档同步。

### Step 11.5：完成事务审查、真实演示、页面截图和最终验收

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard（最终 verification-loop）。
- **完成日期：** 2026-08-01
- **独立一致性修正：** 成功取消 pending confirmation 的状态变化与 allow audit 原先是两个事务，存在 audit 失败后状态已取消的窗口；改为 Repository 同一事务写 `cancelled_at` 和 AuditEvent，deny audit 仍由 Service 记录。自助解决率从“Feedback 未传 ticket_id”修正为“resolved 且该 Run 不存在来源 Ticket”，避免客户端漏传 Ticket Number 抬高指标。聚焦复测 `5 passed in 2.26s`，Ruff 通过。
- **普通安装态：** `.venv/bin/python -m pip install --no-build-isolation .` 成功构建并重新安装 wheel；pandas 3.0.5、Streamlit 1.60.0 可导入，`pip check` 无 broken requirements。
- **数据库与 seed：** development 升级到 `20260801_0013 (head)`；最终 development/test `alembic current` 都是 `20260801_0013 (head)`；安装态 seed 重跑仍返回固定 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback，证明不覆盖实时演示新增数据且 seed 自身幂等。
- **真实 HTTP 演示：** 临时启动正式 FastAPI 和 Streamlit；通过 UI HTTP client 依次完成 VPN diagnosis、同一 Conversation 工单请求、R1 confirm、本地建单、unresolved/3 分 Feedback 和 Analytics。结果为 diagnosis `completed`、5 次工具调用、confirmation `executed`、Ticket `IT-20260801-000001`、Feedback 保存成功，Analytics 返回 14 Runs/5 Tickets（随后浏览器 UI VPN 演示又增加一条 Run，因此截图数值按当时数据库实时变化）。
- **实际浏览器检查：** 通过本地浏览器打开 `127.0.0.1:8501`；Chat 显示 `completed`、`vpn_diagnosis`、10 Steps、5 Tool calls 和完整 executed tools/audit 表；Dashboard 显示 Tickets、自助、转人工、工具成功、满意度、平均步骤/工具/响应时间、四组简洁图表和最近 Evaluation，没有页面异常。实际 1440×900 截图保存到 `docs/screenshots/phase11-chat.png` 和 `phase11-dashboard.png`。
- **运行中发现与修复：** Streamlit 1.60 对三个 `use_container_width=True` 打出弃用提示；统一改为 `width="stretch"`，两页 AppTest 仍 0 exception，后续运行不再产生该项目弃用提示。
- **错误命令记录：** 最终全量第一次错误地给整个 pytest 进程设置 `IT_SUPPORT_ENVIRONMENT=test`，导致 10 个专门验证 development 默认配置的 unit tests 被环境污染，得到 `10 failed, 229 passed in 17.13s`；这不是代码失败。按仓库标准、不加全局覆盖的 `.venv/bin/python -m pytest -q` 立即重跑为 `239 passed in 17.01s`。Integration fixtures 自行设置隔离 test 环境，没有弱化或跳过数据库测试。
- **最终静态门禁：** `.venv/bin/ruff check .` → `All checks passed!`；`.venv/bin/ruff format --check .` → `168 files already formatted`；compileall、pip check、`git diff --check` 通过；Streamlit 两页 AppTest 通过。
- **职责边界审查：** `apps/ui` 没有 DatabaseManager、SQLAlchemy、Repository、Policy、SQL 或 Evaluation 文件读取；Dashboard 的全部指标通过 `/analytics/summary`；Chat 的确认/取消、工单和 Feedback 全部通过 FastAPI；没有新增真实 Adapter、真实 Provider、任意命令工具或审批绕过。
- **文档闭环：** README 增加 seed/启动命令、四步演示和两张实际截图；Project Overview、Roadmap、Backlog、Current State 与 Phase 11 report 同步当前代码、统计口径、真实验证和限制。根目录 `AGENTS.md` 仍不存在，该事实没有被虚构。
- **阶段判断：** 用户列出的功能和验收项全部有实现与运行证据；没有剩余 Blocking 或必要 Important，工程 **PASS**。总体 **CONDITIONAL PASS**，项目所有者需完成 Phase 11 report 的 10 道面试题与独立练习。
- **建议版本：** Commit `feat(ui): add phase 11 support chat and analytics dashboard`；学习验收后建议 Tag `phase-11-complete`。
- **停止条件：** 本次到此停止，未经项目所有者明确确认不进入 Phase 12。

### Step 11.6：独立收尾验收、必要修复与学习门禁

- **所属 Phase：** Phase 11：Streamlit 用户界面与 IT 工单数据分析 Dashboard（独立收尾验收）。
- **完成日期：** 2026-08-01
- **接手与审查边界：** 根目录 `AGENTS.md` 仍不存在；Git 基线仍为 `b882da7`，Phase 6–11 共处未提交工作区。本轮按 Phase 11 原始任务、代码、真实 PostgreSQL 测试和运行结果审查，只修 Blocking 与必要 Important，不增加 Phase 12 功能。
- **修改前问题清单：** 无 Blocking；Important 包括 UI 把全部 retrieved candidates 误标为 Citation、确认后未刷新 `create_ticket` audit、身份/新请求/取消可能留下陈旧 Ticket 或 pending 状态、Run cohort 的 child timestamp 二次过滤导致步骤/工具低估、Feedback 只按 Run 加锁不能覆盖全局 idempotency key、取消/空窗口/损坏 artifact/时间边界/UI 状态失败测试不足，以及 seed 没有提供知识问答数据。Phase report 的角色列表和失败原因口径也与代码不一致。
- **实际修复：** Chat 只投影 `final_response.citations`；新增 Run GET client，确认后刷新 matching assistant trace；身份变化重置会话，新 response 清理旧 Ticket，pending 时禁用新输入，取消显示明确无副作用结果；工具表补 risk/side effect。Analytics 的 Run cohort 连接全部 Steps/Tools；Feedback 对全局 key 与 Run 获取排序 advisory locks。Seed 要求 Fake Embedding 并复用六份虚构知识 fixture。相关 UI、API、Analytics、Service Desk 和 seed 测试补齐上述正常与失败合同。
- **必要回归命令：** `.venv/bin/python -m pytest -q tests/unit/ui tests/integration/api/test_analytics.py tests/integration/api/test_service_desk.py tests/integration/analytics/test_seed.py tests/integration/knowledge/test_migrations.py` → `14 passed in 2.79s`。
- **安装态 seed：** `.venv/bin/python -m pip install --no-build-isolation .` 成功；`.venv/bin/python -m scripts.seed_phase11_demo` → 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback，并且知识 Retriever 能找到 `Evaluation VPN Configuration SOP`。
- **正常实际演示：** 正式 FastAPI + Streamlit 启动后，通过 UI HTTP client 执行知识问答 → `completed`/1 Citation；执行工单请求并确认 → `executed`/Ticket `IT-20260801-000002`；随后 GET Run 的 Tool Execution 包含 `create_ticket`。实际浏览器 Chat 显示回答、completed、knowledge_question、5 Steps、0 Tool calls、最终采用的 Citation 与 Feedback 控件。
- **失败场景一：** wrong actor 取消 pending confirmation → HTTP 403，稳定错误 `confirmation_access_denied`；原 actor 随后取消完成清理。
- **失败场景二：** employee 读取 Analytics → HTTP 403，稳定错误 `analytics_access_denied`。
- **UI 渲染：** Streamlit AppTest：Chat 0 exception/title `IT Support Chat`；Dashboard 0 exception/title `Analytics Dashboard`。本轮浏览器自动化没有可靠触发 Dashboard radio 切换，因此没有把该动作伪记为通过；Dashboard 证据由既有实际截图、本轮 AppTest、实际 Analytics HTTP 和 PostgreSQL integration 组成。
- **全量测试：** 沙箱内标准命令首跑因 localhost PostgreSQL `Operation not permitted` 得到 `7 failed, 144 passed, 91 errors`；按相同命令获准访问隔离测试库后 `.venv/bin/python -m pytest -q` → `242 passed in 17.70s`，没有跳过或用 SQLite/mock 替代数据库语义。
- **最终门禁：** `.venv/bin/ruff check .` → `All checks passed!`；`.venv/bin/ruff format --check .` → `169 files already formatted`；compileall exit 0；pip check `No broken requirements found`；`git diff --check` exit 0。
- **安全与范围结论：** 没有数据库访问进入 UI，没有复制 Policy/统计状态机，没有真实 Provider/企业 Adapter/命令执行，没有过度设计或提前实现 Phase 12。本地 actor/role 仍不等于生产认证，Dashboard 仍无 tenant/大数据性能保证，Feedback comment 仍缺生产 PII 生命周期；这些是明确边界，不是 Phase 11 未完成项。
- **阶段结论：** 所有 Blocking 和必要 Important 已关闭，工程 **PASS**；总体 **CONDITIONAL PASS**，项目所有者需要独立回答本报告 10 道面试题并完成 30–60 分钟练习。建议 Commit `fix(ui): close phase 11 acceptance gaps`；学习验收后建议 Tag `phase-11-complete`。
- **停止条件：** 本次到此停止，不进入 Phase 12。

---

## Phase 12：部署、CI、安全检查和作品集包装

### Step 12.1：建立非 root 应用镜像与安全自动迁移编排

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 让 PostgreSQL/pgvector、数据库 migration、FastAPI 和 Streamlit 具有可复现的一键编排，同时避免每个应用进程启动时重复执行 migration。
- **接手事实：** 根目录 `AGENTS.md` 和 `docs/phase_reports/phase_12.md` 不存在；Git 基线为 `b882da7`，Phase 6–11 仍是既有未提交工作区。修改前只有 db Compose，没有应用 Dockerfile 或 GitHub Actions。Docker Desktop 未运行，`docker compose ps` 返回 Docker socket 不存在。修改前 Ruff/format 通过；全量测试因 localhost PostgreSQL 不可达得到 `7 failed, 144 passed, 91 errors`，与 Phase 11 记录的环境失败一致。
- **实际完成内容：** 新增 Python 3.12 slim 的 FastAPI 与 Streamlit Dockerfile，使用固定 UID/GID 非 root 用户；新增 `.dockerignore` 排除 Git、`.env`、虚拟环境、缓存、测试和本地产物；Compose 增加一次性 `migrate`、FastAPI `api` 和 Streamlit `ui`，PostgreSQL 健康后才迁移、迁移成功后才启动 API、API ready 后才启动 UI；端口仅绑定 localhost，知识文件与 Evaluation artifact 使用命名卷。
- **Migration 安全边界：** 新增 `python -m scripts.run_migrations`；自动执行前要求仓库只有一个 Alembic head，数据库已在 head 时明确 no-op，否则只运行 `upgrade head`，执行后再次核对实际 head。脚本不执行 downgrade、drop、reset、seed 或任意 SQL，也不嵌入每个 Uvicorn/Streamlit 进程。
- **新增或修改文件：** `docker/Dockerfile.api`、`docker/Dockerfile.streamlit`、`.dockerignore`、`compose.yaml`、`scripts/run_migrations.py`、`docs/project_journal.md`。
- **运行与验证命令：** `docker compose config --quiet`；`.venv/bin/ruff check docker scripts/run_migrations.py`；`.venv/bin/python -m compileall -q scripts/run_migrations.py`。
- **真实结果：** Compose 配置解析 exit 0；Ruff `All checks passed!`；migration 脚本编译 exit 0。Docker daemon 当前未运行，因此镜像 build、migration 实际 no-op 和完整 Compose 启动仍待恢复 Docker 后验收，当前不宣称运行通过。
- **当前限制：** 默认 Compose 凭证是明确的本机占位值，不适合公网或生产；本项目没有生产 secret manager、TLS、SSO 或集群 migration lock，这些保持在作品集 MVP 边界外。
- **与下一步骤的关系：** 下一步建立 GitHub Actions，把 lint、真实 PostgreSQL 测试、migration drift、Evaluation、安全 secret scan 和两个镜像 build 固定为独立门禁。

### Step 12.2：建立 GitHub Actions 质量、安全与镜像门禁

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 让每次 push/PR 自动验证代码质量、真实数据库行为、migration 漂移、Evaluation 安全回归、secret 泄漏和镜像可构建性。
- **实际完成内容：** 新增只读 `contents` 权限与并发取消策略的 CI；Quality job 运行 Ruff lint/format、compileall 和 pip check；pytest job 使用官方 pgvector PostgreSQL 17 service，并显式创建隔离 test database；Migration job 连续运行两次安全迁移入口并执行 `alembic check`；Evaluation job以 Fake Model/Embedding 运行正式 30-case gate；Secrets job 用完整 Git history 执行 Gitleaks；Docker matrix 分别构建 FastAPI 和 Streamlit 镜像但不推送。
- **安全设计：** CI 数据库密码是只用于临时 service 的明确占位值，不是 repository secret；外部 Model/Embedding 保持 Fake；workflow 不申请写权限、不发布镜像、不自动部署；Gitleaks 禁用 PR 自动评论以保持最小副作用。
- **新增或修改文件：** `.github/workflows/ci.yml`、`docs/project_journal.md`。
- **运行与验证命令：** Ruby YAML parse；`.venv/bin/ruff check .github scripts/run_migrations.py`；`git diff --check -- .github/workflows/ci.yml docker compose.yaml scripts/run_migrations.py .dockerignore`；检查本机 `actionlint` 与 `gitleaks` 可用性。
- **真实结果：** Workflow YAML 解析成功；Ruff `All checks passed!`；Git whitespace exit 0。本机没有 `actionlint` 或 `gitleaks`，Docker daemon 也未运行，所以 action schema、secret scan、数据库 jobs 和镜像 jobs 尚未在当前机器实跑，不能据静态配置宣称 CI 已通过。
- **版本依据：** 采用当前官方文档展示的 `actions/checkout@v6`、`actions/setup-python@v6`、`docker/setup-buildx-action@v4`、`docker/build-push-action@v7`，以及 Gitleaks Action 最新稳定 `v2.3.9`；后续仍应由 Dependabot 或人工定期审查 action 供应链版本。
- **与下一步骤的关系：** 下一步按 Phase 12 威胁清单增加专项安全测试，重点覆盖 Prompt Injection、跨 actor/role 越权、上传边界、敏感日志和任意代码工具禁止规则。

### Step 12.3：补齐 Prompt Injection、上传与仓库安全回归

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 把安全清单转成可重复执行的行为与静态门禁，确认不因用户输入或知识内容执行任意工具，并收紧上传声明类型。
- **实际完成内容：** 新增两类 Prompt Injection 用例：用户要求忽略指令并调用 `run_shell_command` 时必须升级且零工具调用；检索 Chunk 内的注入文本只能作为 JSON user Context，System Prompt 明确其为不可信数据，最终回答不执行或回显任意命令。上传 API 现在要求 `.txt/.md/.markdown/.pdf` suffix 与 allowlisted media type 匹配，并新增伪装 Shell 文本的 415 回归；原空文件、超限和损坏 PDF 用例改用真实声明类型，仍保留各自业务失败语义。
- **仓库安全门禁：** 新增 `python -m scripts.check_security_boundaries`，扫描 tracked 与未忽略待提交文件中的高置信 API key/private key 形状和误纳入的 `.env`；使用 AST 扫描 `apps/` 与 `src/`，禁止 `eval`、`exec`、`os.system`、`os.popen` 和 `subprocess` 进入应用运行时。该脚本加入 CI Quality job。测试/开发脚本仍可进行受控 Git 子进程检查，不成为 Agent Tool。
- **既有越权与脱敏证据：** 当前套件已覆盖 Conversation role 变化、Agent Run role mismatch、Ticket ownership、wrong actor confirm/cancel、employee audit/analytics、非 approver/self approval、Gateway permission denial、日志 DB URL/Bearer/API key 脱敏，以及工单/audit provider 异常清理；不重复实现第二套授权系统。
- **新增或修改文件：** `knowledge/routes.py`、Agent Runtime/RAG/API tests、`scripts/check_security_boundaries.py`、CI workflow、`docs/project_journal.md`。
- **运行与验证命令：** 聚焦 RAG/Runtime/Gateway/logging pytest；security boundary script；相关 Ruff lint/format；搜索所有 multipart fixture media type。
- **真实结果：** 聚焦测试 `58 passed in 2.02s`；security boundary `security boundary checks passed`；相关 Ruff `All checks passed!`，5 个文件 format check 通过。上传 MIME HTTP 用例与既有 PostgreSQL 越权套件仍待数据库恢复后合并验收。
- **限制说明：** Prompt Injection 测试证明当前确定性图和 Gateway 不会把两种已覆盖注入变成工具执行，不等于对所有语言和编码攻击的形式化证明；“真实公司数据”无法仅靠正则完整判定，最终还需人工审查全部 fixture、截图和文档并明确它们是虚构数据。
- **与下一步骤的关系：** 下一步做可证明的无用/重复文件审查，然后集中完成 README 与三份作品集材料。

### Step 12.4：清理可证明无用的预留入口并保留有效模块

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 删除不会运行且会误导读者的占位代码，同时避免把未提交业务模块或历史评估入口误判为重复实现。
- **实际完成内容：** 确认 Git 没有跟踪 `__pycache__`、`.DS_Store`、pytest/Ruff cache、egg-info 或本地 Evaluation artifacts；Ruff 全仓无未使用 import/变量。`apps/worker/__init__.py` 只有“未来预留”docstring、没有任何引用或入口，因此删除该空 package；`scripts/evaluate_retrieval.py` 与 `scripts/run_evaluations.py` 分别承担 Retrieval-only 与完整 Agent Evaluation，不是重复模块，予以保留。
- **删除文件：** `apps/worker/__init__.py`。本步骤不删除用户的 Phase 6–11 未提交代码、迁移、测试、报告或截图。
- **运行与验证命令：** `git ls-files` 生成物扫描；全仓 worker 引用扫描；检查 worker 文件大小和实际内容；既有 Ruff 全仓基线。
- **真实结果：** 未发现被 Git 跟踪的缓存/构建产物；worker 只有 52-byte 占位 docstring且无代码引用。未发现第二个可在不改变行为的前提下安全删除的业务模块。
- **与下一步骤的关系：** README 将移除已删除 worker 的目录说明，并以最终 Compose、CI、安全和评估事实重写；随后创建面试、演示和简历材料。

### Step 12.5：完成 README 与求职作品集材料初稿

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 让新用户可以按真实入口启动项目，并让面试、演示和简历描述与当前代码、测试和 Mock 边界一致。
- **实际完成内容：** 重写 README，覆盖项目背景、业务问题、功能、Mermaid 架构、技术栈、目录、Docker/本地启动、Demo、RAG、Agent、Tool Gateway、observation、Policy/审批、幂等、Evaluation、CI、安全、当前结果、限制与规划；删除旧 worker/Phase 11 停止点和“尚无 CI”描述。新增面试指南，包含用户指定的 12 个主题及 Codex 辅助责任边界；新增 5 分钟 Demo 时间轴，覆盖 VPN 问答、Outlook Mock 诊断、确认建单、审计、Dashboard 和 Evaluation；新增 AI 应用、AI 产品、数据分析各 3 条量化简历 Bullet。
- **真实性规则：** 所有数字来自当前仓库的 13 个 migration、7 个只读 Mock tools、30-case 数据集、240+ 测试和最后确认的 Evaluation 指标；不声称真实企业集成、生产业务提升、真实员工满意度或生产 SLA。简历文档明确要求最终用 Phase 12 实际通过数替换 `240+`。
- **新增或修改文件：** `README.md`、`docs/interview_guide.md`、`docs/demo_script.md`、`docs/resume_bullets.md`、`docs/project_journal.md`。
- **运行与验证命令：** 检查四份文档的必需二级标题；核对 Demo actor、endpoint、脚本和 mock tool 名称；`git diff --check` 检查文档 whitespace。
- **真实结果：** 用户列出的 README、面试、Demo 和三方向简历主题均存在；文档 whitespace exit 0。README 中 Phase 12 最终结果仍引用后续 `phase_12.md`，需要在完整 Docker/测试/Evaluation 验收后填入最终数字和判定。
- **与下一步骤的关系：** 下一步恢复 Docker/PostgreSQL，执行 migration、上传安全、越权、全量 pytest、Evaluation、secret scan、镜像与 Compose 端到端验证，并依据真实结果修正文档。

### Step 12.6：完成 Docker、迁移、secret scan 和 README 命令实跑

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装。
- **完成日期：** 2026-08-05
- **本步骤目标：** 恢复真实 Docker/PostgreSQL 环境，证明镜像、Compose、重复 migration、seed、Evaluation 和 secret scan 不是只有静态配置。
- **实际完成内容：** Docker Engine 恢复后构建 FastAPI/Streamlit/migrate 镜像；启动 db/migrate/api/ui 完整依赖链；检查 API/UI 非 root、三个健康端点、迁移日志和重复 no-op。下载 Gitleaks v8.30.1 官方 Darwin arm64 release，在执行前用官方 checksum 验证 SHA-256；首轮 worktree 发现 5 个候选，核对为 `.venv` 第三方 source map 和 3 条显式测试幂等值，新增 `.gitleaks.toml` 仅精确排除这些非密钥项，保留默认规则。
- **发现与修复：** README seed 首跑失败，因为 Evaluation fixture 仍在 `tests/fixtures/knowledge`，而镜像不复制 tests。将 6 份虚构知识迁至 `data/evaluation/knowledge`，更新测试、PDF 生成脚本和 Evaluation fixture 路径；没有把测试代码打进生产镜像。重建后 seed 连续两次计数完全一致，容器 Evaluation Gate PASS。Streamlit 增加 localhost browser address，启动日志不再显示外部地址。
- **运行与验证命令：** `docker compose build api ui migrate`；`docker compose up -d`；`docker compose ps -a`；容器 `/health`、`/ready`、`/_stcore/health`；`docker compose exec ... id -u`；`docker compose run --rm migrate`；容器 seed 两次；容器 Evaluation；Gitleaks `dir` 与 `git`。
- **真实结果：** 三镜像 build 成功；db/api/ui healthy，migrate exited 0；API/UI UID 均 10001；三个健康检查通过；重复 migration 输出已在 head；seed 两次均为 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；容器 Evaluation Gate PASS。最终 Gitleaks worktree 约 6.01 MB、3 commits 约 637 KB，均 `no leaks found`。
- **安全说明：** 没有用网络容器挂载私有仓库做扫描；release binary 在本地执行且 checksum 已验证。allowlist 没有排除整个 tests 或禁用 generic secret rule。
- **与下一步骤的关系：** 下一步修正 CI 环境隔离，执行最终 245 项全量、migration drift 和本地 Evaluation，并同步最终报告与状态文档。

### Step 12.7：完成最终 verification-loop 与 Phase 12 文档闭环

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（最终 verification-loop）。
- **完成日期：** 2026-08-05
- **本步骤目标：** 用原始范围、真实代码、全量自动测试、实际 Docker 行为、安全失败路径和文档一致性决定阶段是否可以收尾。
- **发现与修复：** 第一次最终 pytest 命令错误地全局设置 `IT_SUPPORT_ENVIRONMENT=test`，使 10 个验证 development 配置的单元测试被环境污染，得到 `10 failed, 235 passed`。删除 CI 顶层的该变量，只在 migration/evaluation jobs 设置 test；标准 pytest job 由各测试 fixture 决定环境。Fixture 路径迁移后，本地 Evaluation CLI 首次仍加载旧 site-packages；重新安装当前 package 后使用新路径通过。`migrations/env.py` 的 drift 过滤只排除 LangGraph checkpoint saver 管理的表和既有显式 FTS index，没有生成删除 migration。
- **全量测试：** `.venv/bin/python -m pytest -q` → `245 passed in 17.98s`，使用真实隔离 PostgreSQL/pgvector；没有跳过或改用 SQLite。
- **最终门禁：** Ruff `All checks passed!`；format `170 files already formatted`；compileall、pip check、security boundary、Git whitespace 通过；最终 Gitleaks worktree 约 6.17 MB 与 3 commits 均 `no leaks found`；安全 migration 连续两次 no-op；`alembic check` → `No new upgrade operations detected.`。
- **Evaluation：** 重装当前 package 后 `eval-20260805T141357Z-046e52d7` Gate PASS；Recall@3/5 1.0/1.0、MRR 0.8333、Citation/Evidence 1.0、Unsupported Claim 0、Refusal 0.7778、Intent/Tool/Workflow 1.0、Prohibited Action 0。失败仍是 `knowledge-07/08`；previous-run 因 `knowledge_corpus_fingerprint_changed` 不可比较。
- **文档闭环：** 更新 README、Project Overview、Roadmap、Backlog、Current State 和三份作品集材料；新建 `docs/phase_reports/phase_12.md`。旧 Backlog 的安全 Phase 12 与 Docker Phase 13 按本次明确指令合并为最终 Phase 12，不再保留一个虚假的待实施 Phase 13。
- **阶段判断：** 仓库内实现和本地工程门禁 PASS，没有剩余 Blocking 代码缺口。GitHub-hosted workflow 因当前没有 commit/push 尚无 run，因此总体为 **CONDITIONAL PASS**，不能声称远端 CI 已绿。Phase 6–12 共处未提交工作区，本轮不擅自 commit 或 push。
- **建议版本：** Commit `feat(delivery): complete phase 12 portfolio release`；首次 GitHub-hosted CI 通过后 Tag `phase-12-complete`。
- **停止条件：** 本次到此停止，不自动开始新的 Phase 或生产集成。

### Step 12.8：建立根目录工作规则并收敛 Phase 6–12 Git 历史

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（版本收尾）。
- **完成日期：** 2026-08-05
- **本步骤目标：** 修复根目录缺少 `AGENTS.md` 和 Phase 6–12 长期共处未提交工作区两个交付缺口，不通过删除文档表述掩盖事实。
- **实际完成内容：** 新建根目录 `AGENTS.md`，固定 repo-first 阅读顺序、Phase scope、LLM/确定性系统边界、Tool Gateway 禁止项、真实 PostgreSQL/migration 规则、Phase 验证命令、journal/Current State/Phase report 更新要求和 Git hygiene。保留 journal 中各 Phase 当时“AGENTS 缺失/工作区未提交”的历史记录，只更新 Current State 与 Phase 12 最终报告的当前事实。
- **Git 策略：** 由于 Phase 6–12 修改跨越相同 composition root、配置、README、Roadmap、Context 和 journal，无法从最终工作区可靠重建七个互不重叠的历史 diff；按项目所有者本次明确要求使用一个诚实的阶段收尾提交 `feat(delivery): complete phases 6-12`，不伪造逐 Phase commit。提交前重新检查完整 status、whitespace、安全边界和 secret scan；不 push、不 tag。
- **最终状态：** Phase 6–12 的代码、迁移、测试、Evaluation、UI、Docker、CI、安全检查、作品集材料与 `AGENTS.md` 一并进入本地提交；提交完成后工作区应为 clean。GitHub-hosted CI 仍需 push 后确认。
- **停止条件：** 完成本地 commit 与 clean-worktree 复核后停止，不自动 push 或开始新 Phase。

### Step 12.9：逐项重建 Phase 12 验收矩阵并完成双轴代码审查

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（收尾验收）。
- **完成日期：** 2026-08-05
- **本步骤目标：** 不以“代码可运行”代替验收，对照原始任务、验收标准、代码、测试和运行证据逐项检查，并先列出问题再修改。
- **审查方式：** 以 `b882da7` 为固定点，分别执行 Standards 与 Spec 两轴审查；同时核对当前 `8754eb0` 阶段提交、工作区、Phase 12 原始任务、README、Current State、Phase report、CI 和测试。
- **发现的问题：** Blocking：Evaluation CI 新建隔离测试库后直接运行 Evaluation，没有先 migration；外部 Blocking evidence：GitHub-hosted workflow 尚未 push/run，不能声称 CI 全绿。Important：`pyproject.toml` 误写 `httpx2`；FTS expression index 被 Alembic drift 排除但没有独立 contract check；README/状态/报告仍写 3 commits、245 tests 或“没有提交”。Optional：Streamlit 镜像安装完整后端依赖、CI compileall 未覆盖 tests。
- **范围判断：** 未发现真实企业 Adapter、后续 Phase 功能、任意 Shell/Python/SQL Tool、第二套重复授权或可以安全删除的业务重复模块。Optional 镜像瘦身不影响本 Phase 正确性或安全，因此不处理。
- **结果：** 明确修复全部 Blocking 代码问题和必要 Important；托管 CI 作为外部证据缺口保留，不用本地结果冒充。

### Step 12.10：修复 CI、依赖和 migration contract 的必要问题

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（收尾修复）。
- **完成日期：** 2026-08-05
- **实际完成内容：** Evaluation job 新增数据库 migration step；Quality compileall 与仓库标准统一覆盖 tests；将 `httpx2` 改为 API 镜像/Evaluation CLI 所需的 direct runtime `httpx>=0.28,<1`。保留 PostgreSQL FTS expression index 的 Alembic autogenerate exclusion，但明确其由安全迁移脚本负责；迁移首次升级和已在 head 的 no-op 两条路径都从 PostgreSQL catalog 核验表、GIN access method 和关键表达式 token。
- **失败路径测试：** 新增 3 个单元测试，分别验证正确 FTS contract、索引缺失、access method/表达式错误；既有 integration migration test 继续验证真实索引存在。
- **修改文件：** `.github/workflows/ci.yml`、`pyproject.toml`、`migrations/env.py`、`scripts/run_migrations.py`、`tests/unit/test_run_migrations.py`。
- **运行与真实结果：** 新单测 `3 passed`；现有迁移 integration 合并执行 `4 passed`；`IT_SUPPORT_ENVIRONMENT=test python -m scripts.run_migrations` 输出数据库已在 head，显式 contract 核验通过；`alembic check` 为 `No new upgrade operations detected.`；当前 package 重装后 `pip check` 为 `No broken requirements found.`。
- **设计边界：** 没有把复杂 PostgreSQL expression index 强行建模进无法稳定 round-trip 的 ORM metadata；也没有增加 downgrade、drop、repair 或自动重建索引。发现漂移时 fail closed，由人工 migration 修复。

### Step 12.11：用全新 Compose 数据卷完成启动、演示和失败场景验收

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（实际运行验收）。
- **完成日期：** 2026-08-05
- **隔离方式：** 使用 Compose project `itagent_phase12_closeout`、独立端口 55432/58000/58501 和全新命名卷，不复用原项目数据库；从零 build API/UI/migrate 镜像。
- **Docker 与迁移结果：** build 成功；首次日志为 `database migrated to Alembic head 20260801_0013`；db/api/ui healthy，migrate exited 0；再次运行 migrate 输出 `database already at Alembic head 20260801_0013`。干净镜像安装日志明确安装 direct `httpx-0.28.1`。
- **幂等与 Evaluation：** `seed_phase11_demo` 连续两次均返回 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback；容器 Evaluation `eval-20260805T144218Z-10e57dc0` Gate PASS，Recall@3/5 1.0/1.0、MRR 0.8333、Citation/Evidence 1.0、Unsupported Claim 0、Refusal 0.7778、Intent/Tool/Workflow 1.0、Prohibited Action 0。
- **正常演示：** VPN knowledge question completed 且返回 1 个 Citation；Outlook diagnosis completed，执行 `get_account_status`、`get_mail_service_status`、`search_existing_incidents`、`search_knowledge`；原 actor 确认后本地 Ticket executed；Audit 有 11 条事件；Analytics 返回 200。
- **失败演示：** wrong actor confirm → 403 `confirmation_access_denied`；employee Analytics → 403 `analytics_access_denied`；PDF suffix + text media type → 415 `unsupported_document_media_type`。
- **临时资源：** 验收后已删除 `itagent_phase12_closeout` 的容器、网络和三个命名卷；复核原 `itagent` db/api/ui 仍全部 healthy，原项目数据未动。

### Step 12.12：完成 248 项最终门禁与收尾文档同步

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（最终收尾）。
- **完成日期：** 2026-08-05
- **最终命令与结果：** Ruff lint `All checks passed!`；Ruff format `171 files already formatted`；compileall 覆盖 apps/src/scripts/migrations/tests；`pip check` 无 broken requirements；security boundary PASS；全量 pytest 使用真实 PostgreSQL/pgvector，`248 passed in 18.18s`。
- **Secrets：** Gitleaks v8.30.1 扫描 4 个 Git commits 约 1.59 MB 与最终 worktree 约 6.20 MB，均 `no leaks found`；没有扩大 allowlist。
- **文档同步：** 更新 README 当前功能/迁移说明/测试与 Evaluation 结果、Project Overview、Current State、Phase 12 report、Backlog 和 resume bullets；修正提交状态、4-commit scan、248 tests、新 Evaluation run 与 hosted CI 未运行的事实。
- **阶段判断：** 已知 Blocking 工程问题全部修复，必要 Important 已修复，Optional 镜像瘦身未处理。总体 **CONDITIONAL PASS**：项目所有者需完成学习验收，且 push 后首次 GitHub-hosted CI 必须全绿；本轮不擅自 commit、push、tag 或开始下一 Phase。
- **建议版本：** Commit `fix(delivery): close phase 12 acceptance gaps`；学习验收和 hosted CI 均通过后 Tag `phase-12-complete`。

### Step 12.13：修复离线 Evaluation 的证据充分性回归

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（评估加固）。
- **完成日期：** 2026-08-11
- **问题与根因：** `knowledge-07/08` 会因问题中的 `VPN`、`Outlook`、`SOP` 等范围词检索到同主题文档，而本地 Fake RAG 只要收到任意 Context 就固定标记 `answerable=true`，使 Refusal Correctness 只有 `0.7778`。先将集成断言改为期望 `1.0`，真实得到 `0.7778 != 1`；修复探针随后暴露 `knowledge-02` 的正确 Troubleshooting Chunk 被无语义 Fake vector 噪声挤出 Top-5，旧的文档级 Recall 没有揭示这个分段证据缺口。
- **实际修复：** Fake RAG 先按问题的具体 subject terms 选择证据；只有所选片段支持具体事项才标记可回答，否则返回结构化拒答且不绑定 Citation。RAG 默认 Top-K 从 5 校准到 8，使当前小型演示语料中的正确分段能进入受控 Context；没有更改真实模型 Prompt、权限过滤、Citation 物化或 Tool Gateway。
- **新增失败路径测试：** 新增 Fake RAG “只有文档范围词重叠必须拒答”和“具体 subject 支持优先于通用介绍片段”两个单元测试；完整 Evaluation 集成测试要求 Refusal Correctness 为 `1.0` 且 `knowledge-07/08` 不再失败。
- **运行与真实结果：** 修复前定向集成测试按预期失败；第一次修复后 `knowledge-02` 失败并促成 Chunk 级诊断；最终定向集成测试 `1 passed in 6.14s`，新增单元测试 `2 passed in 0.34s`，相关 Ruff lint/format 通过。完整 30-case Evaluation 和全量门禁将在最终验证步骤记录。
- **限制：** 该规则只让 Fake provider 成为更可信的离线/演示替身，不证明任意真实模型同样拒答；真实 provider 仍必须显式授权并单独评估。Top-K=8 是针对当前小型演示语料的可解释校准，不宣称适用于大型生产知识库。

### Step 12.14：补齐 CI 供应链与受控依赖更新门禁

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（CI 加固）。
- **完成日期：** 2026-08-11
- **实际完成内容：** 将 checkout、Python setup、Gitleaks、Buildx 和 Docker build 五类第三方 Action 从可变 tag 固定到经 GitHub API 解析的完整 commit SHA，并保留 tag 注释供 Dependabot 识别；三处 CI pgvector service 固定到本机已验证的 `sha256:feb68f…33966` 镜像 digest。新增独立 Python dependency audit job，固定使用 `pip-audit==2.10.1`，按 `pyproject.toml` 隔离解析并 strict fail closed。新增 Dependabot 配置，按月为 pip、GitHub Actions 和 Docker 提交受控 minor/patch 更新，限制每类最多 5 个开放 PR。
- **为什么没有完整 lockfile：** 当前项目同时服务本地 Python、两个 Docker 镜像和教学型跨平台安装；本步骤没有在 Phase 12 收尾阶段引入新的锁定工具链。major-bounded project dependencies、干净镜像 build、pip-audit 与 Dependabot 共同构成当前作品集级策略，完整 hash lock 仍属于生产发布工程。
- **运行与真实结果：** GitHub API 成功解析 5 个官方 Action ref；本地镜像检查得到 pgvector digest，随后从 Docker Hub Registry 读取 OCI index，确认同一 digest 同时包含 Linux amd64/arm64，适用于 GitHub runner 和本机；workflow 与 Dependabot YAML 解析成功；扫描确认没有剩余 `uses: ...@v*` 可变引用；`python -m pip_audit . --strict` → `No known vulnerabilities found`；`docker compose config --quiet` exit 0。
- **限制：** 漏洞数据库结果具有时间性，必须依靠 hosted CI 和 Dependabot 持续重跑；这不是供应链签名、SLSA provenance 或生产安全认证。

### Step 12.15：以全新 Compose 数据卷完成最终演示验收

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（发布演示验收）。
- **完成日期：** 2026-08-11
- **隔离方式：** 使用 `itagent_phase12_release` Compose project、端口 55433/58001/58502 和三个全新命名卷，从零构建 API、migrate、UI 镜像；不复用原项目数据库。Compose 与 CI 的 pgvector 镜像均使用已验证 digest。
- **Docker 与 migration：** db/api/ui 全部 healthy，migrate exited 0；首次日志 `database migrated to Alembic head 20260801_0013`，第二次运行 `database already at Alembic head 20260801_0013`；API/UI 均以 UID 10001 运行；health、ready、Streamlit health 全部成功。两次 seed 均为 6 Runs、23 Steps、6 Tools、4 Tickets、4 Feedback。
- **正常演示：** `What is the approved VPN server address?` 返回 completed、1 个 Citation 和 `vpn.demo.invalid` 虚构地址；Outlook 错误诊断 completed，四个 Mock tools `get_mail_service_status`、`get_account_status`、`search_existing_incidents`、`search_knowledge` 均 succeeded；确认建单得到 `IT-20260811-000001`，重复确认返回相同 Ticket。
- **失败演示：** wrong actor 确认 → 403 `confirmation_access_denied`；employee Dashboard → 403 `analytics_access_denied`；`.docx` + octet-stream 上传 → 415 `unsupported_document_media_type`。Audit 返回 9 条、其中 1 条 deny；支持角色 Dashboard 返回 41 Runs、5 Tickets、1 条最近 Evaluation。
- **Evaluation：** 容器 run `eval-20260811T124452Z-a5973f16`，Gate PASS、失败案例 `[]`；Recall@3 1.0、MRR 0.9167、Citation Validity 1.0、Refusal Correctness 1.0、Prohibited Action Rate 0。该 run 使用 Fake model/embedding 与 30 条虚构案例。
- **UI 可见性：** 使用本地浏览器实际打开 Streamlit Chat 和 Analytics Dashboard；Chat 输入、模拟身份、页面切换可见，Dashboard 显示 Tickets、Self-service、Human transfer、Tool success、Satisfaction、Steps、Tool calls、Latency、图表与 Recent Evaluation。未发现浏览器 console error；存在 Altair/Vega 对空或离散数据的非阻断 warning，不作为本 Phase Blocking。
- **发现的文档偏差：** 原 Demo 问句 “connecting from home” 实际只命中 VPN Overview，不足以展示配置步骤；最终演示改用固定评估集中的 approved server address 问句，确保回答与引用片段一致。
- **临时资源清理：** 验收后已删除 `itagent_phase12_release` 的容器、网络和三个命名卷，可恢复性为无（仅含本次虚构临时数据）。原 `itagent` 测试数据库容器保持 healthy；其 API/UI 在本步骤开始前即处于 exited 状态，本步骤未修改原卷。

### Step 12.16：完成 251 项最终门禁、漏洞与 secrets 扫描

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（发布门禁）。
- **完成日期：** 2026-08-11
- **首次全量发现：** 在证据充分性修复后，第一次全量得到 `1 failed, 249 passed`：原有 Account FAQ 问题使用复数 `passwords`，证据使用单数 `password`，窄词法判断误拒答。没有放宽断言；新增有限、可解释的英文复数 `-s` 归一化，并新增单复数回归单测。定向三类知识 API + 3 个 Fake RAG 单测随后 `6 passed`。
- **最终全量：** `.venv/bin/python -m pytest -q` → `251 passed in 17.31s`；Ruff lint `All checks passed!`；format `172 files already formatted`；compileall、pip check、security boundary、Git whitespace 全部通过；migration 在 `20260801_0013` no-op。
- **依赖与 Evaluation：** `python -m pip_audit . --strict` → `No known vulnerabilities found`；Evaluation `eval-20260811T125222Z-6a3c661e` Gate PASS、failed cases `[]`，当前 baseline 可比较。未调用真实 Model/Embedding API。
- **Secrets：** 从官方 GitHub release 下载 Gitleaks v8.30.1，校验 Darwin arm64 包 SHA-256 为 `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5`；worktree 约 6.53 MB 和当时 4-commit Git history 约 1.59 MB 均 `no leaks found`。发布 commit 后必须重扫新增 history 才能 push。
- **文档同步：** README、Project Overview、Current State、Phase report、Demo script 和 resume bullets 已更新到 251 tests、零失败 Evaluation、MRR 0.9167、Refusal 1.0、dependency audit、pinned supply-chain refs 和真实 VPN server-address 演示问句；GitHub-hosted CI 状态仍保持待确认，未提前写成通过。

### Step 12.17：发布私有 GitHub 仓库并完成 hosted CI 闭环

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（GitHub 发布验收）。
- **完成日期：** 2026-08-11
- **Git hygiene：** 将尚未发布的 5 个提交重写为 GitHub noreply author/committer，移除原提交身份中的本机 LAN hostname；重写前后最终 tree 完全一致。建立私有仓库 `scout099/enterprise-it-support-ai-agent`，push `main` 与 `agent/phase-12-release`，并创建 Draft PR #1。仓库保持 private，没有未经确认切换为公开或创建 Tag。
- **首次 hosted 失败：** run `31494076726` 中两个 Docker build 与 dependency audit 通过；四个 Python jobs 因 `--no-build-isolation` 要求 runner 预装 `setuptools.build_meta` 而安装失败；Gitleaks Action 因最小只读 token 无权访问其请求的 PR 资源而报 `Resource not accessible by integration`。这些是 runner bootstrap/Action 权限问题，不是 pytest、migration 或泄漏检测结果失败。
- **必要修复：** 四个项目安装恢复标准 PEP 517 build isolation；Secrets job 不再使用需要额外 GitHub API 权限的 Action，而是下载固定 Gitleaks v8.30.1 Linux x64 release、校验官方 SHA-256 后直接执行 Git history 与 worktree 双扫描。继续保留 `contents: read`，没有增加写权限或自动评论。
- **最终托管结果：** commit `6e7589e` 的 PR run [`31494468543`](https://github.com/scout099/enterprise-it-support-ai-agent/actions/runs/31494468543) status `completed`、conclusion `success`。Python dependency audit、Migration safety and drift、Secret scan、Evaluation regression、Docker build (fastapi)、Ruff and package checks、Docker build (streamlit)、pytest with PostgreSQL and pgvector 共 8/8 jobs 通过。
- **GitHub 安全设置：** vulnerability alerts endpoint 返回 204；automated security fixes 返回 `enabled=true`、`paused=false`。仓库内 monthly Dependabot、hosted `pip-audit` 和 Gitleaks 继续作为独立 fail-closed 门禁。
- **最终本地重扫：** 重新下载 Gitleaks v8.30.1 Darwin arm64 官方包并核对 SHA-256 `b40ab0ae55c…aeb6a5`；最终文档工作区约 6.54 MB、6 commits history 约 1.63 MB，二者均 `no leaks found`。Ruff lint、format、repository security boundary 与 `git diff --check` 同时通过。
- **阶段影响：** hosted CI 外部证据缺口关闭，Phase 12 工程结论为 PASS。总体仍为 CONDITIONAL PASS 的唯一原因是项目所有者需独立完成学习验收；公开可见性和 `phase-12-complete` Tag 均不在未确认情况下执行。本步骤同步 README、Current State、Roadmap 与 Phase 12 report，不进入下一 Phase。

### Step 12.18：修复首次 Dependabot 运行暴露的更新策略偏差

- **所属 Phase：** Phase 12：部署、CI、安全检查和作品集包装（持续依赖维护收尾）。
- **完成日期：** 2026-08-11
- **实际发现：** Phase 12 PR 合并后，main CI run `31495296148` 8/8 success；随后平台首次执行三类 Dependabot 更新。pip 与 GitHub Actions job 成功，但 Docker job `31495301140` 因配置目录 `/` 下没有 Dockerfile 而以 `dependency_file_not_found` 失败，实际 Dockerfiles 位于 `/docker`。同时 GitHub Actions 和 pip 产生了 3 个 major-bound PR，证明 `groups.update-types` 只决定分组，不会禁止未分组的 major update，与文档所述“只提出 minor/patch”不一致。
- **必要修复：** Docker ecosystem directory 改为 `/docker`；pip、GitHub Actions 和 Docker 三类均显式 ignore `version-update:semver-major`，保留 monthly、minor/patch group 和每类最多 5 个开放 PR。不会自动合并已产生的 major PR；待配置进入 main 后关闭这些不符合当前策略的 bot PR。
- **验证状态：** YAML 解析、Ruff、security boundary、Git whitespace 和 hosted CI 将按同一发布门禁重跑；Docker Dependabot 的下一次平台运行结果在本步骤后续补充，不用静态配置代替托管证据。
