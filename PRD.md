# Investix — Product Requirements Document

**Version:** 0.1  
**Status:** Draft for user review  
**Data:** 13 ottobre 2026  
**Destinatario:** Codex e proprietario del prodotto  
**Prodotto:** applicazione web privata per la gestione professionale di un portafoglio personale

## 1. Visione

Investix è uno strumento web personale, affidabile e professionale per registrare le operazioni, conoscere il valore corrente e storico del portafoglio, misurare guadagni e rendimenti e confrontarli con benchmark configurabili. Funziona in container Docker con un database persistente e non dipende da Google Sheets per calcoli o aggiornamenti futuri.

“Personale” descrive l’utente iniziale e il modello di accesso, non un compromesso sulla qualità: coerenza dei calcoli, tracciabilità, gestione degli errori, grafici interattivi, sicurezza e procedure di backup sono requisiti di prodotto.

Il database Investix sarà la fonte ufficiale dei dati operativi. Il foglio Google esistente serve per migrazione e riconciliazione, non come servizio runtime né come seconda fonte modificabile.

## 2. Utente e criteri di successo

L’utente iniziale è un singolo investitore che gestisce strumenti distribuiti su più account. Il portafoglio può includere azioni, ETF e criptovalute presenti nel registro. Valuta base EUR.

La soluzione è riuscita quando l’utente può:

- aggiungere, correggere e rimuovere operazioni senza mantenere formule;
- vedere posizioni aggregate per strumento e risalire ai singoli account;
- distinguere valore, P&L realizzato, P&L non realizzato, dividendi e rendimento percentuale;
- esplorare grafici per periodi predefiniti o date personalizzate e confrontarli con benchmark;
- conoscere sempre data e fonte della quotazione, individuando dati mancanti o scaduti;
- cambiare provider senza riscrivere i calcoli o perdere lo storico;
- ripristinare il database da un backup verificato.

## 3. Ambito

### Incluso nella prima versione

1. Applicazione web privata con autenticazione.
2. Dashboard aggregata, dettaglio per account e pagina per strumento.
3. Registro movimenti con inserimento, modifica, annullamento/eliminazione tracciata, ricerca e filtri.
4. Import guidato da STOCKS-26 di movimenti, impostazioni, benchmark e dati storici estraibili e verificabili.
5. Aggiornamento programmato di prezzi EOD e cambi tramite provider selezionabile.
6. Adattatori intercambiabili per più provider con interfaccia comune.
7. Calcolo di posizioni, costo, P&L, rendimento e benchmark.
8. Grafici interattivi, intervalli, filtri ed esportazione dei dati visualizzati.
9. Configurazione di strumenti, simboli/mercati, valute e benchmark.
10. Docker Compose, PostgreSQL persistente, backup e restore documentati.
11. Test automatici di calcoli, import, provider e principali flussi utente.

### Escluso dalla prima versione

- Inserimento o esecuzione di ordini presso broker.
- Collegamenti automatici a broker o conti bancari.
- Gestione di saldo di cassa, pagamenti o riconciliazione bancaria.
- Consulenza finanziaria/fiscale o raccomandazioni di investimento.
- Multiutenza, ruoli, condivisione pubblica o SaaS.
- Quotazioni intraday, streaming e alert per trading.
- Dipendenza operativa da Google Sheets o sincronizzazione bidirezionale.

## 4. Requisiti funzionali

### 4.1 Registro movimenti

Il registro è la base per ricostruire quantità e costo delle posizioni. Deve supportare almeno acquisto, vendita, saldo iniziale, dividendo, commissione separata e rettifica/evento societario documentato quando necessario.

Campi logici: data operazione e, se utile, data regolamento; account; ticker; ISIN; tipo; quantità; prezzo e valuta originali quando noti; controvalore EUR; commissioni EUR; dividendo EUR; simbolo e mercato; note; identificativo univoco; stato e cronologia modifiche.

Non è richiesto mantenere un saldo di cassa. Acquisti e vendite sono finanziati/regolati fuori dal portafoglio. Il motore registra però flussi di capitale derivati, non mostrati come cassa detenuta, per calcolare rendimenti corretti.

Le operazioni devono poter essere corrette o annullate. Le eliminazioni devono essere reversibili o lasciare una traccia di audit. Ogni modifica ricalcola le posizioni e metriche dipendenti.

### 4.2 Posizioni e P&L

- Vista principale aggregata per strumento e dettaglio consultabile per account.
- Costo medio ponderato per ticker e account come metodo iniziale, coerente con il registro attuale. Passare a FIFO richiede decisione esplicita e riconciliazione.
- Il P&L realizzato rimane consultabile anche quando la quantità residua diventa zero.
- P&L non realizzato = valore corrente meno costo residuo della quantità aperta.
- P&L complessivo espone separatamente componenti realizzate, non realizzate, dividendi e commissioni.
- Una posizione azzerata non cancella storico, costo né P&L realizzato.
- Date o costi iniziali approssimativi devono poter essere marcati e accompagnati da nota.

### 4.3 Rendimento e benchmark

Il rendimento percentuale non deve essere il semplice rapporto fra valore finale e iniziale quando ci sono acquisti o vendite. Il motore usa una metodologia flow-adjusted (TWR o metodo scelto e documentato) per escludere l’effetto dei flussi di capitale dal rendimento, mantenendoli distinti dal P&L assoluto.

Requisiti:

- Formula documentata per rendimento giornaliero, cumulato, annualizzato/CAGR e periodo selezionato.
- Acquisti/vendite trattati come flussi sintetici di capitale ai soli fini della performance, non come gestione di cassa.
- Dividendi e commissioni inclusi o esclusi in modo esplicito e coerente fra portafoglio e benchmark.
- Benchmark configurabili con nome, ticker, simbolo provider, mercato, valuta, stato attivo e metodologia price-return o total-return.
- Serie confrontate sullo stesso intervallo e convertite in EUR con cambi storici coerenti quando richiesto.
- Evidenziare proxy ETF, indici price-only e differenze metodologiche che riducono la comparabilità.
- Se date o valori iniziali non bastano, mostrare non disponibile con motivazione, non zero o un rendimento ingannevole.

### 4.4 Dashboard

La schermata principale mostra:

- valore totale corrente, data/ora ultimo aggiornamento e stato dei dati;
- P&L assoluto complessivo e componenti;
- rendimenti per periodi selezionati e CAGR quando il periodo è sufficiente;
- posizioni aggregate con ticker/nome, quantità, valore di mercato, costo EUR, P&L, P&L percentuale e peso;
- ricerca e filtri per strumento, account, tipo di asset e periodo;
- navigazione dall’aggregato ai movimenti e account sottostanti;
- stati chiari di caricamento, assenza dati, errore provider e quotazione scaduta.

KPI, tabella, grafici e dettaglio devono concordare. La valuta base è EUR; per strumenti in altre valute devono essere ispezionabili valuta di quotazione e contributo FX.

### 4.5 Grafici, intervalli e filtri

I grafici sono funzionalità fondamentali. La prima versione include:

1. Valore del portafoglio e P&L complessivo nel tempo, con serie selezionabili.
2. Rendimento effettivo contro uno o più benchmark configurati.
3. Rendimento per strumento e confronto fra strumenti/account.
4. Allocazione per ticker e account.

Intervalli: 1M, 3M, 6M, YTD, 1Y, 2Y, 5Y, tutto lo storico disponibile e intervallo personalizzato da/a. L’interfaccia comunica i limiti dovuti alla copertura effettiva.

Interazioni:

- filtri per ticker, account, benchmark e classe di asset con indicazione visibile dei filtri attivi;
- legenda/controlli per mostrare o nascondere valore, P&L, rendimento e benchmark;
- tooltip per data con valori, rendimento, valuta e fonte/stato;
- zoom, pan o selezione di finestra temporale e reset alla vista iniziale;
- aggregazione giornaliera, settimanale o mensile quando utile, rispettando i calendari di mercato;
- confronti percentuali normalizzati all’inizio del periodo; serie monetarie con scale che non inducano confronti errati;
- esportazione CSV dei punti filtrati e, se supportato dalla libreria scelta, esportazione immagine;
- filtri e range aggiornano coerentemente KPI e dati collegati e consentono il ritorno alla vista completa.

## 5. Fase UX/UI design — gate prima della UI definitiva

Prima dello sviluppo dell’interfaccia si realizza una fase di design distinta dall’implementazione funzionale.

### Attività e deliverable

1. Redigere un design brief per una dashboard finanziaria moderna, dark, densa ma leggibile.
2. Presentare 2–3 direzioni visive/layout per dashboard, grafici, tabella posizioni e registro.
3. Confrontare template/starter kit riutilizzabili e layout su misura. Valutare qualità, manutenzione, licenza, accessibilità, responsive, personalizzazione e dipendenze.
4. Confrontare librerie UI e grafici con gli stessi criteri. Candidati non vincolanti: componenti Tailwind/shadcn, Mantine o MUI; ECharts, Recharts o TradingView Lightweight Charts. La selezione richiede verifica di licenza, manutenzione, accessibilità, funzioni e compatibilità con i filtri richiesti.
5. Preparare wireframe e prototipo visivo/navigabile per dashboard, grafico con range/filtri, dettaglio posizione e inserimento movimento. Usare dati fittizi o minimizzati.
6. Presentare raccomandazione, trade-off e manutenzione prevista.
7. Ottenere approvazione dello stile, layout, template e librerie prima di costruire la UI di produzione.

### Principi visivi e di usabilità

- Tema scuro professionale, contrasto sufficiente; stati positivi/negativi non distinguibili solo dal colore.
- Densità informativa da strumento di analisi, gerarchia chiara, valori numerici leggibili.
- Desktop come esperienza primaria; tablet utilizzabile; mobile leggibile senza sovrapporre controlli e serie.
- Navigazione da tastiera e focus visibile per controlli principali; etichette e tooltip comprensibili.
- Lingua italiana, locale it-IT, date e numeri locali, EUR come valuta base.
- Preferenze persistenti per tema, range e benchmark se realizzabili senza complessità sproporzionata.

**Gate:** nessuna scelta definitiva di UI kit, chart library o template e nessuna UI di produzione prima della revisione e approvazione del prototipo.

## 6. Dati di mercato e adattatori

### 6.1 Interfaccia comune

Il dominio Investix non chiama direttamente API proprietarie. Ogni adapter normalizza:

- ricerca/verifica di simbolo e mercato;
- serie EOD storica per simbolo e intervallo date;
- ultimo EOD disponibile;
- serie FX storiche e ultimo cambio quando forniti;
- metadati di data/ora, valuta, unità e stato;
- errori, limiti, ritardi, rate limit e stato servizio.

Il sistema permette di configurare e provare più provider. Ogni osservazione conserva provider, simbolo originale, data acquisizione, mercato, valuta, unità, campo prezzo e stato. Cambiare provider non sovrascrive silenziosamente i dati: confronto e regole esplicite evitano serie miste o discontinuità.

Aggiornamenti idempotenti; retry con backoff e rate limiting; un errore non cancella l’ultimo dato valido. Dati scaduti restano distinguibili e visibili con avviso.

### 6.2 Frequenza e storico

- Prima versione EOD giornaliera dopo la chiusura del relativo mercato; nessuno streaming/intraday.
- L’interfaccia provider supporta aggiornamenti futuri, backfill e recupero dei buchi anche se lo storico iniziale viene importato dal foglio.
- Pianificazione per mercato e fuso orario; non assumere che borse USA ed Europa chiudano allo stesso orario.
- Lo storico normalizzato è conservato in PostgreSQL e validato prima di alimentare KPI e grafici.

### 6.3 Valute, unità ed eventi societari

- Conservare prezzo nativo, valuta, prezzo normalizzato, FX utilizzato, valore EUR, data e fonte del cambio.
- Trattare GBX (pence) distintamente da GBP (sterline): dividere per 100 prima della conversione EUR.
- Usare FX storico per valutazioni storiche, non il cambio odierno retroattivo.
- Gestire split ed eventi societari per evitare salti artificiali in quantità, costo e rendimento.
- Conservare prezzo grezzo e aggiustato quando disponibili e documentare quale alimenta ciascuna metrica.
- Il total-return deve tener conto dei dividendi o dichiarare che la serie è price-only.

### 6.4 Selezione del provider

La prova di copertura verifica simboli reali e benchmark, profondità dello storico, FX, unità di quotazione, split/dividendi, quota API, conservazione e licenza per visualizzazione personale. Nessun provider è considerato già approvato. Un piano gratuito non è automaticamente adeguato o autorizzato perché i dati sono accessibili da browser.

## 7. Migrazione da Google Sheets

Per l'identificativo del workbook, l'inventario dei fogli, il mapping dei campi e l'analisi del flusso formule/dati consultare [GOOGLE_SHEET_REFERENCE.md](./GOOGLE_SHEET_REFERENCE.md). È la scheda tecnica di riferimento per comprendere STOCKS-26 senza dover riesaminare ogni volta il foglio; riporta anche limiti, assunzioni e verifiche richieste prima dell'import.

### Fonti e mapping

- MOVIMENTI: dati di input quali data, account, ticker/ISIN, tipo, quantità, prezzo EUR, commissioni, note, valuta/simbolo; costo residuo, PMC e P&L realizzato sono riconciliati e ricostruiti dal ledger quando possibile.
- SETUP: valuta base, orizzonte, data iniziale, simboli e valute di quotazione, benchmark attivi.
- _PRICE_HISTORY: serie data/prezzo per strumento e date/cambi FX, candidata per import storico se valori estraibili e validabili.
- _PERFORMANCE: serie calcolata utile per riconciliazione, non sostituisce le quotazioni necessarie al ricalcolo.
- DASHBOARD: riferimento di KPI, viste e grafici, non fonte contabile primaria.

### Flusso

1. Leggere/esportare senza modificare il foglio.
2. Mostrare anteprima: conteggi, intervalli, duplicati, errori, valute e righe non riconosciute.
3. Validare e mappare i dati.
4. Importare in staging e produrre report di righe accettate/rifiutate e motivazioni.
5. Riconciliare quantità per ticker/account, costo residuo, PMC, P&L realizzato, dividendi, storico, benchmark e valori di riferimento.
6. Confermare l’import mantenendo copia grezza con data/versione e hash.

Le formule GOOGLEFINANCE sono dati mobili, non snapshot per definizione. L’import prova a materializzare righe statiche data/prezzo/cambio e verifica copertura e buchi; non presume che API Sheets o Apps Script restituiscano sempre lo storico. Se l’estrazione è incompleta, segnala i gap e consente backfill da provider, senza perdere la provenienza.

Import ripetibile senza duplicazioni tramite chiavi idempotenti. Discrepanze oltre tolleranza impediscono la finalizzazione o richiedono conferma documentata. Il foglio resta invariato; dopo la riconciliazione può essere archivio/export read-only. Nessuna sincronizzazione bidirezionale.

## 8. Architettura proposta

Proposta iniziale da tradurre in piano tecnico dopo l’approvazione della PRD:

- Frontend React + TypeScript.
- API backend Python + FastAPI, con dominio testabile separato dagli adapter.
- PostgreSQL fonte autorevole; migrazioni versionate.
- Worker/scheduler per aggiornamenti EOD, backfill e controlli.
- Docker Compose per applicazione, worker, database e proxy TLS nel deployment remoto.
- Configurazione via environment/config; segreti esclusi da repository e immagini.
- Le API provider sono chiamate solo server-side; il browser non riceve chiavi.
- UI kit, chart library e template rimangono decisioni del gate UX/UI.

Prima distribuzione singolo utente, privata e non pubblica per default. Hosting e accesso remoto si decidono in seguito. Nessuna esposizione a Internet senza autenticazione, TLS e aggiornamenti di sicurezza.

## 9. Sicurezza e operatività

- Autenticazione anche per uso personale; sessioni protette e segreti fuori dal codice.
- Nessun ordine o accesso broker; memorizzare solo i dati portfolio necessari.
- Validazione server-side e log privi di token/segreti.
- HTTPS su reti non fidate; accesso predefinito limitato a LAN/VPN.
- Backup automatici database con retention configurabile, esportazione e restore documentato.
- Health check di app, DB e worker; visualizzare ultimo update provider e backup.
- Quotazioni e P&L informativi, non consulenza né prezzo garantito di esecuzione.

## 10. Test e criteri di accettazione

### Test richiesti

- Unit test di quantità, costo medio, vendite parziali/totali, riacquisti, P&L realizzato, dividendi, commissioni, split, FX/GBX, TWR e CAGR.
- Test adapter con mock per successo, dato mancante, simbolo sconosciuto, rate limit, timeout, dato invalido e retry.
- Test import per duplicati, date/valute non valide, formule/errori, righe incomplete e idempotenza.
- Test integrazione PostgreSQL/migrazioni.
- Test end-to-end UI per CRUD movimento, filtri, range grafici, benchmark, refresh e stati d’errore.
- Test backup/restore in database temporaneo.
- Riconciliazione con dataset congelato e tolleranze documentate.

### Accettazione funzionale

1. Modifiche al registro aggiornano aggregati, account, P&L e grafici senza fogli tecnici.
2. Quantità aggregate corrispondono alla somma dei movimenti validi.
3. Vendita totale azzera la quantità ma conserva P&L realizzato e storico.
4. Un acquisto importante non appare come rendimento positivo solo perché cresce il capitale investito.
5. Prezzi mancanti/scaduti sono segnalati e non spacciati per aggiornati.
6. Cambio provider conserva storico e provenienza verificabile.
7. Range/filtri aggiornano serie e KPI; benchmark espone base, valuta e metodologia.
8. Import produce riconciliazione prima di diventare fonte ufficiale.
9. Compose avvia il servizio; dati persistono al riavvio; restore verificato.
10. I test critici sono eseguibili con comando documentato e passano.

## 11. Fasi di consegna

1. Revisione PRD: confermare requisiti, metriche e assunzioni.
2. Design UX/UI: confrontare stili, template e librerie; prototipo e approvazione.
3. Prova dati: verificare provider, licenze, simboli, storico Sheets, FX ed eventi societari.
4. Piano d’implementazione: attività piccole e testabili per DB, calcoli, adapter, import, API, UI e deploy.
5. Fondazioni: repo, Compose, schema/migrazioni, autenticazione e test.
6. Registro e calcoli: import staging, CRUD, posizioni, P&L e performance.
7. Dati: adapter, backfill, scheduler, FX, controlli e stato.
8. UI e grafici: implementare dopo gate design.
9. Riconciliazione e rilascio privato: import, end-to-end, backup/restore e hosting.

## 12. Assunzioni e decisioni aperte

### Assunzioni iniziali

- Singolo utente, uso personale e accesso privato.
- EUR come valuta base.
- EOD giornaliero sufficiente per la prima versione.
- Nessun saldo cassa; flussi derivati solo per rendimento.
- Costo medio ponderato per ticker/account iniziale, coerente col registro.
- DB fonte unica; Google Sheets per import, controllo e archivio/export.
- FastAPI, PostgreSQL, React e Docker Compose sono la base tecnica proposta.
- Tema dark professionale; UI kit, chart library e template scelti dopo design.

### Da decidere prima del piano tecnico

- Hosting (Mac mini, NAS, VPS o altro) e accesso remoto LAN/VPN/Internet.
- Provider EOD iniziale, costo e termini di licenza.
- Definizione finale di TWR/total return, dividendi, benchmark e valori iniziali approssimativi.
- Politica di correzione/cancellazione e audit.
- Range/filtri iniziali e necessità di esportazione PNG.
- Stile, componenti, chart library e template dopo il prototipo.

## 13. Glossario

- EOD: prezzo di fine giornata del mercato.
- P&L realizzato: utile/perdita contabilizzato sulle quantità vendute.
- P&L non realizzato: utile/perdita sulle quantità ancora detenute.
- TWR: rendimento che neutralizza l’effetto dei flussi di capitale.
- Provider adapter: interfaccia che normalizza le risposte dei provider nel formato Investix.
- Staleness: età del dato rispetto alla sessione EOD attesa per il mercato.
