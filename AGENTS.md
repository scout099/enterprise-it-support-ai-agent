# Repository Working Agreement

This file defines the operating rules for anyone changing the Enterprise IT Support AI Agent repository.

## Start with repository evidence

Before implementation:

1. Read `docs/PROJECT_OVERVIEW.md`, `docs/ROADMAP.md`, `docs/CURRENT_STATE.md`, `docs/project_journal.md`, and the current Phase report.
2. Inspect the relevant code, migrations, tests, `git status`, and recent commits.
3. Treat code and current test results as the source of truth when documentation differs, then repair the documentation.
4. Summarize the handoff and implementation plan before editing a new Phase.

Do not assume chat history contains the complete or current project state.

## Preserve Phase scope

- Implement only the Phase explicitly authorized by the project owner.
- Do not rebuild completed features or start a later Phase without confirmation.
- Prefer the existing modular-monolith seams over new services or infrastructure.
- Keep limitations explicit; never describe Mock, Fake, local identity, or simulated approval as a production enterprise integration.

## Architecture and safety boundaries

- Deterministic code owns authentication/authorization, role filtering, risk, routing, state transitions, Citation materialization, idempotency, confirmation, approval, and audit.
- LLM/model output, user input, uploaded files, retrieved context, and tool observations are untrusted inputs.
- Every Agent tool call must pass through the Tool Registry, strict input/output Schema, Policy, bounded timeout/retry, and Tool Execution audit.
- Do not add Shell, Python, SQL, `eval`, `exec`, `subprocess`, arbitrary-function, or unrestricted system-command tools.
- Do not connect real enterprise accounts or include real company data, employee data, credentials, API keys, or secrets.
- R3 approval remains simulated unless a later Phase explicitly authorizes and designs a real adapter.
- Do not persist or return private model reasoning or chain-of-thought.

## Database and migration rules

- PostgreSQL/pgvector behavior must be tested against the real isolated PostgreSQL test database; do not substitute SQLite or meaningless repository mocks for database semantics.
- Migrations must have one Alembic head and pass `alembic check`.
- Automatic migration may only move forward to `head`; it must be a no-op at head and must never automatically downgrade, drop, reset, delete volumes, or seed data.
- Keep development and test database URLs distinct.
- LangGraph checkpoint-saver tables are framework-owned; do not generate destructive application migrations for them.

## Required verification

Run checks proportional to the change. A Phase closeout normally requires:

```bash
docker compose up -d db
.venv/bin/python -m scripts.run_migrations
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m compileall -q apps src scripts tests migrations
.venv/bin/python -m pip check
.venv/bin/python -m scripts.check_security_boundaries
IT_SUPPORT_ENVIRONMENT=test .venv/bin/python -m scripts.run_evaluations
git diff --check
```

If localhost PostgreSQL access is blocked by the execution environment, restore approved Docker/localhost access and rerun. Do not weaken or skip the tests.

Before composition-root, CLI, seed, or Evaluation smoke tests after source changes, reinstall the current package:

```bash
.venv/bin/python -m pip install --no-build-isolation .
```

Tests and Evaluation must use Fake providers by default and must not call paid APIs without explicit authorization.

## Documentation and development record

- Append a real entry to `docs/project_journal.md` after each completed subtask. Record commands, actual results, problems, fixes, limitations, and the next dependency.
- At Phase completion, update `docs/CURRENT_STATE.md`, `docs/ROADMAP.md`, affected architecture/overview documents, and `docs/phase_reports/phase_x.md`.
- Keep README commands executable and aligned with the current API, Compose services, migrations, seed, Evaluation, and security boundaries.
- Use actual metrics and test counts. Do not claim hosted CI, browser behavior, production performance, or business improvements that were not observed.

## Git hygiene

- Preserve unrelated user changes and inspect the full staged diff before committing.
- Do not commit `.env`, secrets, caches, local knowledge uploads, Evaluation run artifacts, or build output.
- Use focused commit messages and do not push, tag, or open a pull request unless the project owner authorizes it.
- A clean worktree is not a substitute for tests, and a workflow file is not proof that GitHub-hosted CI has passed.
