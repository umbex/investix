# Investix — Specifica di design

**Stato:** approvata per pianificazione tecnica  
**Data:** 13 ottobre 2026  
**Specifica sorgente:** `PRD.md` versione 0.1

## Obiettivo

Realizzare un'applicazione privata, autogestita e riproducibile in Docker per gestire il portafoglio personale. Il database Investix è la fonte autorevole; STOCKS-26 serve esclusivamente per import iniziale e riconciliazione in sola lettura.

## Architettura

- Frontend React + TypeScript, servito insieme all'applicazione privata.
- Backend FastAPI: API autenticata, dominio contabile/performance, import e adapter provider.
- PostgreSQL persistente: ledger, configurazione, strumenti, osservazioni prezzi/FX, import e audit.
- Worker separato: aggiornamenti EOD, backfill storico, controllo staleness e, in futuro, refresh configurabili più frequenti.
- Docker Compose sul Mac mini, portabile senza modifiche architetturali nel Docker homelab. Accesso privato tramite Tailscale; nessuna esposizione Internet predefinita.

Il frontend legge gli snapshot persistiti. Quando il worker salva un nuovo dato, FastAPI può notificare la UI tramite WebSocket; il browser non chiama provider esterni e non riceve segreti. L'eventuale frequenza intraday futura è una policy del worker e non richiede una diversa architettura frontend/backend.

## UI e grafici

- Direzione approvata: **Command center** — dashboard dark, densa ma leggibile, con KPI, andamento principale, allocazione e drill-down a registro e performance.
- Lingua italiana, locale `it-IT`, valuta base EUR; numeri tabulari, focus visibile, navigazione tastiera e stati non affidati al solo colore.
- Libreria UI: **Mantine Core** (MIT), senza starter/template a pagamento come dipendenza di prodotto.
- Grafici: **Apache ECharts** (Apache-2.0), con tooltip, legenda, zoom/pan, range, export dei dati filtrati e descrizioni accessibili.
- Desktop prioritario; tablet utilizzabile; mobile riorganizza i controlli senza sovrapposizioni.

## Ledger, posizioni e calcoli

`operations` è un ledger append-only. Una correzione crea una revisione e un annullamento conserva audit e riferimenti; non esistono cancellazioni distruttive non tracciate.

Ogni operazione appartiene a un account e a uno strumento. L'input supporta acquisto, vendita, saldo iniziale, dividendo, commissione, trasferimenti e rettifiche/eventi societari documentati. Quantità, prezzo, controvalore, commissione e dividendo mantengono valore/valuta originaria ed EUR quando disponibili.

Commissioni e dividendi sono opzionali e nullable: l'assenza non viene trasformata in uno zero dichiarato. KPI e report distinguono quindi importi registrati e copertura incompleta.

Le posizioni e le metriche sono derivate dal ledger e dalle osservazioni di mercato:

- costo medio ponderato per ticker/account;
- P&L realizzato persistente anche a posizione con quantità zero;
- P&L non realizzato come valore corrente meno costo residuo;
- P&L totale separato in realizzato, non realizzato, dividendi e commissioni registrati;
- TWR giornaliero flow-adjusted, con flussi a fine giornata; dividendi e commissioni inclusi quando registrati.

Se mancano dati necessari, rendimento/CAGR è non disponibile con motivazione, mai un valore artificiale pari a zero.

## Dati di mercato

Ogni `price_observation` conserva provider, simbolo originale, mercato, valuta, unità, timestamp di acquisizione, campo prezzo, valore grezzo, valore normalizzato, FX e stato.

La v1 esegue aggiornamenti EOD. Provider pubblici o scraping sono consentiti soltanto per basso volume e uso personale, con cache, rate limit, retry/backoff, provenienza e staleness. Un errore non cancella l'ultimo dato valido.

Per un nuovo titolo, l'utente definisce/conferma ticker, borsa, valuta e unità; l'adapter esegue un backfill dalla prima operazione, con margine per giorni non di mercato, e poi entra nella pianificazione ordinaria. In caso di copertura insufficiente il sistema espone il gap e permette backfill da altro provider o CSV, senza inventare punti storici. GBX viene normalizzato in GBP prima della conversione EUR; le serie storiche usano FX storico.

## Import STOCKS-26 e riconciliazione

L'import è one-shot e non introduce sincronizzazione futura con Google Sheets.

1. Verifica live in sola lettura di ID, titolo, fogli e schema.
2. Acquisizione grezza di `MOVIMENTI` con numero riga, timestamp e hash.
3. Staging e validazione di tipi, date, quantità, valute, simboli e duplicati.
4. Acquisizione versionata di setup, benchmark e, se verificabili, snapshot prezzo/FX.
5. Report di riconciliazione: quantità ticker/account, costo residuo, P&L realizzato, dividendi registrati, benchmark, copertura e gap.
6. Finalizzazione idempotente solo senza righe non mappate, valute/unità dubbie o scostamenti oltre tolleranza documentata.

La verifica del 13 ottobre 2026 conferma il workbook `STOCKS-26`, ID `1Cqpe6uYLJwOmru1wgbEKr4a-NKndAvRg5j2TyAYmhHg`, i sei fogli e gli ID riportati nella scheda. La discrepanza nota resta: SETUP cita le colonne N:O, mentre l'intestazione del ledger colloca `SIMBOLO QUOTA` e `VALUTA QUOTA` in M:N. L'import segue sempre le intestazioni effettive M:N.

## Sicurezza e operatività

- Autenticazione obbligatoria anche per il singolo utente; API e provider solo server-side.
- Segreti in environment/config, mai in repository, immagini, browser o log.
- Volume PostgreSQL persistente, backup con retention configurabile, export e restore verificato su database temporaneo.
- Health check di app, DB e worker; stato dell'ultimo provider update e backup consultabile.

## Fuori ambito della v1

Nessuna integrazione broker/banca, gestione di cassa, trading, multiutenza, esposizione pubblica, streaming/intraday, consulenza finanziaria o sincronizzazione bidirezionale con Google Sheets.

Il refresh più frequente resta un'estensione futura, prevista nei confini dell'architettura ma non pianificata come requisito funzionale della prima versione.

## Criteri di verifica principali

- Test di ledger: acquisti, vendite parziali/totali, riacquisti, costo medio, P&L, dividendi/commissioni opzionali, split, FX/GBX, TWR e CAGR.
- Test di import: schema, righe incomplete, date/valute invalide, formule/errori, duplicati, idempotenza e riconciliazione.
- Test adapter: successo, copertura insufficiente, dato mancante, simbolo sconosciuto, rate limit, timeout, valore invalido e retry.
- Test PostgreSQL/migrazioni, CRUD e2e, filtri/range/grafici, provider refresh, backup/restore.

## Decisioni rinviate intenzionalmente

- Provider iniziale specifico: sarà selezionato dopo una prova di copertura e licenza sui simboli reali, senza attivare servizi a pagamento senza consenso.
- Soglie di staleness, frequenze EOD esatte per mercato, tolleranze di riconciliazione e retention backup: definite nel piano tecnico e nella configurazione, non hard-coded.
- Esportazione PNG: valutata con l'implementazione ECharts; CSV resta requisito certo.
