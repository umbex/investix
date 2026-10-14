import { AppShell, Badge, Button, Card, Group, Loader, MantineProvider, Modal, NumberInput, Select, SimpleGrid, Stack, Switch, Table, Text, TextInput, Title, Tooltip } from "@mantine/core";
import { Fragment, FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { api, type BenchmarkConfig, type InstrumentCatalogItem, type InstrumentLookupResult, type LiveQuotesSummary, type Operation, type PerformanceSummary, type PortfolioSummary, type QuotesSummary, type WorkerHealth } from "./api";
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
const amount = (value: string | null | undefined) => value == null ? "N/A" : euro.format(numericValue(value));
const kpiAmount = (value: string | null | undefined) => value == null ? "N/A" : `${kpiEuro.format(numericValue(value) / 1000)}K€`;
const percent = (value: string | null | undefined) => value == null ? "N/A" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 }).format(Number(value));
const chartText = "#b8c2d0";
const RANGE_OPTIONS = ["1W", "1M", "3M", "6M", "YTD", "1Y", "2Y", "All"];
// Future option: keep the date-filter implementation available without exposing
// a redundant control in Panoramica while chart range selectors remain active.
const SHOW_OVERVIEW_DATE_FILTER = false;
type SortDirection = "asc" | "desc";
type SortState = { key: string; direction: SortDirection };
const KPI_DEFINITIONS = [
  { key: "marketValue", label: "Portfolio value" },
  { key: "todayPnl", label: "Today P&L" },
  { key: "openCost", label: "Open capital" },
  { key: "realizedPnl", label: "Realized P&L" },
  { key: "unrealizedPnl", label: "Unrealized P&L" },
  { key: "twr", label: "TWR return" },
] as const;
const DEFAULT_KPI_ORDER = KPI_DEFINITIONS.map((definition) => definition.key);
type KpiKey = (typeof KPI_DEFINITIONS)[number]["key"];
type UserSettings = { chartRange: string; quoteRange: string; liveRefreshMinutes: number; kpiOrder: KpiKey[]; hiddenKpis: KpiKey[] };
const SETTINGS_STORAGE_KEY = "investix.user-settings";
const DEFAULT_SETTINGS: UserSettings = { chartRange: "All", quoteRange: "3M", liveRefreshMinutes: 5, kpiOrder: DEFAULT_KPI_ORDER, hiddenKpis: [] };
const LIVE_REFRESH_OPTIONS = [
  { value: "0", label: "Disabled" },
  { value: "5", label: "Every 5 minutes" },
  { value: "10", label: "Every 10 minutes" },
  { value: "15", label: "Every 15 minutes" },
];
function readUserSettings(): UserSettings {
  try {
    const parsed = JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) || "null") as Partial<UserSettings> | null;
    const storedOrder = Array.isArray(parsed?.kpiOrder) ? parsed!.kpiOrder!.filter((key): key is KpiKey => DEFAULT_KPI_ORDER.includes(key as KpiKey)) : DEFAULT_KPI_ORDER;
    const kpiOrder = [...new Set([...storedOrder, ...DEFAULT_KPI_ORDER])];
    const hiddenKpis = Array.isArray(parsed?.hiddenKpis) ? parsed!.hiddenKpis!.filter((key): key is KpiKey => DEFAULT_KPI_ORDER.includes(key as KpiKey)) : [];
    return { ...DEFAULT_SETTINGS, ...parsed, chartRange: RANGE_OPTIONS.includes(parsed?.chartRange || "") ? parsed!.chartRange! : DEFAULT_SETTINGS.chartRange, quoteRange: RANGE_OPTIONS.includes(parsed?.quoteRange || "") ? parsed!.quoteRange! : DEFAULT_SETTINGS.quoteRange, liveRefreshMinutes: [0, 5, 10, 15].includes(parsed?.liveRefreshMinutes ?? -1) ? parsed!.liveRefreshMinutes! : DEFAULT_SETTINGS.liveRefreshMinutes, kpiOrder, hiddenKpis };
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
const operationKindLabel = (kind: string) => ({ BUY: "Buy", SELL: "Sell", OPENING_BALANCE: "Opening balance", TRANSFER_IN: "Transfer in", TRANSFER_OUT: "Transfer out", ADJUSTMENT: "Adjustment", DIVIDEND: "Dividend", FEE: "Fee" }[kind] || kind);
type DemoData = { summary: PortfolioSummary; quotes: QuotesSummary; liveQuotes: LiveQuotesSummary; performance: PerformanceSummary; workerHealth: WorkerHealth };
const DEMO_DATES = ["2026-01-05", "2026-02-02", "2026-03-02", "2026-04-01", "2026-05-04", "2026-06-01", "2026-07-01", "2026-08-03", "2026-09-01", "2026-10-01"];
const demoSeries = (values: number[]) => DEMO_DATES.map((date, index) => ({ observed_at: `${date}T16:00:00Z`, price_eur: String(values[index]) }));
const DEMO_DATA: DemoData = {
  summary: {
    valuation_status: "available",
    kpis: { open_cost_eur: "118450.00", market_value_eur: "126870.00", realized_pnl_eur: "2840.00", unrealized_pnl_eur: "8420.00" },
    positions: [
      { ticker: "MSFT", quantity: "42", open_cost_eur: "15200.00", average_cost_eur: "361.90", realized_pnl_eur: "0", market_value_eur: "18480.00", unrealized_pnl_eur: "3280.00", market_data_status: "available", last_observed_at: "2026-10-14T16:00:00Z", market_data_provider: "twelve-data", market_data_source_symbol: "MSFT", market_data_venue: "NASDAQ", market_data_fx_provider: null, accounts: [{ name: "Long-term", quantity: "42", open_cost_eur: "15200.00", realized_pnl_eur: "0" }] },
      { ticker: "VWCE", quantity: "185", open_cost_eur: "19800.00", average_cost_eur: "107.03", realized_pnl_eur: "0", market_value_eur: "22620.00", unrealized_pnl_eur: "2820.00", market_data_status: "available", last_observed_at: "2026-10-14T16:00:00Z", market_data_provider: "twelve-data", market_data_source_symbol: "VWCE.DE", market_data_venue: "XETRA", market_data_fx_provider: null, accounts: [{ name: "Long-term", quantity: "185", open_cost_eur: "19800.00", realized_pnl_eur: "0" }] },
      { ticker: "EQQQ", quantity: "76", open_cost_eur: "29750.00", average_cost_eur: "391.45", realized_pnl_eur: "0", market_value_eur: "33520.00", unrealized_pnl_eur: "3770.00", market_data_status: "available", last_observed_at: "2026-10-14T16:00:00Z", market_data_provider: "twelve-data", market_data_source_symbol: "EQQQ.L", market_data_venue: "LSE", market_data_fx_provider: null, accounts: [{ name: "Growth", quantity: "76", open_cost_eur: "29750.00", realized_pnl_eur: "0" }] },
      { ticker: "BTC-EUR", quantity: "0.28", open_cost_eur: "23800.00", average_cost_eur: "85000.00", realized_pnl_eur: "0", market_value_eur: "32250.00", unrealized_pnl_eur: "2550.00", market_data_status: "available", last_observed_at: "2026-10-14T16:00:00Z", market_data_provider: "twelve-data", market_data_source_symbol: "BTC/EUR", market_data_venue: "COINBASE", market_data_fx_provider: null, accounts: [{ name: "Digital", quantity: "0.28", open_cost_eur: "23800.00", realized_pnl_eur: "0" }] },
    ],
    allocations: [],
    account_allocations: [],
  },
  quotes: { days: 365, items: [
    { ticker: "MSFT", price_eur: "440.00", change_percent: "1.84", observed_at: "2026-10-14T16:00:00Z", provider: "twelve-data", points: demoSeries([382, 395, 401, 412, 420, 427, 431, 434, 438, 440]) },
    { ticker: "VWCE", price_eur: "122.27", change_percent: "0.62", observed_at: "2026-10-14T16:00:00Z", provider: "twelve-data", points: demoSeries([106, 108, 110, 112, 114, 116, 117, 119, 121, 122.27]) },
    { ticker: "EQQQ", price_eur: "441.05", change_percent: "1.12", observed_at: "2026-10-14T16:00:00Z", provider: "twelve-data", points: demoSeries([388, 395, 401, 410, 414, 420, 427, 431, 437, 441.05]) },
    { ticker: "BTC-EUR", price_eur: "115178.57", change_percent: "2.41", observed_at: "2026-10-14T16:00:00Z", provider: "twelve-data", points: demoSeries([82000, 86000, 91000, 88000, 96000, 101000, 98000, 108000, 112000, 115178.57]) },
  ] },
  liveQuotes: { status: "fresh", credits_used: 4, retry_after: null, statuses: {}, items: [
    { ticker: "MSFT", price: "440.00", price_eur: "440.00", currency: "EUR", change_percent: "1.84", observed_at: "2026-10-14T16:05:00Z", provider: "twelve-data", status: "fresh" },
    { ticker: "VWCE", price: "122.27", price_eur: "122.27", currency: "EUR", change_percent: "0.62", observed_at: "2026-10-14T16:05:00Z", provider: "twelve-data", status: "fresh" },
    { ticker: "EQQQ", price: "441.05", price_eur: "441.05", currency: "EUR", change_percent: "1.12", observed_at: "2026-10-14T16:05:00Z", provider: "twelve-data", status: "fresh" },
    { ticker: "BTC-EUR", price: "115178.57", price_eur: "115178.57", currency: "EUR", change_percent: "2.41", observed_at: "2026-10-14T16:05:00Z", provider: "twelve-data", status: "fresh" },
  ] },
  performance: { methodology: "TWR", total_return: "0.146", points: DEMO_DATES.map((date, index) => ({ date, value_eur: String([102000, 105400, 108900, 110200, 114800, 117100, 119900, 121600, 124200, 126870][index]), external_flow_eur: "0", cumulative_return: String([0, 0.033, 0.067, 0.080, 0.125, 0.148, 0.175, 0.192, 0.218, 0.244][index]) })), benchmarks: [{ name: "MSCI World", ticker: "URTH", quote_currency: "EUR", methodology: "price_return", points: DEMO_DATES.map((date, index) => ({ date, return: String([0, 0.018, 0.031, 0.044, 0.069, 0.083, 0.104, 0.117, 0.132, 0.151][index]) })) }] },
  workerHealth: { status: "ok", provider: "twelve-data", updated_at: "2026-10-14T16:05:00Z" },
};

export function App() {
  const demoMode = new URLSearchParams(window.location.search).get("demo") === "1";
  const [authenticated, setAuthenticated] = useState(false);
  const [page, setPage] = useState<"dashboard" | "operations" | "settings">("dashboard");
  const [settings, setSettings] = useState<UserSettings>(() => readUserSettings());
  const updateSettings = (next: UserSettings) => { setSettings(next); writeUserSettings(next); };
  useEffect(() => { if (demoMode) return; void api.authMode().then(({ bypass }) => { if (bypass) setAuthenticated(true); }).catch(() => undefined); }, [demoMode]);
  if (demoMode) return <MantineProvider defaultColorScheme="dark"><DemoShell /></MantineProvider>;
  if (!authenticated) return <MantineProvider defaultColorScheme="dark"><Login onAuthenticated={() => setAuthenticated(true)} /></MantineProvider>;
  return <MantineProvider defaultColorScheme="dark"><AppShell header={{ height: { base: 112, sm: 64 } }} padding="md" className="investix-shell">
    <AppShell.Header px="md" py="sm" className="topbar"><Group justify="space-between" className="topbar-content"><Group gap="xs"><Title order={1} size="h3">Investix</Title><Badge color="cyan" variant="light">v{packageJson.version}</Badge></Group><Group gap="xs" className="topbar-actions"><Button variant={page === "dashboard" ? "light" : "subtle"} size="xs" onClick={() => setPage("dashboard")}>Dashboard</Button><Button variant={page === "operations" ? "light" : "subtle"} size="xs" onClick={() => setPage("operations")}>Register</Button><Button variant={page === "settings" ? "light" : "subtle"} size="xs" onClick={() => setPage("settings")}>Settings</Button></Group></Group></AppShell.Header>
    <AppShell.Main>{page === "dashboard" ? <Dashboard settings={settings} onOpenRegistry={() => setPage("operations")} /> : page === "operations" ? <Operations /> : <SettingsPage settings={settings} onChange={updateSettings} />}</AppShell.Main>
    <footer className="app-footer">Made by umbex · © 2026 · Market data is provided as-is; umbex is not responsible for inaccurate, delayed, or incomplete data.</footer>
  </AppShell></MantineProvider>;
}

function SettingsPage({ settings, onChange }: { settings: UserSettings; onChange: (settings: UserSettings) => void }) {
  const [summary, setSummary] = useState<PortfolioSummary>();
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth>({ status: "unknown" });
  const [catalog, setCatalog] = useState<InstrumentCatalogItem[]>([]);
  const [benchmarks, setBenchmarks] = useState<BenchmarkConfig[]>([]);
  const [watchQuery, setWatchQuery] = useState("");
  const [watchLookup, setWatchLookup] = useState<InstrumentLookupResult[]>([]);
  const [selectedWatch, setSelectedWatch] = useState<string | null>(null);
  const [catalogMessage, setCatalogMessage] = useState("");
  const loadSettingsData = () => Promise.all([api.portfolio(), api.workerHealth(), api.instrumentCatalog(), api.benchmarks()]).then(([nextSummary, nextWorkerHealth, nextCatalog, nextBenchmarks]) => { setSummary(nextSummary); setWorkerHealth(nextWorkerHealth); setCatalog(nextCatalog); setBenchmarks(nextBenchmarks); }).catch(() => setCatalogMessage("Instrument catalog unavailable."));
  useEffect(() => { void loadSettingsData(); }, []);
  const positions = summary?.positions ?? [];
  const orderedKpis = settings.kpiOrder.filter((key) => DEFAULT_KPI_ORDER.includes(key));
  const toggleKpi = (key: KpiKey, visible: boolean) => onChange({ ...settings, hiddenKpis: visible ? settings.hiddenKpis.filter((item) => item !== key) : [...settings.hiddenKpis, key] });
  const moveKpi = (index: number, offset: -1 | 1) => { const nextIndex = index + offset; if (nextIndex < 0 || nextIndex >= orderedKpis.length) return; const nextOrder = [...orderedKpis]; [nextOrder[index], nextOrder[nextIndex]] = [nextOrder[nextIndex], nextOrder[index]]; onChange({ ...settings, kpiOrder: nextOrder }); };
  const verifyWatch = async () => { if (!watchQuery.trim()) return; setCatalogMessage(""); try { const result = await api.lookupInstrument(watchQuery.trim()); setWatchLookup(result.items); setSelectedWatch(result.items.length ? watchOptionValue(result.items[0]) : null); if (!result.items.length) setCatalogMessage(result.status === "temporarily_unavailable" ? "Provider temporarily unavailable." : "No provider listing found."); } catch { setWatchLookup([]); setSelectedWatch(null); setCatalogMessage("Provider verification failed."); } };
  const watchOptionValue = (item: InstrumentLookupResult) => `${item.symbol}|${item.exchange}|${item.currency}`;
  const saveWatch = async () => { const item = watchLookup.find((candidate) => watchOptionValue(candidate) === selectedWatch); if (!item) return; try { await api.setWatchInstrument(item.symbol, { quote_symbol: item.symbol, quote_venue: item.exchange, quote_currency: item.currency, watch: true }); setWatchQuery(""); setWatchLookup([]); setSelectedWatch(null); await loadSettingsData(); } catch (reason) { setCatalogMessage(reason instanceof Error ? reason.message : "Unable to save watch instrument."); } };
  const removeWatch = async (item: InstrumentCatalogItem) => { if (!item.quote_symbol || !item.quote_venue || !item.quote_currency) return; await api.setWatchInstrument(item.ticker, { quote_symbol: item.quote_symbol, quote_venue: item.quote_venue, quote_currency: item.quote_currency, watch: false }); await loadSettingsData(); };
  const activateBenchmark = async (item: InstrumentCatalogItem) => { if (!item.quote_symbol || !item.quote_venue || !item.quote_currency) return; await api.configureBenchmark(item.ticker, { name: item.ticker, ticker: item.ticker, quote_symbol: item.quote_symbol, quote_venue: item.quote_venue, quote_currency: item.quote_currency, methodology: "price_return", active: true }); await loadSettingsData(); };
  const activeBenchmark = benchmarks.find((item) => item.active)?.ticker ?? null;
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Local preferences</Text><Title order={2}>Settings</Title></div><Card withBorder><Title order={3}>Dashboard</Title><Text size="sm" c="dimmed" mt="xs">These preferences apply immediately and do not require a service restart.</Text><SimpleGrid cols={{ base: 1, sm: 2 }} mt="md"><Select label="Default chart range" value={settings.chartRange} onChange={(value) => onChange({ ...settings, chartRange: value || DEFAULT_SETTINGS.chartRange })} data={RANGE_OPTIONS} /><Select label="Default quotes history" value={settings.quoteRange} onChange={(value) => onChange({ ...settings, quoteRange: value || DEFAULT_SETTINGS.quoteRange })} data={RANGE_OPTIONS} /><Select label="Quotes refresh" value={String(settings.liveRefreshMinutes)} onChange={(value) => onChange({ ...settings, liveRefreshMinutes: Number(value || DEFAULT_SETTINGS.liveRefreshMinutes) })} data={LIVE_REFRESH_OPTIONS} /></SimpleGrid></Card><Card withBorder><Title order={3}>Overview KPIs</Title><Text size="sm" c="dimmed" mt="xs">Choose which KPIs to show and their order. Changes apply immediately.</Text><Stack mt="md" gap="xs">{orderedKpis.map((key, index) => { const definition = KPI_DEFINITIONS.find((item) => item.key === key)!; const visible = !settings.hiddenKpis.includes(key); return <Group key={key} justify="space-between" wrap="nowrap"><Switch label={definition.label} checked={visible} onChange={(event) => toggleKpi(key, event.currentTarget.checked)} /><Group gap={"xs"} wrap="nowrap"><Button variant="subtle" size="compact-xs" aria-label={`Move ${definition.label} up`} disabled={index === 0} onClick={() => moveKpi(index, -1)}>↑</Button><Button variant="subtle" size="compact-xs" aria-label={`Move ${definition.label} down`} disabled={index === orderedKpis.length - 1} onClick={() => moveKpi(index, 1)}>↓</Button></Group></Group>; })}</Stack></Card><Card withBorder><Group justify="space-between"><Title order={3}>Watchlist</Title><Text size="sm" c="dimmed">{catalog.filter((item) => item.watch).length}/5</Text></Group><Text size="sm" c="dimmed" mt="xs">Verify a provider listing, then add it without creating a portfolio position.</Text><Group align="end" mt="md"><TextInput label="Ticker or symbol" value={watchQuery} onChange={(event) => setWatchQuery(event.currentTarget.value)} /><Button variant="light" onClick={() => void verifyWatch()}>Search</Button></Group>{watchLookup.length > 0 && <Group align="end" mt="sm"><Select label="Verified provider listing" value={selectedWatch} onChange={setSelectedWatch} data={watchLookup.map((item) => ({ value: watchOptionValue(item), label: `${item.symbol} · ${item.exchange} · ${item.currency} · ${item.name}` }))} /><Button onClick={() => void saveWatch()} disabled={!selectedWatch || catalog.filter((item) => item.watch).length >= 5}>Add watch</Button></Group>}{catalogMessage && <Text size="xs" c="yellow" mt="xs">{catalogMessage}</Text>}<Stack mt="md" gap="xs">{catalog.filter((item) => item.watch).map((item) => <Group key={item.ticker} justify="space-between"><Text>{item.ticker}</Text><Button size="xs" variant="subtle" onClick={() => void removeWatch(item)}>Remove</Button></Group>)}</Stack></Card><Card withBorder><Title order={3}>Benchmarks</Title><Text size="sm" c="dimmed" mt="xs">Choose one verified portfolio or watchlist instrument for the return comparison chart.</Text><Select mt="md" label="Active benchmark" aria-label="Active benchmark" value={activeBenchmark} onChange={(value) => { const item = catalog.find((candidate) => candidate.ticker === value); if (item) void activateBenchmark(item); }} data={catalog.filter((item) => item.quote_symbol && item.quote_venue && item.quote_currency).map((item) => ({ value: item.ticker, label: item.ticker }))} clearable /><Stack mt="md" gap="xs">{catalog.filter((item) => item.quote_symbol && item.quote_venue && item.quote_currency).map((item) => <Group key={item.ticker} justify="space-between"><Text size="sm">{item.ticker}{item.watch ? " · Watch" : item.has_position ? " · Portfolio" : ""}</Text>{activeBenchmark !== item.ticker && <Button size="xs" variant="subtle" onClick={() => void activateBenchmark(item)}>Use as benchmark</Button>}</Group>)}</Stack></Card><Card withBorder><Title order={3}>Technical configuration</Title><Text size="sm" c="dimmed" mt="xs">Provider, API key, quota limits, database, and worker remain server-side configuration and are not exposed in the UI.</Text></Card><Card withBorder><Title order={3}>Data status</Title><Stack mt="md" gap="sm"><Status label="Ledger" value={String(positions.length) + " instruments"} /><Status label="Price provider" value={summary?.valuation_status === "available" ? "Persisted observations" : "No observation"} /><Status label="EOD worker" value={workerHealth.status === "ok" ? `Active${workerHealth.provider === "disabled" ? " · provider disabled" : ""}` : workerHealth.status === "not_configured" ? "Not configured" : "Not verified"} /><Status label="Latest quote" value={latestObservation(positions)} /></Stack></Card></Stack>;
}

function DemoShell() {
  return <AppShell header={{ height: { base: 112, sm: 64 } }} padding="md" className="investix-shell">
    <AppShell.Header px="md" py="sm" className="topbar"><Group justify="space-between" className="topbar-content"><Group gap="xs"><Title order={1} size="h3">Investix</Title><Badge color="cyan" variant="light">Demo data</Badge></Group><Badge variant="outline" color="gray">Synthetic preview</Badge></Group></AppShell.Header>
    <AppShell.Main><Dashboard settings={DEFAULT_SETTINGS} onOpenRegistry={() => undefined} demoData={DEMO_DATA} /></AppShell.Main>
    <footer className="app-footer">Made by umbex · © 2026 · Synthetic values for demonstration only.</footer>
  </AppShell>;
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { await api.login(String(form.get("username")), String(form.get("password"))); onAuthenticated(); } catch { setError("Invalid credentials or API unavailable"); }
  }
  return <main className="login"><Card withBorder radius="md" p="xl"><Title order={1}>Investix</Title><Text c="dimmed" mb="lg">Private access</Text><form onSubmit={submit}><Stack><TextInput name="username" label="Username" required autoComplete="username" /><TextInput name="password" type="password" label="Password" required autoComplete="current-password" />{error && <Text c="red" size="sm">{error}</Text>}<Button type="submit">Sign in</Button></Stack></form></Card></main>;
}

function Dashboard({ settings, onOpenRegistry, demoData }: { settings: UserSettings; onOpenRegistry: () => void; demoData?: DemoData }) {
  const [summary, setSummary] = useState<PortfolioSummary | undefined>(demoData?.summary);
  const [quotePositions, setQuotePositions] = useState<PortfolioSummary["positions"]>(demoData?.summary.positions ?? []);
  const [performance, setPerformance] = useState<PerformanceSummary | undefined>(demoData?.performance);
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth>(demoData?.workerHealth ?? { status: "unknown" });
  const [quotes, setQuotes] = useState<QuotesSummary | undefined>(demoData?.quotes);
  const [liveQuotes, setLiveQuotes] = useState<LiveQuotesSummary | undefined>(demoData?.liveQuotes);
  const [quoteRange, setQuoteRange] = useState(settings.quoteRange);
  const [range, setRange] = useState(settings.chartRange);
  const [ticker, setTicker] = useState("");
  const [account, setAccount] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const load = async (filter = ticker) => { if (demoData) return; setError(""); try { const nextSummary = await api.portfolio(filter || undefined, account || undefined); let nextQuotePositions = nextSummary.positions; if (filter) { try { nextQuotePositions = (await api.portfolio(undefined, account || undefined)).positions; } catch { /* keep filtered positions if the unfiltered lookup fails */ } } try { setPerformance(await api.performance(filter || undefined, dateFrom || undefined, dateTo || undefined)); } catch { setPerformance(undefined); } try { setWorkerHealth(await api.workerHealth()); } catch { setWorkerHealth({ status: "unknown" }); } try { setQuotes(await api.quotes(rangeDays(quoteRange))); } catch { setQuotes(undefined); } setSummary(nextSummary); setQuotePositions(nextQuotePositions); } catch (reason) { setError(reason instanceof Error ? reason.message : "Data unavailable"); } };
  useEffect(() => { if (!demoData) void load(""); }, [demoData]);
  const changeQuoteRange = (value: string | null) => { const nextRange = value || "3M"; setQuoteRange(nextRange); if (!demoData) void api.quotes(rangeDays(nextRange)).then(setQuotes).catch(() => setQuotes(undefined)); };
  const positions = summary?.positions ?? [];
  const todayPnlTotal = useMemo(() => {
    let total = 0;
    let available = 0;
    for (const item of quotes?.items ?? []) {
      const live = (liveQuotes?.items ?? []).find((candidate) => candidate.ticker === (item.quote_symbol || item.ticker));
      const position = quotePositions.find((candidate) => candidate.ticker === item.ticker);
      const pnl = todayPnlAmount(position?.quantity, live?.price_eur ?? item.price_eur, live?.change_percent ?? item.change_percent);
      if (pnl != null) { total += pnl; available += 1; }
    }
    return available ? total : null;
  }, [quotes, liveQuotes, quotePositions]);
  const todayPnlDisplay = todayPnlTotal == null ? "N/A" : `${todayPnlTotal >= 0 ? "+" : ""}${kpiEuro.format(todayPnlTotal / 1000)}K€`;
  const kpiCards = {
    marketValue: <Metric label="Portfolio value" value={kpiAmount(summary?.kpis.market_value_eur)} note={summary?.valuation_status === "available" ? "Latest persisted observation" : "Quotes missing"} />,
    todayPnl: <Metric label="Today P&L" value={todayPnlDisplay} note="Today's change" positive={todayPnlTotal != null && todayPnlTotal >= 0} negative={todayPnlTotal != null && todayPnlTotal < 0} />,
    openCost: <Metric label="Open capital" value={kpiAmount(summary?.kpis.open_cost_eur)} note="Cost reconstructed from ledger" />,
    realizedPnl: <Metric label="Realized P&L" value={kpiAmount(summary?.kpis.realized_pnl_eur)} note="Recorded sales" positive={Number(summary?.kpis.realized_pnl_eur) > 0} />,
    unrealizedPnl: <Metric label="Unrealized P&L" value={kpiAmount(summary?.kpis.unrealized_pnl_eur)} note="Available with EOD quotes" positive={Number(summary?.kpis.unrealized_pnl_eur) > 0} />,
    twr: <Metric label="TWR return" value={performance?.total_return == null ? "N/A" : new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 2 }).format(Number(performance.total_return))} note="Time-weighted return" positive={Number(performance?.total_return) > 0} />,
  };
  const visibleKpis = settings.kpiOrder.filter((key) => !settings.hiddenKpis.includes(key)).map((key) => <Fragment key={key}>{kpiCards[key]}</Fragment>);
  const liveSessionId = useRef(`tab-${Math.random().toString(36).slice(2)}`);
  useEffect(() => {
    if (demoData) return;
    const symbols = (quotes?.items ?? []).filter((item) => marketStatus(item.quote_venue).open).map((item) => item.quote_symbol || item.ticker);
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
  }, [demoData, quotes?.items?.map((item) => `${item.ticker}:${item.quote_symbol || ""}`).join(","), settings.liveRefreshMinutes]);
  return <Stack gap="lg" className="dashboard">
    <Group justify="flex-start" className="dashboard-title">{summary && summary.valuation_status !== "available" && <Badge color="yellow">Quotes missing</Badge>}</Group>
    <Group className="filter-bar" align="end"><Select label="Ticker" placeholder="All" clearable value={ticker || null} onChange={(value) => setTicker(value || "")} data={positions.map((position) => position.ticker)} /><Select label="Account" placeholder="All" clearable value={account || null} onChange={(value) => setAccount(value || "")} data={Array.from(new Set(positions.flatMap((position) => position.accounts.map((item) => item.name)))).sort()} />{SHOW_OVERVIEW_DATE_FILTER && <><TextInput label="From" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.currentTarget.value)} /><TextInput label="To" type="date" value={dateTo} onChange={(event) => setDateTo(event.currentTarget.value)} /></>}<Button onClick={() => void load()}>Apply</Button><Button variant="subtle" onClick={() => { setTicker(""); setAccount(""); setDateFrom(""); setDateTo(""); void load(""); }}>Reset</Button></Group>
    {error && <Card withBorder><Text c="red">{error}</Text><Button mt="sm" size="xs" onClick={() => void load()}>Retry</Button></Card>}
    {!summary && !error ? <Group justify="center" py="xl"><Loader aria-label="Loading portfolio" /></Group> : <><SimpleGrid cols={{ base: 2, md: 5 }} spacing="md">{visibleKpis}</SimpleGrid>
      <Card withBorder radius="md"><Group justify="space-between" align="center"><Title order={3}>Quotes</Title><Select aria-label="Quotes history" size="xs" value={quoteRange} onChange={changeQuoteRange} data={RANGE_OPTIONS} /></Group><QuotesTable quotes={quotes} liveQuotes={liveQuotes} positions={quotePositions} /></Card>
      <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Positions</Title><Button variant="subtle" size="xs" onClick={onOpenRegistry}>Operations register</Button></Group><PositionTable positions={positions} totalOpenCost={summary!.kpis.open_cost_eur} totalMarketValue={summary!.kpis.market_value_eur} /></Card>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Value over time</Title><Group gap="xs"><Select aria-label="Chart range" size="xs" value={range} onChange={(value) => setRange(value || "All")} data={RANGE_OPTIONS} /><Badge variant="outline">EUR</Badge></Group></Group><PortfolioChart performance={performance} range={range} /><Text size="xs" c="dimmed">{performance?.methodology || "No historical series available: valid historical observations are required."}</Text></Card>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Return vs benchmark</Title><Group gap="xs"><Select aria-label="Benchmark range" size="xs" value={range} onChange={(value) => setRange(value || "All")} data={RANGE_OPTIONS} /><Badge variant="outline">Common base 0%</Badge></Group></Group><BenchmarkChart performance={performance} range={range} /><Text size="xs" c="dimmed">Price-return benchmarks exclude dividends; the legend indicates comparability.</Text></Card>
      </>}
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
  if (!positions.length) return <Text c="dimmed" mt="md">No positions match the selected filter.</Text>;
  return <Table.ScrollContainer minWidth={680}><Table mt="md" striped highlightOnHover><Table.Thead><Table.Tr><SortableHeader label="Instrument" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Quantity" sort={sort} sortKey="quantity" onSort={onSort} /><SortableHeader label="Cost EUR" sort={sort} sortKey="cost" onSort={onSort} /><SortableHeader label="Value" sort={sort} sortKey="value" onSort={onSort} /><SortableHeader label="P&L" sort={sort} sortKey="pnl" onSort={onSort} /><SortableHeader label="Status" sort={sort} sortKey="status" onSort={onSort} /></Table.Tr></Table.Thead><Table.Tbody>{sortedPositions.map((position) => <Table.Tr key={position.ticker}><Table.Td><Text fw={600}>{position.ticker}</Text><Text size="xs" c="dimmed">{position.accounts.map((item) => item.name).join(" · ")}</Text></Table.Td><Table.Td>{Number(position.quantity).toLocaleString("it-IT")}</Table.Td><Table.Td><Text>{amount(position.open_cost_eur)}</Text><Text size="xs" c="dimmed">{percent(totalOpenCost && Number(totalOpenCost) ? String(Number(position.open_cost_eur) / Number(totalOpenCost)) : null)}</Text></Table.Td><Table.Td><Text>{amount(position.market_value_eur)}</Text><Text size="xs" c="dimmed">{percent(position.market_value_eur && totalMarketValue ? String(Number(position.market_value_eur) / Number(totalMarketValue)) : null)}</Text></Table.Td><Table.Td>{amount(position.unrealized_pnl_eur)}</Table.Td><Table.Td><Tooltip label={marketStatusLabel(position)}><span className={`market-status-icon ${position.market_data_status}`} role="img" aria-label={position.market_data_status === "available" ? "Quote available" : "Quote missing"}>{position.market_data_status === "available" ? "✓" : "!"}</span></Tooltip></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>;
}

function marketStatusLabel(position: PortfolioSummary["positions"][number]): string {
  if (position.market_data_status === "missing") return "No persisted quote for this instrument";
  return `Quote available${position.market_data_provider ? ` · ${position.market_data_provider}` : ""}`;
}

function latestObservation(positions: PortfolioSummary["positions"]): string {
  const values = positions.map((position) => position.last_observed_at).filter((value): value is string => value != null).sort();
  const latest = values[values.length - 1];
  return latest ? new Date(latest).toLocaleString("it-IT") : "Not available";
}

function QuotesTable({ quotes, liveQuotes, positions }: { quotes?: QuotesSummary; liveQuotes?: LiveQuotesSummary; positions: PortfolioSummary["positions"] }) {
  const retryLabel = liveQuotes?.retry_after ? ` dopo le ${new Date(liveQuotes.retry_after * 1000).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}` : "";
  const [sort, setSort] = useState<SortState | null>(null);
  const liveFor = (item: QuotesSummary["items"][number]) => (liveQuotes?.items ?? []).find((candidate) => candidate.ticker === (item.quote_symbol || item.ticker));
  const items = useMemo(() => sortedBy(quotes?.items ?? [], sort, (item, key) => { const live = liveFor(item); return ({ ticker: item.ticker, price: item.price_eur, change: item.change_percent, pnl: todayPnlAmount(positions.find((candidate) => candidate.ticker === item.ticker)?.quantity, live?.price_eur ?? item.price_eur, live?.change_percent ?? item.change_percent) }[key as "ticker" | "price" | "change" | "pnl"]); }), [quotes?.items, sort, positions, liveQuotes]);
  const onSort = (key: string) => setSort((current) => nextSort(current, key, ["price", "change", "pnl"].includes(key) ? "desc" : "asc"));
  if (!quotes?.items?.length) return <Text c="dimmed" mt="md">Quotes are not available.</Text>;
  return <><Table.ScrollContainer minWidth={760}><Table mt="md" striped><Table.Thead><Table.Tr><SortableHeader label="Ticker" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Last" sort={sort} sortKey="price" onSort={onSort} /><SortableHeader label="Change" sort={sort} sortKey="change" onSort={onSort} /><SortableHeader label="Today P&L" sort={sort} sortKey="pnl" onSort={onSort} /><Table.Th>Trend</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => { const live = liveFor(item); const livePrice = live?.price_eur ?? (live ? `${live.price} ${live.currency}` : null); const currentPrice = live?.price_eur ?? item.price_eur; const position = positions.find((candidate) => candidate.ticker === item.ticker); const quantity = position?.quantity; const changePercent = live?.change_percent ?? item.change_percent; const todayPnl = todayPnlAmount(quantity, currentPrice, changePercent); const market = marketStatus(item.quote_venue || position?.market_data_venue); return <Table.Tr key={item.ticker}><Table.Td><Group gap="xs" wrap="nowrap"><Text fw={600}>{item.ticker}</Text>{item.watch && !position && <Badge size="xs" variant="light">Watch</Badge>}<Tooltip label={market.label}><span className={`market-open-dot ${market.open ? "open" : "closed"}`} role="img" aria-label={market.label} /></Tooltip></Group><Text size="xs" c="dimmed">{live ? `Live · ${new Date(live.observed_at).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}` : item.observed_at ? new Date(item.observed_at).toLocaleString("it-IT") : "No persisted quote"}</Text></Table.Td><Table.Td>{livePrice == null ? amount(item.price_eur) : typeof livePrice === "string" && livePrice.includes(" ") ? livePrice : amount(livePrice)}</Table.Td><Table.Td c={changePercent == null ? "dimmed" : Number(changePercent) >= 0 ? "teal" : "red"}>{changePercent == null ? "N/A" : `${Number(changePercent).toLocaleString("it-IT", { maximumFractionDigits: 2 })}%`}</Table.Td><Table.Td c={todayPnl == null ? "dimmed" : todayPnl >= 0 ? "teal" : "red"}>{todayPnl == null ? "N/A" : amount(String(todayPnl))}</Table.Td><Table.Td><Sparkline points={item.points.map((point) => Number(point.price_eur))} label={`Trend ${item.ticker}`} /></Table.Td></Table.Tr>; })}</Table.Tbody></Table></Table.ScrollContainer>{liveQuotes?.status === "quota_exhausted" && <Text size="xs" c="yellow" mt="xs">Provider limit reached: wait for the next available window{retryLabel}.</Text>}{liveQuotes?.status === "pending" && <Text size="xs" c="dimmed" mt="xs">Live update queued.</Text>}</>;
}

function marketStatus(venue: string | null | undefined): { open: boolean; label: string } {
  const normalized = (venue || "").toUpperCase();
  if (["BINANCE", "COINBASE", "COINBASE PRO", "KRAKEN", "BITSTAMP"].includes(normalized)) return { open: true, label: `Market open${venue ? ` · ${venue}` : ""}` };
  const timezone = normalized === "NASDAQ" || normalized === "NYSE" ? "America/New_York" : "Europe/Rome";
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: timezone, weekday: "short", hour: "numeric", minute: "numeric", hour12: false }).formatToParts(new Date());
  const weekday = parts.find((part) => part.type === "weekday")?.value;
  const hour = Number(parts.find((part) => part.type === "hour")?.value);
  const minute = Number(parts.find((part) => part.type === "minute")?.value);
  const current = hour * 60 + minute;
  const start = normalized === "NASDAQ" || normalized === "NYSE" ? 570 : 540;
  const end = normalized === "NASDAQ" || normalized === "NYSE" ? 960 : 1050;
  const open = !["Sat", "Sun"].includes(weekday || "") && current >= start && current < end;
  return { open, label: `Market ${open ? "open" : "closed"}${venue ? ` · ${venue}` : ""}` };
}

function todayPnlAmount(quantity: string | undefined, price: string | number | null, changePercent: string | null): number | null {
  if (!quantity || price == null || changePercent == null) return null;
  const current = typeof price === "number" ? price : numericValue(price);
  const change = Number(changePercent) / 100;
  if (!Number.isFinite(current) || !Number.isFinite(change) || change <= -1) return null;
  return numericValue(quantity) * (current - current / (1 + change));
}

function Sparkline({ points, label }: { points: number[]; label: string }) {
  if (points.length < 2) return <Text size="xs" c="dimmed">N/A</Text>;
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
  const load = async () => { try { setItems((await api.operations()).items); } catch (reason) { setError(reason instanceof Error ? reason.message : "Register unavailable"); } };
  const startEdit = (item: Operation) => { setEditing(item); setReason(""); setQuantity(item.quantity); setPrice(item.unit_price_eur); setTradeDate(item.trade_date); setNote(item.note || ""); setError(""); };
  const revise = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (!editing || !reason.trim()) return; try { await api.reviseOperation(editing.id, { reason: reason.trim(), quantity, unit_price_eur: price, trade_date: tradeDate, note: note || null }); setEditing(null); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to correct the operation"); } };
  const cancel = async (item: Operation) => { if (!window.confirm(`Cancel operation ${item.ticker} dated ${item.trade_date}?`)) return; const cancellationReason = window.prompt("Cancellation reason"); if (!cancellationReason?.trim()) return; try { await api.cancelOperation(item.id, cancellationReason.trim()); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to cancel the operation"); } };
  const lookup = async () => { if (!ticker.trim()) return; setLookupStatus("Searching..."); setLookupItems([]); setSelectedLookup(null); try { const result = await api.lookupInstrument(ticker.trim()); setLookupItems(result.items); setLookupStatus(result.status === "ok" ? (result.items.length ? "Select the correct listing" : "No listing found") : (result.message || "Provider unavailable")); } catch (reason) { setLookupStatus(reason instanceof Error ? reason.message : "Lookup unavailable"); } };
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = new FormData(event.currentTarget);
    if (lookupItems.length && !selectedLookup) { setError("Select the provider listing before recording the operation"); return; }
    const selected = lookupItems.find((item) => item.symbol === selectedLookup);
    try { await api.createOperation({ account_name: values.get("account"), ticker: ticker.trim().toUpperCase(), quote_symbol: selected?.symbol ?? null, quote_venue: selected?.exchange ?? null, quote_currency: selected?.currency ?? null, kind: values.get("kind"), quantity: parseNumericInput(values.get("quantity")), unit_price_eur: parseNumericInput(values.get("price")), original_unit_price: values.get("original_price") ? parseNumericInput(values.get("original_price")) : null, original_currency: values.get("original_currency") || null, trade_date: values.get("date"), settlement_date: values.get("settlement_date") || null, note: values.get("note") || null, is_approximate: values.get("is_approximate") === "on", source_order: 0 }); event.currentTarget.reset(); setTicker(""); setLookupItems([]); setSelectedLookup(null); setLookupStatus(""); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to record the operation"); }
  }
  const sortedItems = useMemo(() => sortedBy(items, sort, (item, key) => ({ date: item.trade_date, account: item.account_name, ticker: item.ticker, kind: item.kind, quantity: item.quantity, price: item.unit_price_eur, context: item.note || (item.is_approximate ? "Approximate" : "") }[key as "date" | "account" | "ticker" | "kind" | "quantity" | "price" | "context"])), [items, sort]);
  const onSort = (key: string) => setSort((current) => nextSort(current, key, ["quantity", "price"].includes(key) ? "desc" : "asc"));
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Audited ledger</Text><Title order={2}>Operations register</Title></div><Card withBorder><form onSubmit={submit}><SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}><TextInput required name="account" label="Account" /><Group align="end" gap="xs"><TextInput required name="ticker" label="Ticker" value={ticker} onChange={(event) => { setTicker(event.currentTarget.value); setLookupItems([]); setSelectedLookup(null); setLookupStatus(""); }} /><Button type="button" variant="light" onClick={() => void lookup()}>Search</Button></Group>{lookupItems.length > 0 && <Select required label="Provider listing" placeholder="Select the instrument" value={selectedLookup} onChange={setSelectedLookup} data={lookupItems.map((item) => ({ value: item.symbol, label: `${item.symbol} · ${item.exchange} · ${item.currency} · ${item.name}` }))} />}{lookupStatus && <Text size="xs" c="dimmed">{lookupStatus}</Text>}<Select required name="kind" label="Type" data={[{ value: "BUY", label: "Buy" }, { value: "SELL", label: "Sell" }, { value: "OPENING_BALANCE", label: "Opening balance" }, { value: "TRANSFER_IN", label: "Transfer in" }, { value: "TRANSFER_OUT", label: "Transfer out" }, { value: "ADJUSTMENT", label: "Adjustment" }, { value: "DIVIDEND", label: "Dividend" }, { value: "FEE", label: "Fee" }]} /><NumberInput required name="quantity" label="Quantity" decimalScale={6} /><NumberInput required name="price" label="Price EUR" min={0} decimalScale={4} /><TextInput name="original_price" label="Original price" /><TextInput name="original_currency" label="Original currency" maxLength={8} /><TextInput required name="date" type="date" label="Date" defaultValue={new Date().toISOString().slice(0, 10)} /><TextInput name="settlement_date" type="date" label="Settlement date" /><TextInput name="note" label="Note" /><label><input name="is_approximate" type="checkbox" /> Approximate value</label></SimpleGrid><Button mt="md" type="submit">Record operation</Button></form></Card>{error && <Text c="red">{error}</Text>}<Card withBorder><Table.ScrollContainer minWidth={900}><Table><Table.Thead><Table.Tr><SortableHeader label="Date" sort={sort} sortKey="date" onSort={onSort} /><SortableHeader label="Account" sort={sort} sortKey="account" onSort={onSort} /><SortableHeader label="Ticker" sort={sort} sortKey="ticker" onSort={onSort} /><SortableHeader label="Type" sort={sort} sortKey="kind" onSort={onSort} /><SortableHeader label="Quantity" sort={sort} sortKey="quantity" onSort={onSort} /><SortableHeader label="Price" sort={sort} sortKey="price" onSort={onSort} /><SortableHeader label="Context" sort={sort} sortKey="context" onSort={onSort} /><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{sortedItems.map((item) => <Table.Tr key={item.id}><Table.Td>{new Date(item.trade_date).toLocaleDateString("it-IT")}</Table.Td><Table.Td>{item.account_name}</Table.Td><Table.Td>{item.ticker}</Table.Td><Table.Td>{operationKindLabel(item.kind)}</Table.Td><Table.Td>{item.quantity}</Table.Td><Table.Td>{amount(item.unit_price_eur)}</Table.Td><Table.Td>{item.note || (item.is_approximate ? "Approximate" : "—")}</Table.Td><Table.Td><Group gap="xs" wrap="nowrap"><Button size="xs" variant="light" onClick={() => startEdit(item)}>Edit</Button><Button size="xs" variant="subtle" color="red" onClick={() => void cancel(item)}>Cancel</Button></Group></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card><Modal opened={editing !== null} onClose={() => setEditing(null)} title={editing ? `Correct ${editing.ticker}` : "Correct operation"}><form onSubmit={revise}><Stack><TextInput label="Reason" required value={reason} onChange={(event) => setReason(event.currentTarget.value)} /><NumberInput label="Quantity" required value={quantity} onChange={(value) => setQuantity(String(value))} min={0} decimalScale={6} /><NumberInput label="Price EUR" required value={price} onChange={(value) => setPrice(String(value))} min={0} decimalScale={4} /><TextInput label="Date" type="date" required value={tradeDate} onChange={(event) => setTradeDate(event.currentTarget.value)} /><TextInput label="Note" value={note} onChange={(event) => setNote(event.currentTarget.value)} /><Group justify="flex-end"><Button variant="subtle" onClick={() => setEditing(null)}>Close</Button><Button type="submit">Save correction</Button></Group></Stack></form></Modal></Stack>;
}

function Metric({ label, value, note, positive = false, negative = false }: { label: string; value: string; note: string; positive?: boolean; negative?: boolean }) { return <Card withBorder radius="md"><Text size="sm" c="dimmed">{label}</Text><Text className={`${positive ? "positive" : ""}${negative ? " negative" : ""} metric`}>{value}</Text><Text size="xs" c="dimmed">{note}</Text></Card>; }
function Status({ label, value }: { label: string; value: string }) { return <Group justify="space-between" wrap="nowrap"><Text size="sm">{label}</Text><Text size="sm" c="dimmed">{value}</Text></Group>; }
function PortfolioChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range);
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); chart.setOption(points.length ? { grid: { left: 48, right: 16, top: 18, bottom: 28 }, tooltip: { trigger: "axis", valueFormatter: (value: number) => euro.format(value) }, xAxis: { type: "category", data: points.map((point) => point.date), axisLabel: { color: chartText, formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) }, axisLine: { lineStyle: { color: chartText } } }, yAxis: { type: "value", axisLabel: { color: chartText, formatter: (value: number) => euro.format(value) }, axisLine: { lineStyle: { color: chartText } } }, series: [{ type: "line", data: points.map((point) => Number(point.value_eur)), smooth: true, showSymbol: false, areaStyle: { opacity: 0.16 }, lineStyle: { color: "#22d3ee" } }] } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "No historical series available", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points]);
  return <div className="chart" ref={element} role="img" aria-label="Portfolio value chart" />;
}

function BenchmarkChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range).filter((point) => point.cumulative_return != null);
  const benchmarks = (performance?.benchmarks ?? []).map((benchmark) => ({ ...benchmark, points: withinRange(benchmark.points, range) }));
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, components.LegendComponent, components.DataZoomComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); const dates = points.map((point) => point.date); const series = [{ name: "Portfolio TWR", type: "line", data: points.map((point) => Number(point.cumulative_return)), smooth: true, showSymbol: false, lineStyle: { color: "#22d3ee" } }, ...benchmarks.map((benchmark) => ({ name: `${benchmark.name} (${benchmark.methodology === "price_return" ? "price" : "total"})`, type: "line", data: dates.map((day) => Number(benchmark.points.find((point) => point.date === day)?.return ?? NaN)), smooth: true, showSymbol: false }))]; chart.setOption(points.length ? { grid: { left: 52, right: 18, top: 36, bottom: 42 }, legend: { top: 0, textStyle: { color: chartText } }, tooltip: { trigger: "axis", valueFormatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(value) }, dataZoom: [{ type: "inside" }], xAxis: { type: "category", data: dates, axisLabel: { color: chartText, formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) }, axisLine: { lineStyle: { color: chartText } } }, yAxis: { type: "value", axisLabel: { color: chartText, formatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 0 }).format(value) }, axisLine: { lineStyle: { color: chartText } } }, series } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "Benchmark or return data unavailable", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points, benchmarks]);
  return <div className="chart" ref={element} role="img" aria-label="Portfolio return vs benchmark chart" />;
}

function withinRange<T extends { date: string }>(points: T[], range: string): T[] {
  if (!points.length || range === "All") return points;
  const end = new Date(points.at(-1)!.date);
  const start = new Date(end);
  if (range === "YTD") start.setMonth(0, 1); else if (range === "1W") start.setDate(start.getDate() - 7); else start.setMonth(start.getMonth() - Number(range.replace("M", "").replace("Y", "")) * (range.endsWith("Y") ? 12 : 1));
  return points.filter((point) => new Date(point.date) >= start);
}
