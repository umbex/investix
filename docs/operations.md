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

Provare il ripristino solo in un database temporaneo non esistente:

```sh
./scripts/restore.sh /absolute/path/investix-2026-10-13.sql.gz investix_restore_check
```

`restore.sh` rifiuta i database protetti `investix`, `postgres`, `template0` e `template1`; eliminare il database temporaneo solo dopo avere verificato il risultato.

I comandi leggono `.env`; in una verifica separata si può impostare `INVESTIX_ENV_FILE=.env.example`.

## Sicurezza e dati

- Google Sheets viene letto solo durante l’import iniziale da file esportato: non configurare credenziali Sheets nell’app.
- Per verificare in seguito l’import senza riaprire il foglio, montare il CSV congelato nel container ed eseguire `python -m app.importing.reconcile_cli /data/movimenti.csv`; un disallineamento ticker/conto interrompe il report con dettaglio.
- Il worker non abilita provider pubblici di default. Il CSV manuale mantiene l’uso personale a basso volume e la provenienza del dato.
- Commissioni e dividendi assenti restano sconosciuti; non vanno convertiti in zero nell’operatività.
