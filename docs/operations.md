# Investix Operations

## Private startup

1. Copy `.env.example` to `.env` and replace every placeholder with a randomly generated secret.
2. Start the stack with `docker compose up -d --build`.
3. Open `http://127.0.0.1:5173`; for Tailscale access, publish the service through a private reverse proxy/host without exposing ports to the Internet.

The API and frontend are bound to the loopback interface. PostgreSQL does not publish a host port.

## Backup and restore verification

The backup is a compressed PostgreSQL dump:

```sh
./scripts/backup.sh /absolute/path/investix-$(date +%F).sql.gz
```

Retention does not delete anything by default: list dumps older than the threshold with `./scripts/prune-backups.sh /absolute/path 30`; use `--apply` only after reviewing the list.

Test restores only in a temporary database that does not already exist:

```sh
./scripts/restore.sh /absolute/path/investix-2026-10-13.sql.gz investix_restore_check
```

`restore.sh` refuses the protected databases `investix`, `postgres`, `template0`, and `template1`; remove the temporary database only after verifying the result.
The local gate is `./scripts/test-backup-restore.sh`; to run the real PostgreSQL cycle explicitly use `RUN_DOCKER_TESTS=1 ./scripts/test-backup-restore.sh`.

The commands read `.env`; for an isolated configuration check, set `INVESTIX_ENV_FILE=.env.example`.

## Security and data

- Historical sources are read only during the initial import from exported files; the application does not require spreadsheet credentials.
- To verify an import later, mount the frozen CSV in the container and run `python -m app.importing.reconcile_cli /data/movimenti.csv`; a ticker/account mismatch stops the report with details.
- Configure the initial benchmark with `python -m app.importing.benchmark_catalog_cli --name "Nasdaq-100" --ticker QQQ --symbol QQQ --venue NASDAQ --currency USD --methodology price_return --note "Proxy ETF; dividends excluded."`.
- The worker does not enable public providers by default. Manual CSV import remains suitable for personal, low-volume use and preserves data provenance.
- Twelve Data is optional and uses only the server-side variable `INVESTIX_TWELVE_DATA_API_KEY`; never put the key in the frontend or in a populated `.env.example`.
- Live quotes are on-demand from the dashboard: the backend uses batches of at most 8 tickers, temporary caching, and a daily reserve. If the provider quota is exhausted, the UI keeps the last valid value and asks the user to wait for the next window instead of raising a blocking error. Live observations are not written to the database; history and KPIs remain based on persisted EOD data.
- EOD refresh is scheduled per market: Europe at 18:00 `Europe/Rome`, USA at 16:30 `America/New_York`. DST conversions are handled by IANA time zones.
- To reconcile and finalize an import, first generate the report with `python -m app.importing.reconcile_cli /data/movimenti.csv --report /data/reconciliation.json`, then run `python -m app.importing.cli --finalize /data/movimenti.csv --reconciliation-report /data/reconciliation.json`.
- Missing fees and dividends remain unknown; they must not be converted to zero during operations.
