# Riferimento Google Sheet — STOCKS-26

Scheda tecnica per la migrazione di Investix. Descrive il workbook osservato il 13 ottobre 2026, il suo flusso logico e il mapping utile all'import, così un agente può partire da questo documento senza riesaminare ogni tab. Il foglio resta una fonte esterna da verificare al momento dell'import: formule e impostazioni possono cambiare.

## Identità e regole d'accesso

- Titolo: STOCKS-26
- URL: https://docs.google.com/spreadsheets/d/1Cqpe6uYLJwOmru1wgbEKr4a-NKndAvRg5j2TyAYmhHg/edit
- Spreadsheet ID: 1Cqpe6uYLJwOmru1wgbEKr4a-NKndAvRg5j2TyAYmhHg
- Locale: it_IT; fuso orario: Europe/Rome; valuta base configurata: EUR.
- Ruolo nel progetto: sorgente per import iniziale, controllo e riconciliazione; non deve essere una dipendenza runtime dell'app.
- Regola: accesso in sola lettura. Non modificare celle, formule, struttura o visibilità dei fogli durante la migrazione.
- Prima di importare, verificare che nome, ID e schemi corrispondano ancora; il nome da solo non identifica univocamente il workbook.

## Inventario dei fogli osservati

| Foglio | Visibilità | Ruolo nel sistema corrente |
|---|---|---|
| DASHBOARD | Visibile | Presentazione aggregata: KPI, posizioni per ticker e grafici. Vista di controllo, non ledger primario. |
| MOVIMENTI | Visibile | Ledger operativo delle operazioni; fonte autorevole attuale per quantità e costo delle posizioni. |
| _DASH_DATA | Nascosto | Tabella tecnica per posizione ticker/conto con quantità, mapping quotazione, prezzo EUR, valore, costo e P&L. Alimenta i KPI e le tabelle della dashboard. |
| SETUP | Visibile | Valuta base, orizzonte storico, data iniziale ricostruita, benchmark attivi, universo strumenti e mapping di valuta. |
| _PRICE_HISTORY | Nascosto | Serie storiche data/prezzo per strumenti e benchmark, più serie di cambio. |
| _PERFORMANCE | Nascosto | Serie giornaliera calcolata di valore del portafoglio, flussi/TWR e benchmark, usata da KPI e grafici. |

Gli ID numerici interni osservati sono: DASHBOARD 222222001, MOVIMENTI 222222003, _DASH_DATA 222222002, SETUP 1453730562, _PRICE_HISTORY 884342945, _PERFORMANCE 1909144463. Sono identificatori API, non chiavi di dominio da conservare nel database.

## Flusso dei dati e logica analitica

La catena principale è: MOVIMENTI alimenta l'universo configurato in SETUP, la valorizzazione ticker/conto in _DASH_DATA e le quantità storiche in _PERFORMANCE. SETUP stabilisce gli strumenti, gli orizzonti e le valute per _PRICE_HISTORY, _DASH_DATA e _PERFORMANCE. _PRICE_HISTORY fornisce le quotazioni e i cambi storici a _PERFORMANCE; infine _DASH_DATA alimenta valori e P&L della DASHBOARD, mentre _PERFORMANCE alimenta KPI e grafici di rendimento. Il P&L realizzato in MOVIMENTI!U viene incluso nel totale P&L della dashboard.

### 1. MOVIMENTI: input e calcoli per operazione

Intestazioni alla riga 4, record dalla riga 5. Colonne A:U:

| Colonne | Campo | Interpretazione per l'import |
|---|---|---|
| A:D | Data, Conto, Ticker, ISIN | Identità e contesto dell'operazione. Il conto distingue i lotti e le posizioni per account. |
| E:H | Tipo, Quantità, Prezzo EUR, Commissioni EUR | Campi operativi. Quantità di vendita è trattata come quantità da sottrarre dalle consistenze. |
| I:L | Importo movimento EUR, Controvalore EUR, Flusso operazione EUR, Note | Valori calcolati/di supporto e annotazioni. Il flusso è una metrica per il calcolo dei rendimenti, non un saldo di cassa da importare come cassa del portafoglio. |
| M:N | Simbolo quota, Valuta quota | Mapping dello strumento per il prezzo di mercato e la conversione valutaria. |
| O:Q | QTY DOPO MOV., COSTO RESIDUO EUR, PMC CORRENTE EUR | Campi derivati per consistenza e costo; ricostruire e riconciliare dall'ordine delle operazioni, non trattarli automaticamente come input canonici. |
| R:T | Chiave ticker/conto, chiave con simbolo, chiave con valuta | Chiavi ausiliarie generate da formule; non sono identificativi persistenti dell'app. |
| U | P&L REALIZZATO EUR | P&L realizzato calcolato/controllato; utile per riconciliazione e storico anche dopo l'azzeramento della quantità. |

Tipo determina il segno economico della quantità: acquisto e saldo iniziale aggiungono quantità; vendita la sottrae; trasferimenti in entrata/uscita modificano le quantità se presenti. L'app deve modellare esplicitamente questa semantica e preservare le operazioni quando una posizione va a zero. Non assumere che l'utente voglia tracciare liquidità: il foglio è focalizzato sugli strumenti detenuti e i flussi sono usati per i rendimenti, non per una gestione completa della cassa.

Il costo residuo e il PMC sono tracciati a livello ticker/conto (la chiave ticker|conto); la dashboard poi aggrega i conti per ticker. Le vendite realizzano P&L, mentre P&L aperto è valore corrente meno costo residuo. Il totale P&L della dashboard combina P&L aperto e P&L realizzato.

### 2. SETUP: universo, orizzonte, benchmark e valute

- Valuta base corrente: EUR.
- Orizzonte storico corrente: 730 giorni.
- Data iniziale della ricostruzione: minima data di un record Saldo iniziale in MOVIMENTI; il valore è una formula, non una data da assumere immutabile.
- Capacità dichiarata: 35 ticker + 5 benchmark.
- Universo ticker generato dai ticker presenti in MOVIMENTI; simbolo e valuta sono recuperati dal movimento più recente per quel ticker. Benchmark attivi vengono aggiunti all'universo.
- Colonne di configurazione strumenti: sorgente, ticker/chiave, nome, simbolo quotazione, valuta, attivo/stato, valuta normalizzata.
- La tabella benchmark contiene nome, chiave, simbolo, valuta, attivo e nota metodologica. Al momento della verifica, Nasdaq-100 tramite QQQ era attivo; S&P 500 tramite SPY ed EURO STOXX 50 tramite FEZ erano proxy configurabili ma non attive.
- Benchmark indicati come ETF proxy e price return: i dividendi sono esclusi. Non interpretarli come total return degli indici.
- Mappature viste: AAPL / NASDAQ:AAPL / USD; BTC-EUR / CURRENCY:BTCEUR / EUR; EQQQ / LON:EQQQ / GBX; MSFT / NASDAQ:MSFT / USD; NVDA / NASDAQ:NVDA / USD; SPCX / NASDAQ:SPCX / USD; benchmark Nasdaq-100 proxy QQQ / NASDAQ:QQQ / USD. Sono fotografia configurativa, non catalogo fisso per l'app.
- Valute FX normalizzate derivate dall'universo includono GBP e USD; il foglio interroga serie GBP/EUR e USD/EUR.

**Incongruenza da non propagare:** l'istruzione testuale di SETUP chiede di compilare simbolo e valuta nelle colonne N:O di MOVIMENTI. Le intestazioni effettive del ledger mostrano invece SIMBOLO QUOTA in M e VALUTA QUOTA in N. Nell'import fare fede allo schema/intestazioni del ledger (M:N), segnalando il disallineamento; non correggere il workbook come parte dell'import.

### 3. _PRICE_HISTORY: quotazioni e cambi storici

- Coppie di colonne Date / Price, una coppia per ciascun ticker o benchmark; la riga 4 identifica lo strumento e la riga 5 le due intestazioni. Le coppie attive iniziano da A:B; l'area CC:CR contiene coppie data/valore FX.
- Le formule interrogano GOOGLEFINANCE con frequenza giornaliera, da circa TODAY() - orizzonte - 7 fino a TODAY(). Il margine di 7 giorni aiuta a includere la prima quotazione disponibile; weekend/festività possono produrre date mancanti.
- La serie è una finestra mobile calcolata da formule, non un archivio giornaliero immutabile. Il suo contenuto può cambiare nel tempo o presentare lacune/valori non disponibili.
- Per quotazioni in GBP il foglio normalizza i pence GBX dividendo per 100 e applica il cambio GBP/EUR. Per USD applica USD/EUR; EUR non richiede conversione.
- L'app deve importare, se tecnicamente estraibili, snapshot con data, valore, valuta, provider/provenienza e timestamp d'acquisizione. Validare ordinamento, duplicati, buchi, unità (GBX vs GBP) e copertura; non assumere che l'API di Sheets o Apps Script esponga sempre il risultato completo di GOOGLEFINANCE.

### 4. _PERFORMANCE: ricostruzione delle serie del portafoglio

- La colonna A costruisce una sequenza giornaliera mobile di 731 date (oggi meno 730 giorni fino a oggi).
- Per ogni strumento, la quantità alla data dt è ricostruita sommando acquisti, saldi iniziali e trasferimenti in entrata fino a dt, meno vendite e trasferimenti in uscita.
- La valorizzazione usa l'ultima quotazione disponibile non successiva alla data richiesta, applicando il cambio storico della valuta normalizzata e la correzione GBX/100.
- Il totale di portafoglio aggrega i valori EUR; i flussi netti e il TWR giornaliero/indice sono calcolati a parte per evitare di confondere apporti/rientri esterni con performance. Le serie benchmark sono confrontate nello stesso intervallo disponibile.
- È un dato derivato utile a riconciliare il risultato dell'app, non la fonte primaria delle quotazioni né un record contabile. Non importare i totali giornalieri come se fossero prezzi degli strumenti.
- La data iniziale effettiva può essere successiva all'inizio della finestra: la dashboard dichiara N/D per periodi non coperti. Non inventare valori per riempire la parte non osservata.

### 5. _DASH_DATA e DASHBOARD: valutazione corrente e presentazione

- _DASH_DATA espone in V:AG righe per ticker/conto: TICKER, ACCOUNT, QTY, QUOTE SYMBOL, QUOTE CCY, PRICE EUR, VALUE EUR, PMC EUR, COST EUR, P&L EUR, P&L %, TODAY P&L EUR. Le formule aggregano le quantità per account+ticker, recuperano l'ultimo simbolo/valuta, calcolano prezzo corrente con GOOGLEFINANCE e convertono in EUR.
- I dati a livello account sono poi aggregati per ticker nella dashboard; non sostituire un saldo aggregato con più righe di movimenti senza mantenere i collegamenti all'account.
- La dashboard mostra TOTAL VALUE, TOTAL P&L, TODAY P&L, rendimenti 1M/3M/6M/12M/24M, CAGR a 2 anni, posizioni aggregate e grafici Portfolio Value & Total P&L · 2Y e Total return effettivo vs benchmark · EUR.
- Tabella posizioni: TICKER, QTY, TODAY %, TODAY VALUE, VALUE EUR, COST EUR, OPEN P&L, OPEN %, WEIGHT. Il campo TODAY % è la variazione percentuale del titolo (non il P&L in euro).
- TOTAL P&L è P&L aperto aggregato più P&L realizzato nel ledger; OPEN P&L è invece solo la componente ancora aperta. Per la performance temporale usare il TWR, non il semplice rapporto tra valore corrente e capitale investito quando ci sono flussi.
- Il workbook ha formule e intervalli dimensionati; l'app non deve replicarne i limiti di righe o coordinate, ma trattare i dati come tabelle con intestazioni e validazione.

## Procedura di acquisizione raccomandata

1. Leggere i metadati per verificare identità e nomi fogli; acquisire gli intervalli con intestazioni e formule/valori effettivi necessari, senza scrivere nel documento.
2. Importare MOVIMENTI grezzo in staging, mantenendo i valori originali e il numero di riga sorgente per audit; classificare esplicitamente input, formule e chiavi tecniche.
3. Acquisire SETUP e mapping ticker/valute/benchmark come configurazione iniziale versionata, non come configurazione runtime sincronizzata.
4. Tentare l'estrazione di _PRICE_HISTORY e FX come snapshot puntuali; registrare per ogni riga data/valore/fonte e produrre un report di copertura e gap. Se la serie non è estraibile o insufficiente, fare backfill tramite un adapter provider selezionabile e marcare chiaramente la provenienza.
5. Usare _PERFORMANCE e DASHBOARD solo come controlli di riconciliazione: quantità per conto/ticker, valore totale, costo residuo, P&L aperto, P&L realizzato, rendimenti e benchmark, con tolleranze esplicite.
6. Non finalizzare se vi sono righe non mappate, quantità incoerenti, valute/unità dubbie o scostamenti non spiegati. Conservare file grezzo, hash, timestamp e report import.
7. Dopo la migrazione, il database di Investix diventa la fonte autorevole. Nessuna sincronizzazione bidirezionale con Google Sheets.

## Variabilità e limiti

Questo documento registra una fotografia analitica del workbook al 13 ottobre 2026. Non certifica che i valori/formule siano rimasti invariati dopo tale data. La lettura live del foglio in fase di import deve sempre prevalere sul presente documento per verificare schema e contenuto; se vi sono differenze, aggiornare questa scheda e mostrare l'impatto prima di procedere.
