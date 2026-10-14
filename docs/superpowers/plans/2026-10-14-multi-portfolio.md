# Multi-Portfolio Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow Investix to manage independent portfolios while preserving the existing ledger, market-data history, and single-user workflow.

**Architecture:** Introduce a first-class `Portfolio` entity and scope operational data, calculations, imports, API responses, and dashboard state by `portfolio_id`. Keep instruments and market observations shared across portfolios because prices are market facts; keep benchmark configuration global in phase 1 and add per-portfolio benchmark assignment only in phase 2.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16, React/TypeScript, Mantine, ECharts, pytest, Vitest, Docker Compose.

**Spec:** `PRD.md` (especially sections 4.1–4.5, 6, 7, and 8)

## Global Constraints

- Existing data must remain available in a seeded portfolio named `Principale`.
- No query or calculation may silently combine operations from different portfolios.
- Instruments and persisted market observations remain shared and provider-scoped.
- EUR remains the current base currency; `base_currency` is stored on the portfolio for future extension.
- Historical exports remain an import/reconciliation source, never a runtime dependency.
- Corrections and cancellations remain non-destructive and auditable.
- The first delivery does not include a consolidated “All portfolios” performance view.
- This plan does not introduce multi-user permissions; authentication remains single-user.

## Review Focus

- Existing operations are all assigned exactly once to `Principale`; no historical row is left unscoped.
- A portfolio filter cannot leak positions, accounts, operations, or performance points from another portfolio.
- Shared observations do not duplicate or overwrite prices merely because two portfolios hold the same instrument.
- An empty portfolio is represented correctly without fabricated zero values or unavailable P&L being reported as zero.
- Repeated imports are idempotent per portfolio and cannot be mistaken for an import into another portfolio.

## Decision Summary

### Recommended phase 1

Use `portfolio_id` on `operations` and `import_runs`; add a `portfolios` table; seed `Principale`; expose a global portfolio selector; scope portfolio, performance, quotes, operations, filters, and dashboard state.

Keep `accounts`, `instruments`, and `observations` shared. Accounts shown in a portfolio are derived from its operations. This supports a broker account being used by more than one portfolio without duplicating market instruments or prices.

### Deferred phase 2

- portfolio-specific benchmark assignment;
- consolidated “All portfolios” view;
- explicit account-to-portfolio membership rules;
- transfers between portfolios;
- portfolio-level sharing or multi-user authorization.

## File Map

**Create**

- `backend/alembic/versions/0008_portfolios.py` — create `portfolios`, backfill `Principale`, add and backfill `portfolio_id` columns and indexes.
- `backend/app/services/portfolios.py` — portfolio lookup, default selection, and serialization.
- `backend/tests/api/test_portfolios.py` — isolation and portfolio lifecycle tests.

**Modify**

- `backend/app/models.py` — add `Portfolio`; add `portfolio_id` to `Operation` and `ImportRun`.
- `backend/app/api/portfolio.py` — require/resolve portfolio context and scope positions.
- `backend/app/api/performance.py` — scope TWR and benchmark series by portfolio.
- `backend/app/api/quotes.py` — return instruments held by the selected portfolio only.
- `backend/app/api/operations.py` and `backend/app/services/operations.py` — create/list/revise/cancel within the selected portfolio.
- `backend/app/importing/finalize.py`, `backend/app/importing/stocks26.py`, and reconciliation modules — assign imports to a portfolio and make idempotency portfolio-aware.
- `backend/app/services/performance.py` — accept `portfolio_id` in portfolio-series construction.
- `frontend/src/api.ts` — add portfolio types, list/select calls, and `portfolio_id` to scoped requests.
- `frontend/src/App.tsx` — add the global selector and reset/reload dashboard and register state when it changes.
- `frontend/src/App.test.tsx` and backend API tests — cover selector and isolation behavior.
- `docs/operations.md` and `README.md` — document creation, selection, import target, and backup implications.

## Implementation Tasks

### Task 1: Lock the data model and migration contract

**Files:**

- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/0008_portfolios.py`
- Test: `backend/tests/api/test_portfolios.py`, migration/integration fixtures

**Interfaces:**

- Produce `Portfolio(id: int, name: str, base_currency: str, timezone: str, active: bool)`.
- Produce `Operation.portfolio_id` and `ImportRun.portfolio_id`, both non-null after backfill.

- [ ] Write a failing migration test proving existing operations are assigned to `Principale`.
- [ ] Write a failing constraint/index test for `(portfolio_id, trade_date)` and `(portfolio_id, account_id, instrument_id)`.
- [ ] Implement the migration with a transaction-safe seed, nullable backfill step, then non-null constraint.
- [ ] Verify upgrade/downgrade on a disposable PostgreSQL database.
- [ ] Commit `feat: add portfolio data model`.

### Task 2: Scope ledger and read APIs

**Files:**

- Modify: `backend/app/services/portfolios.py`, `backend/app/api/portfolio.py`, `backend/app/api/operations.py`, `backend/app/services/operations.py`
- Test: `backend/tests/api/test_portfolios.py`, `backend/tests/api/test_operations.py`, `backend/tests/api/test_portfolio.py`

**Interfaces:**

- `resolve_portfolio(session, portfolio_id: int | None) -> Portfolio` resolves an explicit ID or the seeded default for backward-compatible clients.
- Scoped endpoints accept `portfolio_id: int` after the frontend migration; missing IDs remain temporarily mapped to `Principale`.

- [ ] Add two portfolios and operations with the same ticker/account names; assert each API response contains only its own rows.
- [ ] Assert an empty portfolio returns empty positions and unavailable valuation, not zeros.
- [ ] Add portfolio list/create/read behavior with duplicate-name validation.
- [ ] Filter account and ticker choices from the selected portfolio only.
- [ ] Run the focused backend API suite and commit `feat: scope ledger by portfolio`.

### Task 3: Scope performance, quotes, and benchmarks

**Files:**

- Modify: `backend/app/services/performance.py`, `backend/app/api/performance.py`, `backend/app/api/quotes.py`
- Test: `backend/tests/api/test_portfolio.py`, `backend/tests/api/test_performance.py`, `backend/tests/api/test_quotes.py`

**Interfaces:**

- `portfolio_series(session, *, portfolio_id: int, ticker: str | None = None) -> PortfolioSeries`.
- `quotes(..., portfolio_id: int, days: int) -> QuotesSummary` returns only instruments held in that portfolio.

- [ ] Assert identical instruments in two portfolios reuse the same observation rows.
- [ ] Assert TWR and external flows differ when the portfolios have different operations.
- [ ] Assert active global benchmarks are currently visible in both portfolios but are calculated against each portfolio’s own series.
- [ ] Preserve the existing no-data/staleness semantics.
- [ ] Run focused service/API tests and commit `feat: scope portfolio analytics`.

### Task 4: Make imports portfolio-aware

**Files:**

- Modify: `backend/app/importing/stocks26.py`, `backend/app/importing/finalize.py`, reconciliation modules, import API/CLI
- Test: `backend/tests/importing/test_stocks26.py`, `backend/tests/importing/test_finalize.py`, `backend/tests/importing/test_reconcile.py`

- [ ] Require an import target portfolio in the finalize request, defaulting only for legacy one-shot imports.
- [ ] Change import idempotency from global `source_hash` to a portfolio-aware key, e.g. `(portfolio_id, source_hash)`.
- [ ] Assert the same source can be intentionally imported into two different portfolios while duplicate finalization in one portfolio is rejected.
- [ ] Produce an import report that includes portfolio name and accepted/rejected counts.
- [ ] Run import and reconciliation tests and commit `feat: route imports to portfolios`.

### Task 5: Add the frontend portfolio context

**Files:**

- Modify: `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/styles.css`
- Test: `frontend/src/App.test.tsx`, future `frontend/e2e/portfolios.spec.ts`

**Interfaces:**

- `api.portfolios() -> { items: Portfolio[] }`.
- All scoped API helpers accept `portfolioId: number`.

- [ ] Add a selector in the dashboard shell, defaulting to `Principale`.
- [ ] Reload portfolio, quotes, performance, worker context, and operations when selection changes.
- [ ] Reset portfolio-local ticker/account/date filters when changing portfolio.
- [ ] Show the selected portfolio in the page state and preserve it across dashboard/register navigation.
- [ ] Add an E2E test proving that switching portfolios changes positions, KPI values, and register rows without a full page reload.
- [ ] Run Vitest, build, and the focused Playwright flow; commit `feat: add portfolio selector`.

### Task 6: Quality gate and operational documentation

**Files:**

- Modify: `docs/operations.md`, `README.md`
- Test: full backend/frontend suite, migration/restart integration test, backup/restore test

- [ ] Run the full test suites with the documented Docker/DB environment.
- [ ] Verify a restart preserves portfolio selection, operations, and observations.
- [ ] Verify backup/restore preserves portfolio IDs and all scoped rows.
- [ ] Document the default portfolio, creation path, import target, and the fact that phase 1 has no consolidated view.
- [ ] Review API logs for accidental unscoped queries and run `git diff --check`.
- [ ] Commit `chore: document multi-portfolio operations`.

## Complexity and Scope Gate

Phase 1 is medium complexity: the migration and calculation scoping are the risk center; market observations require no duplication. It is appropriate for a separate feature branch and a dedicated review before implementation.

Do not start phase 2 until phase 1 has demonstrated isolated ledger/API results and a successful backup/restore. A consolidated view must be specified separately because summing portfolio values is easy but producing a defensible consolidated TWR and benchmark comparison is not.

## Future Decisions Required

1. Should `Principale` be renamed before migration, or remain the immutable default label?
2. Should accounts be globally reusable, or explicitly assigned through a `portfolio_accounts` relation?
3. Should benchmarks be global or selected per portfolio?
4. Is a consolidated “All portfolios” dashboard required?
5. Are transfers between portfolios required, or can they remain separate ledger events?
