# Investix — Design Specification

**Status:** approved for technical planning
**Date:** 13 October 2026
**Source specification:** `PRD.md`, version 0.1

## Objective

Build a private, self-hosted, reproducible Docker application for managing a personal portfolio. The Investix database is authoritative; historical exports are used only for one-time import and read-only reconciliation.

## Architecture

- React + TypeScript frontend, served with the private application.
- FastAPI backend: authenticated API, ledger/performance domain, import workflow, and provider adapters.
- Persistent PostgreSQL: ledger, configuration, instruments, price/FX observations, imports, and audit data.
- Separate worker: EOD updates, historical backfill, staleness checks, and future configurable refresh frequencies.
- Docker Compose on the Mac mini, portable to a Docker homelab without architectural changes. Private access through Tailscale; no Internet exposure by default.

The frontend reads persisted snapshots. When the worker saves a new value, FastAPI may notify the UI through WebSocket; the browser never calls external providers and never receives secrets. Any future intraday frequency is a worker policy and does not require a different frontend/backend architecture.

## UI and charts

- Approved direction: **Command center** — a dark, dense but readable dashboard with KPIs, primary performance, allocation, and drill-down to the register and performance views.
- Italian language, `it-IT` locale, EUR base currency; tabular numbers, visible focus, keyboard navigation, and states not conveyed by color alone.
- UI library: **Mantine Core** (MIT), without paid starter/template dependencies.
- Charts: **Apache ECharts** (Apache-2.0), with tooltip, legend, zoom/pan, range controls, filtered-data export, and accessible descriptions.
- Desktop is the primary experience; tablet is usable; mobile rearranges controls without overlap.

## Ledger, positions, and calculations

`operations` is an append-only ledger. A correction creates a revision and a cancellation preserves audit data and references; there are no untracked destructive deletions.

Each operation belongs to an account and an instrument. Input supports buy, sell, opening balance, dividend, fee, transfers, and documented adjustments/corporate events. Quantity, price, consideration, fee, and dividend preserve original value/currency and EUR values when available.

Fees and dividends are optional and nullable: absence is not converted into a stated zero. KPIs and reports therefore distinguish recorded amounts from incomplete coverage.

Positions and metrics are derived from the ledger and market observations:

- weighted average cost per ticker/account;
- realized P&L retained even when quantity reaches zero;
- unrealized P&L as current value minus residual open cost;
- total P&L split into recorded realized, unrealized, dividend, and fee components;
- daily flow-adjusted TWR, with end-of-day flows; dividends and fees included when recorded.

If required data is missing, return unavailable performance/CAGR with an explanation, never an artificial zero.

## Market data

Every `price_observation` stores provider, original symbol, market, currency, unit, acquisition timestamp, price field, raw value, normalized value, FX, and status.

Version 1 performs EOD updates. Public providers or scraping are allowed only for low-volume personal use, with caching, rate limiting, retry/backoff, provenance, and staleness metadata. An error never deletes the last valid value.

For a new instrument, the user defines or confirms ticker, exchange, currency, and unit; the adapter backfills from the first operation, allowing for non-trading days, and then enters the normal schedule. If coverage is insufficient, the system exposes the gap and allows backfill from another provider or CSV without inventing historical points. GBX is normalized to GBP before EUR conversion; historical series use historical FX.

## Historical import and reconciliation

Import is one-shot and does not introduce future synchronization with external sources.

1. Parse the exported input and preserve source row, timestamp, and hash.
2. Show a preview with counts, ranges, duplicates, errors, currencies, and unrecognized rows.
3. Validate and map the data.
4. Import into staging and produce a report of accepted/rejected rows and reasons.
5. Reconcile ticker/account quantities, residual cost, realized P&L, recorded dividends, benchmarks, coverage, and gaps.
6. Finalize idempotently only when there are no unmapped rows, ambiguous currencies/units, or discrepancies beyond the documented tolerance.

The 13 October 2026 verification confirmed the `STOCKS-26` workbook, its six sheets, and the recorded identifiers. The known discrepancy remains: SETUP refers to columns N:O, while the ledger header places `QUOTE SYMBOL` and `QUOTE CURRENCY` in M:N. Import always follows the effective headers M:N.

## Security and operations

- Authentication is required even for a single user; sessions and providers remain server-side.
- No broker integration or trading; store only the portfolio data required by the application.
- Server-side validation and logs without tokens or secrets.
- HTTPS on untrusted networks; default access limited to LAN/VPN.
- Persistent PostgreSQL volume, configurable backup retention, export, and restore verification in a temporary database.
- Health checks for the app, database, and worker; last provider update and backup status are inspectable.
- Quotes and P&L are informational, not advice or guaranteed execution prices.

No broker/bank integration, cash management, trading, multi-user access, public exposure, streaming/intraday service, financial advice, or bidirectional synchronization with external sources.

More frequent refresh remains a future extension supported by the architecture but not a functional requirement of version 1.

## Tests

- Ledger tests: buys, partial/full sells, repurchases, average cost, P&L, optional dividends/fees, splits, FX/GBX, TWR, and CAGR.
- Import tests: schema, incomplete rows, invalid dates/currencies, formula/errors, duplicates, idempotency, and reconciliation.
- Adapter tests: success, insufficient coverage, missing data, unknown symbol, rate limit, timeout, invalid value, and retry.
- PostgreSQL/migration tests, CRUD end-to-end tests, filters/ranges/charts, provider refresh, and backup/restore.

## Intentionally deferred decisions

- Specific initial provider: selected after coverage and licensing checks on real symbols, without enabling paid services without consent.
- Staleness thresholds, exact EOD schedules per market, reconciliation tolerances, and backup retention: defined in the technical plan and configuration rather than hard-coded.
- PNG export: evaluated with the ECharts implementation; CSV remains a confirmed requirement.
