# Live Quotes Rate-Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add on-demand live market quotes that refresh while the dashboard is open, remain within Twelve Data Free limits, and continue to work when the portfolio exceeds eight tickers.

**Architecture:** Keep the existing worker and database observations for EOD/history. Add a server-side live quote service with a single-flight session, in-memory TTL cache, quota-aware batching, and no database writes. The frontend polls only while visible; the backend schedules batches of at most eight symbols and exposes freshness/status metadata.

**Tech Stack:** FastAPI, Python asyncio/thread-safe in-memory state, Twelve Data adapter, React/TypeScript, pytest, Vitest.

**Spec:** This plan is the implementation spec for the live-quotes decision; existing contracts are in `docs/operations.md`, `backend/app/providers/twelve_data.py`, `backend/app/services/market_data.py`, `backend/app/api/quotes.py`, and `frontend/src/App.tsx`.

## Global Constraints

- Twelve Data key remains server-side in `INVESTIX_TWELVE_DATA_API_KEY`.
- One symbol consumes one credit; a batch reduces HTTP requests but not credits.
- A batch contains at most 8 symbols and the scheduler consumes at most 8 credits per rolling minute.
- Live quotes are not persisted; existing EOD/history observations remain authoritative for historical calculations.
- The live session runs only while at least one dashboard client is active and expires after inactivity.
- The UI must distinguish `fresh`, `stale`, `pending`, `market_closed`, and `error` states.
- A provider quota/rate-limit response is a normal availability state, not an application error: keep the last valid quote, stop retries until the next allowed window, and show an actionable wait message.
- Daily budget reserves credits for EOD, retries, and manual refreshes; no automatic loop may spend the full 800-credit allowance.

## Review Focus

- Two browser tabs must not double the provider traffic; test single-flight coalescing.
- Nine to fifteen tickers must be split into batches without exceeding 8 credits/minute.
- A provider timeout or rate-limit response must preserve the last valid value and expose staleness.
- A 429/daily-quota response must not produce a red error page, retry storm, or repeated provider calls before the reset window.
- More symbols than can be refreshed in five minutes must degrade predictably instead of silently claiming all data is current.
- Hidden/unmounted pages must stop polling and release the live session.

## File Map

**Create**

- `backend/app/services/live_quotes.py` — quota-aware scheduler, cache, session lifecycle, and response model.
- `backend/app/api/live_quotes.py` — authenticated live quote endpoint and session/status endpoint.
- `backend/tests/services/test_live_quotes.py` — batching, throttling, cache, failure, and expiry tests.
- `backend/tests/api/test_live_quotes.py` — endpoint and multi-client behavior tests.

**Modify**

- `backend/app/providers/twelve_data.py` — add a quote/batch method separate from daily `time_series` history.
- `backend/app/providers/base.py` — add the live quote interface and normalized result type.
- `backend/app/main.py` (or existing router registration) — register live quote routes.
- `frontend/src/api.ts` — add live quote types and API calls.
- `frontend/src/App.tsx` and the Quotazioni component — visibility-aware polling, 5-minute default, freshness/status display, and cleanup.
- `backend/tests/providers/` — mock `/quote` batch responses, partial failures, timeout, and rate-limit responses.
- `docs/operations.md` — document quota assumptions, live session behavior, and fallback to persisted EOD values.

## Implementation Tasks

### Task 1: Define the provider contract and quota configuration

**Interfaces:**

- `LiveQuoteProvider.fetch_quotes(symbols: list[str]) -> list[LiveQuote]`.
- `LiveQuote(symbol, price, change_percent, observed_at, provider, status, raw)`.
- Settings: `LIVE_REFRESH_MINUTES=5`, `LIVE_BATCH_SIZE=8`, `LIVE_CREDITS_PER_MINUTE=8`, `LIVE_DAILY_CREDITS=800`, `LIVE_DAILY_RESERVE_PERCENT=20`, `LIVE_SESSION_IDLE_MINUTES=10`.

- [ ] Add failing adapter tests for a successful batch, an unknown symbol, partial response, timeout, and provider rate limit.
- [ ] Implement the normalized interface using Twelve Data `/quote` batch requests; keep the API key server-side.
- [ ] Validate configuration so batch size cannot exceed the per-minute credit limit.
- [ ] Run focused provider tests and commit `feat: add live quote provider contract`.

### Task 2: Implement the quota-aware live service

**Interfaces:**

- `LiveQuoteService.get_or_schedule(symbols: list[str], session_id: str) -> LiveQuotesSnapshot`.
- `LiveQuoteService.touch(session_id: str) -> None`.
- `LiveQuoteService.close_expired_sessions(now: datetime) -> int`.

- [ ] Write failing tests proving 9–15 symbols are split into batches of at most 8 and that no more than 8 credits are dispatched in a rolling minute.
- [ ] Implement a single-flight scheduler: normalize/deduplicate symbols, use a TTL cache, coalesce callers, and enqueue batches.
- [ ] Add priority ordering for held/visible symbols and oldest cached values first.
- [ ] Track daily credits and reserve; return `pending` rather than dispatching when the budget is exhausted.
- [ ] Preserve the last valid quote on error and attach `stale_since`, provider error, and retry time.
- [ ] Handle HTTP 429/daily-quota responses as `quota_exhausted`: calculate/store `retry_after` when supplied (otherwise use the configured next-window estimate), suppress calls until then, and return a user-safe `wait_until` message.
- [ ] Add session idle expiry so the service does not run when no UI client is active.
- [ ] Run service tests with a fake clock and fake provider; commit `feat: enforce live quote rate limits`.

### Task 3: Expose the live API

**Interfaces:**

- `GET /api/quotes/live?symbols=AAPL,MSFT,...` returns `{items, requested_at, next_refresh_at, credits_used, statuses}`.
- `POST /api/quotes/live/session` creates/touches a session and returns `session_id`.
- `DELETE /api/quotes/live/session/{session_id}` releases a session.

- [ ] Add API tests for authentication, symbol validation, duplicate symbols, multi-client coalescing, and stale fallback.
- [ ] Add API tests proving quota exhaustion returns HTTP 200 with `status: quota_exhausted`, cached values where available, `retry_after`, and no propagated provider exception.
- [ ] Implement endpoints without database writes and without exposing provider credentials.
- [ ] Ensure the response includes an explicit `source` (`twelve_data` or `persisted_eod`) and freshness timestamps.
- [ ] Run focused API tests and commit `feat: expose live quotes api`.

### Task 4: Add visibility-aware frontend polling

**Interfaces:**

- `fetchLiveQuotes(symbols, sessionId) -> LiveQuotesSnapshot` in `frontend/src/api.ts`.
- Quotazioni uses one module-wide range-independent polling interval of five minutes.

- [ ] Add frontend tests for immediate first fetch, five-minute polling, `document.visibilityState === hidden` pause, visibility resume, unmount cleanup, and error/stale rendering.
- [ ] Implement one session per browser tab and avoid per-row requests.
- [ ] Display last reading time as secondary metadata and show pending/stale states without presenting them as current.
- [ ] Keep Positions/KPI values on persisted EOD data in this phase; do not silently mix live and historical valuations.
- [ ] Run Vitest/build and commit `feat: poll live quotes while dashboard is visible`.

### Task 5: Verify operational behavior and document limits

- [ ] Add a mock integration test for 15 symbols over a 5-minute cycle: two batches, no rate-limit violation, and all values returned or explicitly pending.
- [ ] Add a test for more than 40 symbols proving the cycle is extended or lower-priority symbols remain pending.
- [ ] Verify that the existing EOD worker still writes history and that live polling does not create observations.
- [ ] Update `docs/operations.md` with the quota model, recommended ticker limits, troubleshooting, and fallback semantics.
- [ ] Run backend tests, frontend tests, `git diff --check`, and the Docker smoke test.
- [ ] Commit `docs: document live quote operations`.

## Acceptance Criteria

- With 15 tickers, the service uses two batches and never exceeds 8 credits in any rolling minute.
- With a 5-minute visible session, the UI refreshes live data without a permanent worker and stops after the page is hidden or closed.
- Provider failures never erase the last valid value and are visible as stale/error.
- Provider quota exhaustion never breaks the dashboard or causes a retry storm; the UI tells the user to wait until the next provider window.
- The database remains unchanged by live polling.
- EOD/history, TWR, and existing dashboard calculations continue to use persisted observations.
