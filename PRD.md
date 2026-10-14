# Investix — Product Requirements Document

**Version:** 0.1  
**Status:** Draft for user review  
**Date:** 13 October 2026
**Audience:** Codex and the product owner
**Product:** private web application for professional management of a personal portfolio

## 1. Vision

Investix is a reliable, professional personal web tool for recording transactions, understanding current and historical portfolio value, measuring gains and returns, and comparing them with configurable benchmarks. It runs in Docker containers with a persistent database and does not depend on external spreadsheet sources for future calculations or updates.

“Personal” describes the initial user and access model, not a compromise on quality: calculation consistency, traceability, error handling, interactive charts, security, and backup procedures are product requirements.

The Investix database is the authoritative source for operational data. Historical sources used for migration are only for import and reconciliation, never a runtime service or a second editable source.

## 2. User and success criteria

The initial user is a single investor managing instruments across multiple accounts. The portfolio may include stocks, ETFs, and cryptocurrencies present in the register. The base currency is EUR.

The solution succeeds when the user can:

- add, correct, and remove operations without maintaining formulas;
- view positions aggregated by instrument and drill down to individual accounts;
- distinguish value, realized P&L, unrealized P&L, dividends, and percentage return;
- explore charts for predefined or custom date periods and compare them with benchmarks;
- always see quote date and source, identifying missing or stale data;
- change provider without rewriting calculations or losing history;
- restore the database from a verified backup.

## 3. Scope

### Included in the first version

1. Private authenticated web application.
2. Aggregated dashboard, account detail, and instrument page.
3. Operations register with create, revise, audited cancellation, search, and filters.
4. Guided import of STOCKS-26 operations, settings, benchmarks, and extractable/verifiable historical data.
5. Scheduled EOD prices and FX updates through a selectable provider.
6. Interchangeable adapters for multiple providers behind a common interface.
7. Position, cost, P&L, return, and benchmark calculations.
8. Interactive charts, ranges, filters, and export of displayed data.
9. Configuration of instruments, symbols/markets, currencies, and benchmarks.
10. Docker Compose, persistent PostgreSQL, and documented backup/restore.
11. Automated tests for calculations, import, providers, and key user flows.

### Excluded from the first version

- Placing or executing broker orders.
- Automatic broker or bank-account connections.
- Cash-balance management, payments, or bank reconciliation.
- Financial/tax advice or investment recommendations.
- Multi-user access, roles, public sharing, or SaaS operation.
- Intraday quotes, streaming, or trading alerts.
- Operational dependency on external spreadsheet sources or bidirectional synchronization.

## 4. Functional requirements

### 4.1 Operations register

The register is the basis for reconstructing position quantities and cost. It must support at least buy, sell, opening balance, dividend, separate fee, and documented adjustment/corporate event when required.

Logical fields: trade date and, when useful, settlement date; account; ticker; ISIN; type; quantity; original price and currency when known; EUR consideration; EUR fees; EUR dividend; symbol and market; notes; unique identifier; status; and change history.

Cash-balance tracking is not required. Buys and sells are funded/settled outside the portfolio. The engine nevertheless records derived capital flows, not shown as held cash, to calculate returns correctly.

Operations must be correctable or cancellable. Deletions must be reversible or leave an audit trail. Every change recalculates positions and dependent metrics.

### 4.2 Positions and P&L

- Primary view aggregated by instrument with account-level detail.
- Weighted average cost per ticker/account as the initial method, consistent with the current register. Moving to FIFO requires an explicit decision and reconciliation.
- Realized P&L remains available even when residual quantity reaches zero.
- Unrealized P&L = current value minus residual cost of the open quantity.
- Total P&L exposes realized, unrealized, dividend, and fee components separately.
- A zeroed position does not delete history, cost, or realized P&L.
- Approximate initial dates or costs can be marked and accompanied by a note.

### 4.3 Return and benchmark

Percentage return must not be a simple final-versus-initial value ratio when buys or sells occur. The engine uses a flow-adjusted methodology (TWR or another selected and documented method) to exclude capital-flow effects from return while keeping them separate from absolute P&L.

Requirements:

- Documented formula for daily, cumulative, annualized/CAGR, and selected-period return.
- Buys/sells treated as synthetic capital flows only for performance purposes, not as cash management.
- Dividends and fees included or excluded explicitly and consistently for portfolio and benchmark.
- Benchmarks configurable with name, ticker, provider symbol, market, currency, active status, and price-return or total-return methodology.
- Series compared over the same interval and converted to EUR with consistent historical FX when required.
- ETF proxies, price-only indices, and methodological differences that reduce comparability must be highlighted.
- If initial dates or values are insufficient, show unavailable with an explanation, never zero or a misleading return.

### 4.4 Dashboard

The main screen shows:

- current total value, last-update timestamp, and data status;
- total absolute P&L and its components;
- returns for selected periods and CAGR when the period is long enough;
- aggregated positions with ticker/name, quantity, market value, EUR cost, P&L, percentage P&L, and weight;
- search and filters by instrument, account, asset type, and period;
- navigation from aggregates to underlying operations and accounts;
- clear loading, no-data, provider-error, and stale-quote states.

KPIs, tables, charts, and detail views must agree. The base currency is EUR; for instruments in other currencies, quote currency and FX contribution must be inspectable.

### 4.5 Charts, ranges, and filters

Charts are core functionality. The first version includes:

1. Portfolio value and total P&L over time, with selectable series.
2. Actual return against one or more configured benchmarks.
3. Return by instrument and comparison across instruments/accounts.
4. Allocation by ticker and account.

Ranges: 1M, 3M, 6M, YTD, 1Y, 2Y, 5Y, all available history, and custom from/to dates. The interface communicates limits caused by actual data coverage.

Interactions:

- filters for ticker, account, benchmark, and asset class with visible active-filter state;
- legend/controls to show or hide value, P&L, return, and benchmark;
- date tooltip with values, return, currency, and source/status;
- zoom, pan, or time-window selection with reset to the initial view;
- daily, weekly, or monthly aggregation when useful, respecting market calendars;
- percentage comparisons normalized at the start of the period; monetary series use scales that do not encourage invalid comparisons;
- CSV export of filtered points and, if supported by the selected library, image export;
- filters and ranges update KPIs and related data consistently and allow returning to the full view.

## 5. UX/UI design phase — gate before final UI

Before implementation of the interface, complete a design phase separate from functional implementation.

### Activities and deliverables

1. Write a design brief for a modern, dark, dense but readable financial dashboard.
2. Present 2–3 visual/layout directions for the dashboard, charts, positions table, and register.
3. Compare reusable templates/starter kits with custom layouts. Evaluate quality, maintenance, license, accessibility, responsiveness, customization, and dependencies.
4. Compare UI and chart libraries using the same criteria. Non-binding candidates: Tailwind/shadcn components, Mantine, or MUI; ECharts, Recharts, or TradingView Lightweight Charts. Selection requires verification of license, maintenance, accessibility, capabilities, and compatibility with required filters.
5. Prepare wireframes and a visual/navigable prototype for dashboard, chart with ranges/filters, position detail, and operation entry. Use synthetic or minimized data.
6. Present recommendation, trade-offs, and expected maintenance.
7. Obtain approval of style, layout, template, and libraries before building production UI.

### Visual and usability principles

- Professional dark theme with sufficient contrast; positive/negative states must not be distinguished by color alone.
- Analysis-tool information density, clear hierarchy, and readable numeric values.
- Desktop as the primary experience; tablet usable; mobile readable without overlapping controls or series.
- Keyboard navigation and visible focus for primary controls; understandable labels and tooltips.
- Italian language, it-IT locale, localized dates and numbers, EUR as base currency.
- Persistent preferences for theme, range, and benchmark if achievable without disproportionate complexity.

Gate: no final UI-kit, chart-library, or template choice and no production UI before prototype review and approval.

## 6. Market data and adapters

### 6.1 Common interface

The Investix domain does not call proprietary APIs directly. Each adapter normalizes:

- symbol and market search/verification;
- historical EOD series by symbol and date interval;
- latest available EOD value;
- historical FX series and latest FX value when provided;
- date/time, currency, unit, and status metadata;
- errors, limits, delays, rate limits, and service status.

The system allows multiple providers to be configured and tested. Each observation stores provider, original symbol, acquisition date, market, currency, unit, price field, and status. Changing provider does not silently overwrite data: comparisons and explicit rules prevent mixed or discontinuous series.

Updates are idempotent; retries use backoff and rate limiting; an error does not delete the last valid value. Stale data remains distinguishable and visible with a warning.

### 6.2 Frequency and history

- First version: daily EOD after the relevant market closes; no streaming/intraday data.
- The provider interface supports future updates, backfill, and gap recovery even when initial history comes from a frozen file.
- Schedule by market and time zone; do not assume US and European exchanges close at the same time.
- Normalized history is stored in PostgreSQL and validated before feeding KPIs and charts.

### 6.3 Currencies, units, and corporate events

- Preserve native price, currency, normalized price, FX used, EUR value, date, and FX source.
- Treat GBX (pence) separately from GBP (pounds): divide by 100 before EUR conversion.
- Use historical FX for historical valuations, not today’s FX retroactively.
- Handle splits and corporate events to avoid artificial jumps in quantity, cost, and return.
- Preserve raw and adjusted prices when available and document which one feeds each metric.
- Total return must include dividends or state that the series is price-only.

### 6.4 Provider selection

Coverage testing verifies real symbols and benchmarks, historical depth, FX, quote units, splits/dividends, API quota, retention, and licensing for personal display. No provider is considered pre-approved. A free plan is not automatically suitable or authorized because data is accessible from a browser.

## 7. Migration from historical sources

Migration uses frozen exports and reconciliation reports to materialize required operations and historical series in the database. After finalization, the database is authoritative and the import introduces no runtime dependency on the original source.

### Sources and mapping

- MOVIMENTI: input data such as date, account, ticker/ISIN, type, quantity, EUR price, fees, notes, currency/symbol; residual cost, average cost, and realized P&L are reconciled and rebuilt from the ledger whenever possible.
- SETUP: base currency, horizon, initial date, quote symbols/currencies, active benchmarks.
- _PRICE_HISTORY: date/price series by instrument and FX dates/rates, eligible for historical import when extractable and validatable.
- _PERFORMANCE: calculated series useful for reconciliation; it does not replace quotes required for recalculation.
- DASHBOARD: reference for KPIs, views, and charts, not the primary accounting source.

### Flow

1. Read/export without modifying the original source.
2. Show a preview: counts, ranges, duplicates, errors, currencies, and unrecognized rows.
3. Validate and map data.
4. Import into staging and produce a report of accepted/rejected rows and reasons.
5. Reconcile ticker/account quantities, residual cost, average cost, realized P&L, dividends, history, benchmarks, and reference values.
6. Confirm import while retaining a raw copy with date/version and hash.

Formulas and calculated values in the original source are moving data, not snapshots by definition. Import attempts to materialize static date/price/FX rows and checks coverage and gaps. If extraction is incomplete, it reports gaps and allows provider backfill without losing provenance.

Imports are repeatable without duplication through idempotency keys. Discrepancies beyond tolerance prevent finalization or require documented confirmation. The original source remains unchanged; after reconciliation it may be retained as a read-only archive/export. No bidirectional synchronization.

## 8. Proposed architecture

Initial proposal to turn into a technical plan after PRD approval:

- React + TypeScript frontend.
- Python + FastAPI backend, with a testable domain separated from provider adapters.
- PostgreSQL as the authoritative source; versioned migrations.
- Worker/scheduler for EOD updates, backfill, and checks.
- Docker Compose for application, worker, database, and TLS proxy in remote deployment.
- Environment/configuration-based settings; secrets excluded from repositories and images.
- Provider APIs called server-side only; the browser never receives keys.
- UI kit, chart library, and template remain UX/UI-gate decisions.

First release: single-user, private, and non-public by default. Hosting and remote access are decided later. No Internet exposure without authentication, TLS, and security updates.

## 9. Security and operations

- Authentication even for personal use; protected sessions and secrets outside code.
- No orders or broker access; store only the portfolio data required.
- Server-side validation and logs without tokens/secrets.
- HTTPS on untrusted networks; default access limited to LAN/VPN.
- Automatic database backups with configurable retention, export, and documented restore.
- Health checks for app, database, and worker; show latest provider update and backup.
- Quotes and P&L are informational, not advice or a guaranteed execution price.

## 10. Tests and acceptance criteria

### Required tests

- Unit tests for quantities, average cost, partial/full sales, repurchases, realized P&L, dividends, fees, splits, FX/GBX, TWR, and CAGR.
- Adapter tests with mocks for success, missing data, unknown symbol, rate limit, timeout, invalid data, and retry.
- Import tests for duplicates, invalid dates/currencies, formula/errors, incomplete rows, and idempotency.
- PostgreSQL/migration integration tests.
- UI end-to-end tests for operation CRUD, filters, chart ranges, benchmarks, refresh, and error states.
- Backup/restore test in a temporary database.
- Reconciliation against a frozen dataset with documented tolerances.

### Functional acceptance

1. Register changes update aggregates, accounts, P&L, and charts without technical spreadsheets.
2. Aggregated quantities equal the sum of valid operations.
3. A full sale sets quantity to zero while retaining realized P&L and history.
4. A large purchase does not appear as a positive return merely because invested capital increased.
5. Missing/stale prices are flagged and never presented as current.
6. Changing provider preserves verifiable history and provenance.
7. Ranges/filters update series and KPIs; benchmarks expose base, currency, and methodology.
8. Import produces reconciliation before becoming authoritative.
9. Compose starts the service; data persists across restarts; restore is verified.
10. Critical tests run with the documented command and pass.

## 11. Delivery phases

1. PRD review: confirm requirements, metrics, and assumptions.
2. UX/UI design: compare styles, templates, and libraries; prototype and approval.
3. Data proof: verify provider, licenses, symbols, imported history, FX, and corporate events.
4. Implementation plan: small, testable tasks for database, calculations, adapters, import, API, UI, and deployment.
5. Foundations: repository, Compose, schema/migrations, authentication, and tests.
6. Register and calculations: staging import, CRUD, positions, P&L, and performance.
7. Data: adapters, backfill, scheduler, FX, checks, and status.
8. UI and charts: implement after the design gate.
9. Reconciliation and private release: import, end-to-end tests, backup/restore, and hosting.

## 12. Assumptions and open decisions

### Initial assumptions

- Single user, personal use, private access.
- EUR as base currency.
- Daily EOD is sufficient for the first version.
- No cash balance; derived flows only for return calculations.
- Initial weighted average cost per ticker/account, consistent with the register.
- Database as the single source; historical files only for import, checking, and archive/export.
- FastAPI, PostgreSQL, React, and Docker Compose are the proposed technical base.
- Professional dark theme; UI kit, chart library, and template selected after design.

### Decide before the technical plan

- Hosting (Mac mini, NAS, VPS, or other) and remote access over LAN/VPN/Internet.
- Initial EOD provider, cost, and license terms.
- Final definition of TWR/total return, dividends, benchmarks, and approximate initial values.
- Correction/deletion and audit policy.
- Initial ranges/filters and need for PNG export.
- Style, components, chart library, and template after the prototype.

## 13. Glossary

- EOD: market end-of-day price.
- Realized P&L: profit/loss recognized on sold quantities.
- Unrealized P&L: profit/loss on quantities still held.
- TWR: return that neutralizes the effect of capital flows.
- Provider adapter: interface that normalizes provider responses into the Investix format.
- Staleness: age of a value relative to the expected market EOD session.
