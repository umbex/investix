# Investix

Private portfolio management application. The design and implementation plan are in `docs/superpowers/`.

## Local setup

```sh
cp .env.example .env
# Set a non-default POSTGRES_PASSWORD and INVESTIX_SESSION_SECRET.
docker compose up --build
```

The frontend is bound to `127.0.0.1:5173` and the API to `127.0.0.1:8000`; access them privately over Tailscale through the host, not by exposing containers publicly. See [`docs/operations.md`](docs/operations.md) for backups, restore checks and operating guidance.

## Required environment variables

- `POSTGRES_PASSWORD`
- `INVESTIX_SESSION_SECRET`
- `INVESTIX_ADMIN_PASSWORD`

## Optional environment variables

- `POSTGRES_DB` (default `investix`)
- `POSTGRES_USER` (default `investix`)
- `INVESTIX_DATABASE_URL` (default points to the Compose database)
