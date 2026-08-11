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
