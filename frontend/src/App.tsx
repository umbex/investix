import { AppShell, Badge, Button, Card, Group, Loader, MantineProvider, Modal, NumberInput, Select, SimpleGrid, Stack, Table, Text, TextInput, Title, Tooltip } from "@mantine/core";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api, type InstrumentLookupResult, type LiveQuotesSummary, type Operation, type PerformanceSummary, type PortfolioSummary, type QuotesSummary, type WorkerHealth } from "./api";
import packageJson from "../package.json";
import "./styles.css";

const euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
const kpiEuro = new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
const quantityFormat = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 6 });
const numericValue = (value: string | number) => {
  const normalized = String(value).trim();
  return Number(normalized.includes(",") ? normalized.replace(/\./g, "").replace(",", ".") : normalized);
};
const parseNumericInput = (value: FormDataEntryValue | null) => {
  const normalized = String(value ?? "").trim();
  return normalized.includes(",") ? normalized.replace(/\./g, "").replace(",", ".") : normalized;
};
const amount = (value: string | null | undefined) => value == null ? "N/D" : euro.format(numericValue(value));
const kpiAmount = (value: string | null | undefined) => value == null ? "N/D" : `${kpiEuro.format(numericValue(value) / 1000)}K€`;
const percent = (value: string | null | undefined) => value == null ? "N/D" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 }).format(Number(value));
const chartText = "#b8c2d0";
const RANGE_OPTIONS = ["1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "Tutto"];
// Future option: keep the date-filter implementation available without exposing
// a redundant control in Panoramica while chart range selectors remain active.
const SHOW_OVERVIEW_DATE_FILTER = false;
type SortDirection = "asc" | "desc";
type SortState = { key: string; direction: SortDirection };
type UserSettings = { chartRange: string; quoteRange: string; liveRefreshMinutes: number };
const SETTINGS_STORAGE_KEY = "investix.user-settings";
const DEFAULT_SETTINGS: UserSettings = { chartRange: "Tutto", quoteRange: "3M", liveRefreshMinutes: 5 };
const LIVE_REFRESH_OPTIONS = [
  { value: "0", label: "Disabilitato" },
  { value: "5", label: "Ogni 5 minuti" },
  { value: "10", label: "Ogni 10 minuti" },
  { value: "15", label: "Ogni 15 minuti" },
];
function readUserSettings(): UserSettings {
  try {
    const parsed = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "null") as Partial<UserSettings> | null;
    return { ...DEFAULT_SETTINGS, ...parsed, chartRange: RANGE_OPTIONS.includes(parsed?.chartRange || "") ? parsed!.chartRange! : DEFAULT_SETTINGS.chartRange, quoteRange: RANGE_OPTIONS.includes(parsed?.quoteRange || "") ? parsed!.quoteRange! : DEFAULT_SETTINGS.quoteRange, liveRefreshMinutes: [0, 5, 10, 15].includes(parsed?.liveRefreshMinutes ?? -1) ? parsed!.liveRefreshMinutes! : DEFAULT_SETTINGS.liveRefreshMinutes };
  } catch {
    return DEFAULT_SETTINGS;
  }
}
function writeUserSettings(settings: UserSettings) { localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings)); }
function nextSort(current: SortState | null, key: string, firstDirection: SortDirection = "asc"): SortState { return current?.key === key ? { key, direction: current.direction === "asc" ? "desc" : "asc" } : { key, direction: firstDirection }; }
function compareSortValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0;
  if (a == null) return 1;
  if (b == null) return -1;
  const left = String(a);
  const right = String(b);
  const leftNumber = Number(left);
  const rightNumber = Number(right);
  if (left.trim() !== "" && right.trim() !== "" && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) return leftNumber - rightNumber;
  return left.localeCompare(right, "it", { numeric: true, sensitivity: "base" });
}
function sortedBy<T>(items: T[], sort: SortState | null, value: (item: T, key: string) => unknown): T[] {
  if (!sort) return items;
  return [...items].sort((a, b) => { const result = compareSortValues(value(a, sort.key), value(b, sort.key)); return sort.direction === "asc" ? result : -result; });
}
const rangeDays = (range: string) => {
  if (range === "1W") return 7;
  if (range === "1M") return 30;
  if (range === "3M") return 90;
  if (range === "6M") return 180;
  if (range === "YTD") {
    const now = new Date();
    return Math.max(1, Math.ceil((now.getTime() - new Date(now.getFullYear(), 0, 1).getTime()) / 86400000));
  }
  if (range === "1Y") return 365;
  if (range === "2Y") return 730;
  return 3650;
};

export function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [page, setPage] = useState<"dashboard" | "operations" | "settings">("dashboard");
  const [settings, setSettings] = useState<UserSettings>(() => readUserSettings());
  const updateSettings = (next: UserSettings) => { setSettings(next); writeUserSettings(next); };
  useEffect(() => { void api.authMode().then(({ bypass }) => { if (bypass) setAuthenticated(true); }).catch(() => undefined); }, []);
  if (!authenticated) return <MantineProvider defaultColorScheme="dark"><Login onAuthenticated={() => setAuthenticated(true)} /></MantineProvider>;
  return <MantineProvider defaultColorScheme="dark"><AppShell header={{ height: 64 }} padding="md" className="investix-shell">
    <AppShell.Header px="md" py="sm" className="topbar"><Group justify="space-between"><Group gap="xs"><Title order={1} size="h3">Investix</Title><Badge color="cyan" variant="light">v{packageJson.version}</Badge></Group><Group gap="xs"><Button variant={page === "dashboard" ? "light" : "subtle"} size="xs" onClick={() => setPage("dashboard")}>Panoramica</Button><Button variant={page === "operations" ? "light" : "subtle"} size="xs" onClick={() => setPage("operations")}>Registro</Button><Button variant={page === "settings" ? "light" : "subtle"} size="xs" onClick={() => setPage("settings")}>Impostazioni</Button></Group></Group></AppShell.Header>
    <AppShell.Main>{page === "dashboard" ? <Dashboard settings={settings} onOpenRegistry={() => setPage("operations")} /> : page === "operations" ? <Operations /> : <SettingsPage settings={settings} onChange={updateSettings} />}</AppShell.Main>
  </AppShell></MantineProvider>;
}

function SettingsPage({ settings, onChange }: { settings: UserSettings; onChange: (settings: UserSettings) => void }) {
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Preferenze locali</Text><Title order={2}>Impostazioni</Title></div><Card withBorder><Title order={3}>Dashboard</Title><Text size="sm" c="dimmed" mt="xs">Queste preferenze si applicano subito e non richiedono il riavvio dei servizi.</Text><SimpleGrid cols={{ base: 1, sm: 2 }} mt="md"><Select label="Range grafici predefinito" value={settings.chartRange} onChange={(value) => onChange({ ...settings, chartRange: value || DEFAULT_SETTINGS.chartRange })} data={RANGE_OPTIONS} /><Select label="Storico Quotazioni predefinito" value={settings.quoteRange} onChange={(value) => onChange({ ...settings, quoteRange: value || DEFAULT_SETTINGS.quoteRange })} data={RANGE_OPTIONS} /><Select label="Aggiornamento Quotazioni" value={String(settings.liveRefreshMinutes)} onChange={(value) => onChange({ ...settings, liveRefreshMinutes: Number(value || DEFAULT_SETTINGS.liveRefreshMinutes) })} data={LIVE_REFRESH_OPTIONS} /></SimpleGrid></Card><Card withBorder><Title order={3}>Configurazione tecnica</Title><Text size="sm" c="dimmed" mt="xs">Provider, API key, limiti quota, database e worker restano configurazioni server e non vengono esposti nella UI.</Text></Card></Stack>;
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { await api.login(String(form.get("username")), String(form.get("password"))); onAuthenticated(); } catch { setError("Credenziali non valide o API non disponibile"); }
  }
  return <main className="login"><Card withBorder radius="md" p="xl"><Title order={1}>Investix</Title><Text c="dimmed" mb="lg">Accesso privato</Text><form onSubmit={submit}><Stack><TextInput name="username" label="Utente" required autoComplete="username" /><TextInput name="password" type="password" label="Password" required autoComplete="current-password" />{error && <Text c="red" size="sm">{error}</Text>}<Button type="submit">Accedi</Button></Stack></form></Card></main>;
}

function Dashboard({ settings, onOpenRegistry }: { settings: UserSettings; onOpenRegistry: () => void }) {
  const [summary, setSummary] = useState<PortfolioSummary>();
  const [quotePositions, setQuotePositions] = useState<PortfolioSummary["positions"]>([]);
  const [performance, setPerformance] = useState<PerformanceSummary>();
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth>({ status: "unknown" });
  const [quotes, setQuotes] = useState<QuotesSummary>();
  const [liveQuotes, setLiveQuotes] = useState<LiveQuotesSummary>();
  const [quoteRange, setQuoteRange] = useState(settings.quoteRange);
  const [range, setRange] = useState(settings.chartRange);
  const [ticker, setTicker] = useState("");
  const [account, setAccount] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const load = async (filter = ticker) => { setError(""); try { const nextSummary = await api.portfolio(filter || undefined, account || undefined); let nextQuotePositions = nextSummary.positions; if (filter) { try { nextQuotePositions = (await api.portfolio(undefined, account || undefined)).positions; } catch { /* keep filtered positions if the unfiltered lookup fails */ } } try { setPerformance(await api.performance(filter || undefined, dateFrom || undefined, dateTo || undefined)); } catch { setPerformance(undefined); } try { setWorkerHealth(await api.workerHealth()); } catch { setWorkerHealth({ status: "unknown" }); } try { setQuotes(await api.quotes(rangeDays(quoteRange))); } catch { setQuotes(undefined); } setSummary(nextSummary); setQuotePositions(nextQuotePositions); } catch (reason) { setError(reason instanceof Error ? reason.message : "Dati non disponibili"); } };
  useEffect(() => { void load(""); }, []);
  const changeQuoteRange = (value: string | null) => { const nextRange = value || "3M"; setQuoteRange(nextRange); void api.quotes(rangeDays(nextRange)).then(setQuotes).catch(() => setQuotes(undefined)); };
  const positions = summary?.positions ?? [];
  const liveSessionId = useRef(`tab-${Math.random().toString(36).slice(2)}`);
  useEffect(() => {
    const symbols = quotePositions.filter((position) => marketStatus(position.market_data_venue).open).map((position) => position.ticker);
    if (!symbols.length) return;
    let disposed = false;
    const refresh = () => {
      if (document.visibilityState === "hidden") return;
      void api.liveQuotes(symbols, liveSessionId.current).then((result) => { if (!disposed) setLiveQuotes(result); }).catch(() => undefined);
    };
    if (settings.liveRefreshMinutes === 0) return;
    refresh();
    const timer = window.setInterval(refresh, settings.liveRefreshMinutes * 60 * 1000);
    const onVisibility = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => { disposed = true; window.clearInterval(timer); document.removeEventListener("visibilitychange", onVisibility); };
  }, [quotePositions.map((position) => position.ticker).join(","), settings.liveRefreshMinutes]);
  return <Stack gap="lg" className="dashboard">
    <Group justify="space-between" align="end" className="dashboard-title"><div><Text c="dimmed">Portafoglio privato</Text><Title order={2}>Panoramica</Title></div><Badge color={summary?.valuation_status === "available" ? "teal" : "yellow"}>{summary?.valuation_status === "available" ? "Quotazioni disponibili" : "Quotazioni mancanti"}</Badge></Group>
    <Group className="filter-bar" align="end"><Select label="Ticker" placeholder="Tutti" clearable value={ticker || null} onChange={(value) => setTicker(value || "")} data={positions.map((position) => position.ticker)} /><Select label="Account" placeholder="Tutti" clearable value={account || null} onChange={(value) => setAccount(value || "")} data={Array.from(new Set(positions.flatMap((position) => position.accounts.map((item) => item.name)))).sort()} />{SHOW_OVERVIEW_DATE_FILTER && <><TextInput label="Da" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.currentTarget.value)} /><TextInput label="A" type="date" value={dateTo} onChange={(event) => setDateTo(event.currentTarget.value)} /></>}<Button onClick={() => void load()}>Applica</Button><Button variant="subtle" onClick={() => { setTicker(""); setAccount(""); setDateFrom(""); setDateTo(""); void load(""); }}>Azzera</Button></Group>
    {error && <Card withBorder><Text c="red">{error}</Text><Button mt="sm" size="xs" onClick={() => void load()}>Riprova</Button></Card>}
    {!summary && !error ? <Group justify="center" py="xl"><Loader aria-label="Caricamento portafoglio" /></Group> : <><SimpleGrid cols={{ base: 1, xs: 2, md: 5 }} spacing="md"><Metric label="Valore portafoglio" value={kpiAmount(summary?.kpis.market_value_eur)} note={summary?.valuation_status === "available" ? "Ultima osservazione persistita" : "Quotazioni mancanti"} /><Metric label="Capitale aperto" value={kpiAmount(summary?.kpis.open_cost_eur)} note="Costo ricostruito dal ledger" /><Metric label="P&L realizzato" value={kpiAmount(summary?.kpis.realized_pnl_eur)} note="Vendite registrate" positive={Number(summary?.kpis.realized_pnl_eur) > 0} /><Metric label="P&L non realizzato" value={kpiAmount(summary?.kpis.unrealized_pnl_eur)} note="Disponibile con quotazioni EOD" positive={Number(summary?.kpis.unrealized_pnl_eur) > 0} /><Metric label="Rendimento TWR" value={performance?.total_return == null ? "N/D" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(Number(performance.total_return))} note="Rendimento ponderato nel tempo" positive={Number(performance?.total_return) > 0} /></SimpleGrid>
      <Card withBorder radius="md"><Group justify="space-between" align="center"><Title order={3}>Quotazioni</Title><Select aria-label="Storico quotazioni" size="xs" value={quoteRange} onChange={changeQuoteRange} data={RANGE_OPTIONS} /></Group><QuotesTable quotes={quotes} liveQuotes={liveQuotes} positions={quotePositions} /></Card>
      <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Posizioni</Title><Button variant="subtle" size="xs" onClick={onOpenRegistry}>Registro operazioni</Button></Group><PositionTable positions={positions} totalOpenCost={summary!.kpis.open_cost_eur} totalMarketValue={summary!.kpis.market_value_eur} /></Card>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Valore nel tempo</Title><Group gap="xs"><Select aria-label="Intervallo grafico" size="xs" value={range} onChange={(value) => setRange(value || "Tutto")} data={RANGE_OPTIONS} /><Badge variant="outline">EUR</Badge></Group></Group><PortfolioChart performance={performance} range={range} /><Text size="xs" c="dimmed">{performance?.methodology || "Serie non disponibile: servono osservazioni storiche valide."}</Text></Card>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Rendimento vs benchmark</Title><Group gap="xs"><Select aria-label="Intervallo benchmark" size="xs" value={range} onChange={(value) => setRange(value || "Tutto")} data={RANGE_OPTIONS} /><Badge variant="outline">Base comune 0%</Badge></Group></Group><BenchmarkChart performance={performance} range={range} /><Text size="xs" c="dimmed">I benchmark price-return escludono i dividendi: la comparabilità è indicata nella legenda.</Text></Card>
      <Card withBorder radius="md"><Title order={3}>Stato dati</Title><Stack mt="md" gap="sm"><Status label="Ledger" value={String(positions.length) + " strumenti"} /><Status label="Provider prezzi" value={summary?.valuation_status === "available" ? "Osservazioni persistite" : "Nessuna osservazione"} /><Status label="Worker EOD" value={workerHealth.status === "ok" ? `Attivo${workerHealth.provider === "disabled" ? " · provider disabilitato" : ""}` : workerHealth.status === "not_configured" ? "Non configurato" : "Non verificato"} /><Status label="Ultima quotazione" value={latestObservation(positions)} /></Stack></Card></>}
  </Stack>;
}

function SortableHeader({ label, sort, sortKey, onSort }: { label: string; sort: SortState | null; sortKey: string; onSort: (key: string) => void }) {
  const active = sort?.key === sortKey;
  return <Table.Th aria-sort={active ? sort!.direction === "asc" ? "ascending" : "descending" : "none"}><Button variant="subtle" size="compact-xs" onClick={() => onSort(sortKey)}><span>{label}</span></Button><span aria-hidden="true">{active ? ` ${sort!.direction === "asc" ? "↑" : "↓"}` : " ↕"}</span></Table.Th>;
}

function PositionTable({ positions, totalOpenCost, totalMarketValue }: { positions: PortfolioSummary["positions"]; totalOpenCost: string; totalMarketValue: string | null }) {
  const [sort, setSort] = useState<SortState | null>(null);
  const sortedPositions = useMemo(() => sortedBy(positions, sort, (position, key) => ({ ticker: position.ticker, quantity: position.quantity, cost: position.open_cost_eur, value: position.market_value_eur, pnl: position.unrealized_pnl_eur, status: position.market_data_status }[key as "ticker" | "quantity" | "cost" | "value" | "pnl" | "status"])), [positions, sort]);
  const onSort = (key: string) => setSort((current) => nextSort(current, key, ["quantity", "cost", "value", "pnl"].includes(key) ? "desc" : "asc"));
  if (!positions.length) return <Text c="dimmed" mt="md">Nessuna posizione per il filtro selezionato.</Text>;
  return <Table.ScrollContainer minWidth={680}><Table mt="md" striped highlightOnHover><Table.Thead><Table.Tr><SortableHeader label="Strumento" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Quantità" sort={sort} sortKey="quantity" onSort={onSort} /><SortableHeader label="Costo EUR" sort={sort} sortKey="cost" onSort={onSort} /><SortableHeader label="Valore" sort={sort} sortKey="value" onSort={onSort} /><SortableHeader label="P&L" sort={sort} sortKey="pnl" onSort={onSort} /><SortableHeader label="Stato" sort={sort} sortKey="status" onSort={onSort} /></Table.Tr></Table.Thead><Table.Tbody>{sortedPositions.map((position) => <Table.Tr key={position.ticker}><Table.Td><Text fw={600}>{position.ticker}</Text><Text size="xs" c="dimmed">{position.accounts.map((item) => item.name).join(" · ")}</Text></Table.Td><Table.Td>{Number(position.quantity).toLocaleString("it-IT")}</Table.Td><Table.Td><Text>{amount(position.open_cost_eur)}</Text><Text size="xs" c="dimmed">{percent(totalOpenCost && Number(totalOpenCost) ? String(Number(position.open_cost_eur) / Number(totalOpenCost)) : null)}</Text></Table.Td><Table.Td><Text>{amount(position.market_value_eur)}</Text><Text size="xs" c="dimmed">{percent(position.market_value_eur && totalMarketValue ? String(Number(position.market_value_eur) / Number(totalMarketValue)) : null)}</Text></Table.Td><Table.Td>{amount(position.unrealized_pnl_eur)}</Table.Td><Table.Td><Tooltip label={marketStatusLabel(position)}><span className={`market-status-icon ${position.market_data_status}`} role="img" aria-label={position.market_data_status === "available" ? "Quotazione disponibile" : "Quotazione mancante"}>{position.market_data_status === "available" ? "✓" : "!"}</span></Tooltip></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>;
}

function marketStatusLabel(position: PortfolioSummary["positions"][number]): string {
  if (position.market_data_status === "missing") return "Nessuna quotazione persistita per questo titolo";
  return `Quotazione disponibile${position.market_data_provider ? ` · ${position.market_data_provider}` : ""}`;
}

function latestObservation(positions: PortfolioSummary["positions"]): string {
  const values = positions.map((position) => position.last_observed_at).filter((value): value is string => value != null).sort();
  const latest = values[values.length - 1];
  return latest ? new Date(latest).toLocaleString("it-IT") : "Non disponibile";
}

function QuotesTable({ quotes, liveQuotes, positions }: { quotes?: QuotesSummary; liveQuotes?: LiveQuotesSummary; positions: PortfolioSummary["positions"] }) {
  const liveByTicker = new Map((liveQuotes?.items ?? []).map((item) => [item.ticker, item]));
  const retryLabel = liveQuotes?.retry_after ? ` dopo le ${new Date(liveQuotes.retry_after * 1000).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}` : "";
  const [sort, setSort] = useState<SortState | null>(null);
  const items = useMemo(() => sortedBy(quotes?.items ?? [], sort, (item, key) => ({ ticker: item.ticker, price: item.price_eur, change: item.change_percent, pnl: todayPnlAmount(positions.find((candidate) => candidate.ticker === item.ticker)?.quantity, liveByTicker.get(item.ticker)?.price_eur ?? item.price_eur, liveByTicker.get(item.ticker)?.change_percent ?? item.change_percent) }[key as "ticker" | "price" | "change" | "pnl"])), [quotes?.items, sort, positions, liveQuotes]);
  const onSort = (key: string) => setSort((current) => nextSort(current, key, ["price", "change", "pnl"].includes(key) ? "desc" : "asc"));
  if (!quotes?.items?.length) return <Text c="dimmed" mt="md">Quotazioni non disponibili.</Text>;
  return <><Table.ScrollContainer minWidth={760}><Table mt="md" striped><Table.Thead><Table.Tr><SortableHeader label="Ticker" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Ultimo" sort={sort} sortKey="price" onSort={onSort} /><SortableHeader label="Variazione" sort={sort} sortKey="change" onSort={onSort} /><SortableHeader label="Today P&L" sort={sort} sortKey="pnl" onSort={onSort} /><Table.Th>Trend</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => { const live = liveByTicker.get(item.ticker); const livePrice = live?.price_eur ?? (live ? `${live.price} ${live.currency}` : null); const currentPrice = live?.price_eur ?? item.price_eur; const position = positions.find((candidate) => candidate.ticker === item.ticker); const quantity = position?.quantity; const changePercent = live?.change_percent ?? item.change_percent; const todayPnl = todayPnlAmount(quantity, currentPrice, changePercent); const market = marketStatus(position?.market_data_venue); return <Table.Tr key={item.ticker}><Table.Td><Group gap="xs" wrap="nowrap"><Text fw={600}>{item.ticker}</Text><Tooltip label={market.label}><span className={`market-open-dot ${market.open ? "open" : "closed"}`} role="img" aria-label={market.label} /></Tooltip></Group><Text size="xs" c="dimmed">{live ? `Live · ${new Date(live.observed_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}` : new Date(item.observed_at).toLocaleString("it-IT")}</Text></Table.Td><Table.Td>{livePrice == null ? amount(item.price_eur) : typeof livePrice === "string" && livePrice.includes(" ") ? livePrice : amount(livePrice)}</Table.Td><Table.Td c={changePercent == null ? "dimmed" : Number(changePercent) >= 0 ? "teal" : "red"}>{changePercent == null ? "N/D" : `${Number(changePercent).toLocaleString("it-IT", { maximumFractionDigits: 2 })}%`}</Table.Td><Table.Td c={todayPnl == null ? "dimmed" : todayPnl >= 0 ? "teal" : "red"}>{todayPnl == null ? "N/D" : amount(String(todayPnl))}</Table.Td><Table.Td><Sparkline points={item.points.map((point) => Number(point.price_eur))} label={`Trend ${item.ticker}`} /></Table.Td></Table.Tr>; })}</Table.Tbody></Table></Table.ScrollContainer>{liveQuotes?.status === "quota_exhausted" && <Text size="xs" c="yellow" mt="xs">Limite provider raggiunto: attendere la prossima finestra disponibile{retryLabel}.</Text>}{liveQuotes?.status === "pending" && <Text size="xs" c="dimmed" mt="xs">Aggiornamento live in coda.</Text>}</>;
}

function marketStatus(venue: string | null | undefined): { open: boolean; label: string } {
  const normalized = (venue || "").toUpperCase();
  if (["BINANCE", "COINBASE", "COINBASE PRO", "KRAKEN", "BITSTAMP"].includes(normalized)) return { open: true, label: `Mercato aperto${venue ? ` · ${venue}` : ""}` };
  const timezone = normalized === "NASDAQ" || normalized === "NYSE" ? "America/New_York" : "Europe/Rome";
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: timezone, weekday: "short", hour: "numeric", minute: "numeric", hour12: false }).formatToParts(new Date());
  const weekday = parts.find((part) => part.type === "weekday")?.value;
  const hour = Number(parts.find((part) => part.type === "hour")?.value);
  const minute = Number(parts.find((part) => part.type === "minute")?.value);
  const current = hour * 60 + minute;
  const start = normalized === "NASDAQ" || normalized === "NYSE" ? 570 : 540;
  const end = normalized === "NASDAQ" || normalized === "NYSE" ? 960 : 1050;
  const open = !["Sat", "Sun"].includes(weekday || "") && current >= start && current < end;
  return { open, label: `Mercato ${open ? "aperto" : "chiuso"}${venue ? ` · ${venue}` : ""}` };
}

function todayPnlAmount(quantity: string | undefined, price: string | number | null, changePercent: string | null): number | null {
  if (!quantity || price == null || changePercent == null) return null;
  const current = typeof price === "number" ? price : numericValue(price);
  const change = Number(changePercent) / 100;
  if (!Number.isFinite(current) || !Number.isFinite(change) || change <= -1) return null;
  return numericValue(quantity) * (current - current / (1 + change));
}

function Sparkline({ points, label }: { points: number[]; label: string }) {
  if (points.length < 2) return <Text size="xs" c="dimmed">N/D</Text>;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const coordinates = points.map((point, index) => `${(index / (points.length - 1)) * 120},${26 - ((point - min) / span) * 22}`).join(" ");
  return <svg className="quote-sparkline" viewBox="0 0 120 28" role="img" aria-label={label}><polyline points={coordinates} fill="none" vectorEffect="non-scaling-stroke" /></svg>;
}

function Operations() {
  const [items, setItems] = useState<Operation[]>([]);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Operation | null>(null);
  const [reason, setReason] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [tradeDate, setTradeDate] = useState("");
  const [note, setNote] = useState("");
  const [ticker, setTicker] = useState("");
  const [lookupItems, setLookupItems] = useState<InstrumentLookupResult[]>([]);
  const [selectedLookup, setSelectedLookup] = useState<string | null>(null);
  const [lookupStatus, setLookupStatus] = useState("");
  const [sort, setSort] = useState<SortState | null>(null);
  const load = async () => { try { setItems((await api.operations()).items); } catch (reason) { setError(reason instanceof Error ? reason.message : "Registro non disponibile"); } };
  const startEdit = (item: Operation) => { setEditing(item); setReason(""); setQuantity(item.quantity); setPrice(item.unit_price_eur); setTradeDate(item.trade_date); setNote(item.note || ""); setError(""); };
  const revise = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (!editing || !reason.trim()) return; try { await api.reviseOperation(editing.id, { reason: reason.trim(), quantity, unit_price_eur: price, trade_date: tradeDate, note: note || null }); setEditing(null); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile correggere il movimento"); } };
  const cancel = async (item: Operation) => { if (!window.confirm(`Annullare il movimento ${item.ticker} del ${item.trade_date}?`)) return; const cancellationReason = window.prompt("Motivo dell'annullamento"); if (!cancellationReason?.trim()) return; try { await api.cancelOperation(item.id, cancellationReason.trim()); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile annullare il movimento"); } };
  const lookup = async () => { if (!ticker.trim()) return; setLookupStatus("Ricerca..."); setLookupItems([]); setSelectedLookup(null); try { const result = await api.lookupInstrument(ticker.trim()); setLookupItems(result.items); setLookupStatus(result.status === "ok" ? (result.items.length ? "Seleziona il listing corretto" : "Nessun listing trovato") : (result.message || "Provider non disponibile")); } catch (reason) { setLookupStatus(reason instanceof Error ? reason.message : "Lookup non disponibile"); } };
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = new FormData(event.currentTarget);
    if (lookupItems.length && !selectedLookup) { setError("Selezionare il listing provider prima di registrare il movimento"); return; }
    const selected = lookupItems.find((item) => item.symbol === selectedLookup);
    try { await api.createOperation({ account_name: values.get("account"), ticker: ticker.trim().toUpperCase(), quote_symbol: selected?.symbol ?? null, quote_venue: selected?.exchange ?? null, quote_currency: selected?.currency ?? null, kind: values.get("kind"), quantity: parseNumericInput(values.get("quantity")), unit_price_eur: parseNumericInput(values.get("price")), original_unit_price: values.get("original_price") ? parseNumericInput(values.get("original_price")) : null, original_currency: values.get("original_currency") || null, trade_date: values.get("date"), settlement_date: values.get("settlement_date") || null, note: values.get("note") || null, is_approximate: values.get("is_approximate") === "on", source_order: 0 }); event.currentTarget.reset(); setTicker(""); setLookupItems([]); setSelectedLookup(null); setLookupStatus(""); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile registrare il movimento"); }
  }
  const sortedItems = useMemo(() => sortedBy(items, sort, (item, key) => ({ date: item.trade_date, account: item.account_name, ticker: item.ticker, kind: item.kind, quantity: item.quantity, price: item.unit_price_eur, context: item.note || (item.is_approximate ? "Approssimato" : "") }[key as "date" | "account" | "ticker" | "kind" | "quantity" | "price" | "context"])), [items, sort]);
  const onSort = (key: string) => setSort((current) => nextSort(current, key, ["quantity", "price"].includes(key) ? "desc" : "asc"));
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Ledger con audit</Text><Title order={2}>Registro operazioni</Title></div><Card withBorder><form onSubmit={submit}><SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}><TextInput required name="account" label="Account" /><Group align="end" gap="xs"><TextInput required name="ticker" label="Ticker" value={ticker} onChange={(event) => { setTicker(event.currentTarget.value); setLookupItems([]); setSelectedLookup(null); setLookupStatus(""); }} /><Button type="button" variant="light" onClick={() => void lookup()}>Cerca</Button></Group>{lookupItems.length > 0 && <Select required label="Listing provider" placeholder="Seleziona il titolo" value={selectedLookup} onChange={setSelectedLookup} data={lookupItems.map((item) => ({ value: item.symbol, label: `${item.symbol} · ${item.exchange} · ${item.currency} · ${item.name}` }))} />}{lookupStatus && <Text size="xs" c="dimmed">{lookupStatus}</Text>}<Select required name="kind" label="Tipo" data={[{ value: "BUY", label: "Acquisto" }, { value: "SELL", label: "Vendita" }, { value: "OPENING_BALANCE", label: "Saldo iniziale" }, { value: "TRANSFER_IN", label: "Trasferimento in entrata" }, { value: "TRANSFER_OUT", label: "Trasferimento in uscita" }, { value: "ADJUSTMENT", label: "Rettifica" }, { value: "DIVIDEND", label: "Dividendo" }, { value: "FEE", label: "Commissione" }]} /><NumberInput required name="quantity" label="Quantità" decimalScale={6} /><NumberInput required name="price" label="Prezzo EUR" min={0} decimalScale={4} /><TextInput name="original_price" label="Prezzo originale" /><TextInput name="original_currency" label="Valuta originale" maxLength={8} /><TextInput required name="date" type="date" label="Data" defaultValue={new Date().toISOString().slice(0, 10)} /><TextInput name="settlement_date" type="date" label="Data regolamento" /><TextInput name="note" label="Nota" /><label><input name="is_approximate" type="checkbox" /> Dato approssimativo</label></SimpleGrid><Button mt="md" type="submit">Registra movimento</Button></form></Card>{error && <Text c="red">{error}</Text>}<Card withBorder><Table.ScrollContainer minWidth={900}><Table><Table.Thead><Table.Tr><SortableHeader label="Data" sort={sort} sortKey="date" onSort={onSort} /><SortableHeader label="Account" sort={sort} sortKey="account" onSort={onSort} /><SortableHeader label="Ticker" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Tipo" sort={sort} sortKey="kind" onSort={onSort} /><SortableHeader label="Quantità" sort={sort} sortKey="quantity" onSort={onSort} /><SortableHeader label="Prezzo" sort={sort} sortKey="price" onSort={onSort} /><SortableHeader label="Contesto" sort={sort} sortKey="context" onSort={onSort} /><Table.Th>Azioni</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{sortedItems.map((item) => <Table.Tr key={item.id}><Table.Td>{new Date(item.trade_date).toLocaleDateString("it-IT")}</Table.Td><Table.Td>{item.account_name}</Table.Td><Table.Td>{item.ticker}</Table.Td><Table.Td>{item.kind}</Table.Td><Table.Td>{item.quantity}</Table.Td><Table.Td>{amount(item.unit_price_eur)}</Table.Td><Table.Td>{item.note || (item.is_approximate ? "Approssimato" : "—")}</Table.Td><Table.Td><Group gap="xs" wrap="nowrap"><Button size="xs" variant="light" onClick={() => startEdit(item)}>Modifica</Button><Button size="xs" variant="subtle" color="red" onClick={() => void cancel(item)}>Annulla</Button></Group></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card><Modal opened={editing !== null} onClose={() => setEditing(null)} title={editing ? `Correggi ${editing.ticker}` : "Correggi movimento"}><form onSubmit={revise}><Stack><TextInput label="Motivazione" required value={reason} onChange={(event) => setReason(event.currentTarget.value)} /><NumberInput label="Quantità" required value={quantity} onChange={(value) => setQuantity(String(value))} min={0} decimalScale={6} /><NumberInput label="Prezzo EUR" required value={price} onChange={(value) => setPrice(String(value))} min={0} decimalScale={4} /><TextInput label="Data" type="date" required value={tradeDate} onChange={(event) => setTradeDate(event.currentTarget.value)} /><TextInput label="Nota" value={note} onChange={(event) => setNote(event.currentTarget.value)} /><Group justify="flex-end"><Button variant="subtle" onClick={() => setEditing(null)}>Chiudi</Button><Button type="submit">Salva correzione</Button></Group></Stack></form></Modal></Stack>;
}

function Metric({ label, value, note, positive = false }: { label: string; value: string; note: string; positive?: boolean }) { return <Card withBorder radius="md"><Text size="sm" c="dimmed">{label}</Text><Text className={positive ? "positive metric" : "metric"}>{value}</Text><Text size="xs" c="dimmed">{note}</Text></Card>; }
function Status({ label, value }: { label: string; value: string }) { return <Group justify="space-between" wrap="nowrap"><Text size="sm">{label}</Text><Text size="sm" c="dimmed">{value}</Text></Group>; }
function PortfolioChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range);
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); chart.setOption(points.length ? { grid: { left: 48, right: 16, top: 18, bottom: 28 }, tooltip: { trigger: "axis", valueFormatter: (value: number) => euro.format(value) }, xAxis: { type: "category", data: points.map((point) => point.date), axisLabel: { color: chartText, formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) }, axisLine: { lineStyle: { color: chartText } } }, yAxis: { type: "value", axisLabel: { color: chartText, formatter: (value: number) => euro.format(value) }, axisLine: { lineStyle: { color: chartText } } }, series: [{ type: "line", data: points.map((point) => Number(point.value_eur)), smooth: true, showSymbol: false, areaStyle: { opacity: 0.16 }, lineStyle: { color: "#22d3ee" } }] } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "Nessuna serie storica disponibile", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points]);
  return <div className="chart" ref={element} role="img" aria-label="Grafico del valore del portafoglio" />;
}

function BenchmarkChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range).filter((point) => point.cumulative_return != null);
  const benchmarks = (performance?.benchmarks ?? []).map((benchmark) => ({ ...benchmark, points: withinRange(benchmark.points, range) }));
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, components.LegendComponent, components.DataZoomComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); const dates = points.map((point) => point.date); const series = [{ name: "Portafoglio TWR", type: "line", data: points.map((point) => Number(point.cumulative_return)), smooth: true, showSymbol: false, lineStyle: { color: "#22d3ee" } }, ...benchmarks.map((benchmark) => ({ name: `${benchmark.name} (${benchmark.methodology === "price_return" ? "price" : "total"})`, type: "line", data: dates.map((day) => Number(benchmark.points.find((point) => point.date === day)?.return ?? NaN)), smooth: true, showSymbol: false }))]; chart.setOption(points.length ? { grid: { left: 52, right: 18, top: 36, bottom: 42 }, legend: { top: 0, textStyle: { color: chartText } }, tooltip: { trigger: "axis", valueFormatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(value) }, dataZoom: [{ type: "inside" }], xAxis: { type: "category", data: dates, axisLabel: { color: chartText, formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) }, axisLine: { lineStyle: { color: chartText } } }, yAxis: { type: "value", axisLabel: { color: chartText, formatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 0 }).format(value) }, axisLine: { lineStyle: { color: chartText } } }, series } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "Benchmark o rendimento non disponibili", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points, benchmarks]);
  return <div className="chart" ref={element} role="img" aria-label="Grafico del rendimento del portafoglio rispetto ai benchmark" />;
}

function withinRange<T extends { date: string }>(points: T[], range: string): T[] {
  if (!points.length || range === "Tutto") return points;
  const end = new Date(points.at(-1)!.date);
  const start = new Date(end);
  if (range === "YTD") start.setMonth(0, 1); else if (range === "1W") start.setDate(start.getDate() - 7); else start.setMonth(start.getMonth() - Number(range.replace("M", "").replace("Y", "")) * (range.endsWith("Y") ? 12 : 1));
  return points.filter((point) => new Date(point.date) >= start);
}
