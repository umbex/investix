# Operazioni Investix

## Avvio privato

1. Copiare `.env.example` in `.env` e sostituire ogni valore di esempio con segreti casuali.
2. Avviare `docker compose up -d --build`.
3. Aprire `http://127.0.0.1:5173`; per Tailscale pubblicare il servizio attraverso il reverse proxy/host privato, senza esporre porte su Internet.

API e frontend sono vincolati al loopback. Il database non espone porte host.

## Backup e prova di ripristino

Il backup è un dump PostgreSQL compresso:

```sh
./scripts/backup.sh /absolute/path/investix-$(date +%F).sql.gz
```

La retention non cancella nulla per default: elencare i dump oltre soglia con `./scripts/prune-backups.sh /absolute/path 30`; usare `--apply` solo dopo aver verificato l’elenco.

Provare il ripristino solo in un database temporaneo non esistente:

```sh
./scripts/restore.sh /absolute/path/investix-2026-10-13.sql.gz investix_restore_check
```

`restore.sh` rifiuta i database protetti `investix`, `postgres`, `template0` e `template1`; eliminare il database temporaneo solo dopo avere verificato il risultato.
Il gate locale è `./scripts/test-backup-restore.sh`; per eseguire anche il ciclo PostgreSQL reale usare esplicitamente `RUN_DOCKER_TESTS=1 ./scripts/test-backup-restore.sh`.

I comandi leggono `.env`; in una verifica separata si può impostare `INVESTIX_ENV_FILE=.env.example`.

## Sicurezza e dati

- Google Sheets viene letto solo durante l’import iniziale da file esportato: non configurare credenziali Sheets nell’app.
- Per verificare in seguito l’import senza riaprire il foglio, montare il CSV congelato nel container ed eseguire `python -m app.importing.reconcile_cli /data/movimenti.csv`; un disallineamento ticker/conto interrompe il report con dettaglio.
- Il benchmark iniziale è configurabile senza riaprire Sheets: `python -m app.importing.benchmark_catalog_cli --name "Nasdaq-100" --ticker QQQ --symbol QQQ --venue NASDAQ --currency USD --methodology price_return --note "Proxy ETF; dividendi esclusi."`.
- Il worker non abilita provider pubblici di default. Il CSV manuale mantiene l’uso personale a basso volume e la provenienza del dato.
- Twelve Data è opzionale e usa solo la variabile server-side `INVESTIX_TWELVE_DATA_API_KEY`; non inserire la chiave nel frontend o in `.env.example` valorizzato.
- Le quotazioni live sono on-demand dalla dashboard: il backend usa batch da massimo 8 ticker, cache temporanea e una riserva giornaliera. Se il provider esaurisce la quota, la UI mantiene l’ultimo dato valido e indica di attendere la prossima finestra, senza generare errori bloccanti. Le osservazioni live non vengono scritte nel DB; storico e KPI restano basati sui dati EOD persistiti.
- Il refresh EOD è separato per mercato: Europa alle 18:00 `Europe/Rome`, USA alle 16:30 `America/New_York`. Le conversioni DST sono gestite dai fusi IANA.
- Per riconciliare e finalizzare un import, prima generare il report: `python -m app.importing.reconcile_cli /data/movimenti.csv --report /data/reconciliation.json`, poi eseguire `python -m app.importing.cli --finalize /data/movimenti.csv --reconciliation-report /data/reconciliation.json`.
- Commissioni e dividendi assenti restano sconosciuti; non vanno convertiti in zero nell’operatività.
