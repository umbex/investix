# Investix

Versione applicativa: `0.3.0` (SemVer; sorgente: [`VERSION`](VERSION)).

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

## Dati di mercato

- Il catalogo dello strumento conserva ISIN e listing preferito: per `EQQQ` (ISIN `IE0032077012`) il listing configurato è `EQQQ.MI`, Borsa Italiana, EUR. Il ticker non identifica da solo una borsa o una valuta.
- I cambi USD/EUR futuri possono essere letti lato server dall'adapter ECB (`ecb-reference`), che conserva il tasso di riferimento normalizzato in EUR per USD. Non è abilitato automaticamente dal worker.
- Lo snapshot storico iniziale resta un file locale congelato: Google Sheets non è una dipendenza operativa. La serie storica EQQQ già importata da Londra resta valida come fallback normalizzato GBX→EUR finché non è disponibile una serie EUR con copertura e controlli equivalenti.
