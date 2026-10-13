import { AppShell, Badge, Button, Card, Group, Loader, MantineProvider, NumberInput, Select, SimpleGrid, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { FormEvent, useEffect, useRef, useState } from "react";

import { api, type Operation, type PerformanceSummary, type PortfolioSummary } from "./api";
import "./styles.css";

const euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 });
const amount = (value: string | null | undefined) => value == null ? "N/D" : euro.format(Number(value));

export function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [page, setPage] = useState<"dashboard" | "operations">("dashboard");
  if (!authenticated) return <MantineProvider defaultColorScheme="dark"><Login onAuthenticated={() => setAuthenticated(true)} /></MantineProvider>;
  return <MantineProvider defaultColorScheme="dark"><AppShell header={{ height: 64 }} padding="md" className="investix-shell">
    <AppShell.Header px="md" py="sm" className="topbar"><Group justify="space-between"><Group gap="xs"><Title order={1} size="h3">Investix</Title><Badge color="cyan" variant="light">Privato</Badge></Group><Group gap="xs"><Button variant={page === "dashboard" ? "light" : "subtle"} size="xs" onClick={() => setPage("dashboard")}>Panoramica</Button><Button variant={page === "operations" ? "light" : "subtle"} size="xs" onClick={() => setPage("operations")}>Registro</Button></Group></Group></AppShell.Header>
    <AppShell.Main>{page === "dashboard" ? <Dashboard onOpenRegistry={() => setPage("operations")} /> : <Operations />}</AppShell.Main>
  </AppShell></MantineProvider>;
}

function Login({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try { await api.login(String(form.get("username")), String(form.get("password"))); onAuthenticated(); } catch { setError("Credenziali non valide o API non disponibile"); }
  }
  return <main className="login"><Card withBorder radius="md" p="xl"><Title order={1}>Investix</Title><Text c="dimmed" mb="lg">Accesso privato</Text><form onSubmit={submit}><Stack><TextInput name="username" label="Utente" required autoComplete="username" /><TextInput name="password" type="password" label="Password" required autoComplete="current-password" />{error && <Text c="red" size="sm">{error}</Text>}<Button type="submit">Accedi</Button></Stack></form></Card></main>;
}

function Dashboard({ onOpenRegistry }: { onOpenRegistry: () => void }) {
  const [summary, setSummary] = useState<PortfolioSummary>();
  const [performance, setPerformance] = useState<PerformanceSummary>();
  const [range, setRange] = useState("Tutto");
  const [ticker, setTicker] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const load = async (filter = ticker) => { setError(""); try { setSummary(await api.portfolio(filter || undefined)); try { setPerformance(await api.performance(filter || undefined, dateFrom || undefined, dateTo || undefined)); } catch { setPerformance(undefined); } } catch (reason) { setError(reason instanceof Error ? reason.message : "Dati non disponibili"); } };
  useEffect(() => { void load(""); }, []);
  const positions = summary?.positions ?? [];
  return <Stack gap="lg" className="dashboard">
    <Group justify="space-between" align="end" className="dashboard-title"><div><Text c="dimmed">Portafoglio privato</Text><Title order={2}>Panoramica</Title></div><Badge color={summary?.valuation_status === "available" ? "teal" : "yellow"}>{summary?.valuation_status === "available" ? "Quotazioni disponibili" : "Quotazioni mancanti"}</Badge></Group>
    <Group className="filter-bar" align="end"><TextInput label="Filtra per ticker" placeholder="es. VWCE" value={ticker} onChange={(event) => setTicker(event.currentTarget.value.toUpperCase())} /><TextInput label="Da" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.currentTarget.value)} /><TextInput label="A" type="date" value={dateTo} onChange={(event) => setDateTo(event.currentTarget.value)} /><Button onClick={() => void load()}>Applica</Button><Button variant="subtle" onClick={() => { setTicker(""); setDateFrom(""); setDateTo(""); void load(""); }}>Azzera</Button><Button component="a" variant="light" href={api.exportUrl(ticker || undefined)} download>Posizioni CSV</Button><Button component="a" variant="light" href={api.performanceExportUrl(ticker || undefined, dateFrom || undefined, dateTo || undefined)} download>Performance CSV</Button></Group>
    {error && <Card withBorder><Text c="red">{error}</Text><Button mt="sm" size="xs" onClick={() => void load()}>Riprova</Button></Card>}
    {!summary && !error ? <Group justify="center" py="xl"><Loader aria-label="Caricamento portafoglio" /></Group> : <><SimpleGrid cols={{ base: 1, xs: 2, md: 4 }} spacing="md"><Metric label="Valore portafoglio" value={amount(summary?.kpis.market_value_eur)} note={summary?.valuation_status === "available" ? "Ultima osservazione persistita" : "Quotazioni mancanti"} /><Metric label="Capitale aperto" value={amount(summary?.kpis.open_cost_eur)} note="Costo ricostruito dal ledger" /><Metric label="P&L realizzato" value={amount(summary?.kpis.realized_pnl_eur)} note="Vendite registrate" positive={Number(summary?.kpis.realized_pnl_eur) > 0} /><Metric label="P&L non realizzato" value={amount(summary?.kpis.unrealized_pnl_eur)} note="Disponibile con quotazioni EOD" positive={Number(summary?.kpis.unrealized_pnl_eur) > 0} /></SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md"><Card withBorder radius="md" className="chart-card" style={{ gridColumn: "span 2" }}><Group justify="space-between"><Title order={3}>Valore nel tempo</Title><Group gap="xs"><Select aria-label="Intervallo grafico" size="xs" value={range} onChange={(value) => setRange(value || "Tutto")} data={["1M", "3M", "6M", "YTD", "1Y", "2Y", "Tutto"]} /><Badge variant="outline">EUR</Badge></Group></Group><PortfolioChart performance={performance} range={range} /><Text size="xs" c="dimmed">{performance?.methodology || "Serie non disponibile: servono osservazioni storiche valide."}</Text></Card><Card withBorder radius="md"><Title order={3}>Stato dati</Title><Stack mt="md" gap="sm"><Status label="Ledger" value={String(positions.length) + " strumenti"} /><Status label="Provider prezzi" value={summary?.valuation_status === "available" ? "Osservazioni persistite" : "Nessuna osservazione"} /><Status label="Rendimento TWR" value={performance?.total_return == null ? "N/D" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(Number(performance.total_return))} /><Status label="Ultima quotazione" value={latestObservation(positions)} /></Stack></Card></SimpleGrid>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Rendimento vs benchmark</Title><Badge variant="outline">Base comune 0%</Badge></Group><BenchmarkChart performance={performance} range={range} /><Text size="xs" c="dimmed">I benchmark price-return escludono i dividendi: la comparabilità è indicata nella legenda.</Text></Card>
      <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Posizioni</Title><Button variant="subtle" size="xs" onClick={onOpenRegistry}>Registro operazioni</Button></Group><PositionTable positions={positions} /></Card></>}
  </Stack>;
}

function PositionTable({ positions }: { positions: PortfolioSummary["positions"] }) {
  if (!positions.length) return <Text c="dimmed" mt="md">Nessuna posizione per il filtro selezionato.</Text>;
  return <Table.ScrollContainer minWidth={680}><Table mt="md" striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Strumento</Table.Th><Table.Th>Quantità</Table.Th><Table.Th>Costo EUR</Table.Th><Table.Th>Valore</Table.Th><Table.Th>P&L realizzato</Table.Th><Table.Th>Stato</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{positions.map((position) => <Table.Tr key={position.ticker}><Table.Td><Text fw={600}>{position.ticker}</Text><Text size="xs" c="dimmed">{position.accounts.map((item) => item.name).join(" · ")}</Text></Table.Td><Table.Td>{Number(position.quantity).toLocaleString("it-IT")}</Table.Td><Table.Td>{amount(position.open_cost_eur)}</Table.Td><Table.Td>{amount(position.market_value_eur)}</Table.Td><Table.Td>{amount(position.realized_pnl_eur)}</Table.Td><Table.Td><Badge color={position.market_data_status === "available" ? "teal" : "yellow"} title={position.market_data_provider ? `${position.market_data_provider}${position.market_data_source_symbol ? ` · ${position.market_data_source_symbol}` : ""}` : undefined}>{position.market_data_status === "available" ? (position.market_data_provider || "EOD") : "Mancante"}</Badge></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>;
}

function latestObservation(positions: PortfolioSummary["positions"]): string {
  const values = positions.map((position) => position.last_observed_at).filter((value): value is string => value != null).sort();
  const latest = values[values.length - 1];
  return latest ? new Date(latest).toLocaleString("it-IT") : "Non disponibile";
}

function Operations() {
  const [items, setItems] = useState<Operation[]>([]);
  const [error, setError] = useState("");
  const load = async () => { try { setItems((await api.operations()).items); } catch (reason) { setError(reason instanceof Error ? reason.message : "Registro non disponibile"); } };
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = new FormData(event.currentTarget);
    try { await api.createOperation({ account_name: values.get("account"), ticker: values.get("ticker"), kind: values.get("kind"), quantity: values.get("quantity"), unit_price_eur: values.get("price"), original_unit_price: values.get("original_price") || null, original_currency: values.get("original_currency") || null, trade_date: values.get("date"), settlement_date: values.get("settlement_date") || null, note: values.get("note") || null, is_approximate: values.get("is_approximate") === "on", source_order: 0 }); event.currentTarget.reset(); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile registrare il movimento"); }
  }
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Ledger con audit</Text><Title order={2}>Registro operazioni</Title></div><Card withBorder><form onSubmit={submit}><SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}><TextInput required name="account" label="Account" /><TextInput required name="ticker" label="Ticker" /><Select required name="kind" label="Tipo" data={[{ value: "BUY", label: "Acquisto" }, { value: "SELL", label: "Vendita" }, { value: "OPENING_BALANCE", label: "Saldo iniziale" }, { value: "TRANSFER_IN", label: "Trasferimento in entrata" }, { value: "TRANSFER_OUT", label: "Trasferimento in uscita" }, { value: "ADJUSTMENT", label: "Rettifica" }, { value: "DIVIDEND", label: "Dividendo" }, { value: "FEE", label: "Commissione" }]} /><NumberInput required name="quantity" label="Quantità" decimalScale={6} /><NumberInput required name="price" label="Prezzo EUR" min={0} decimalScale={4} /><TextInput name="original_price" label="Prezzo originale" /><TextInput name="original_currency" label="Valuta originale" maxLength={8} /><TextInput required name="date" type="date" label="Data" defaultValue={new Date().toISOString().slice(0, 10)} /><TextInput name="settlement_date" type="date" label="Data regolamento" /><TextInput name="note" label="Nota" /><label><input name="is_approximate" type="checkbox" /> Dato approssimativo</label></SimpleGrid><Button mt="md" type="submit">Registra movimento</Button></form></Card>{error && <Text c="red">{error}</Text>}<Card withBorder><Table.ScrollContainer minWidth={720}><Table><Table.Thead><Table.Tr><Table.Th>Data</Table.Th><Table.Th>Account</Table.Th><Table.Th>Ticker</Table.Th><Table.Th>Tipo</Table.Th><Table.Th>Quantità</Table.Th><Table.Th>Prezzo</Table.Th><Table.Th>Contesto</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}><Table.Td>{new Date(item.trade_date).toLocaleDateString("it-IT")}</Table.Td><Table.Td>{item.account_name}</Table.Td><Table.Td>{item.ticker}</Table.Td><Table.Td>{item.kind}</Table.Td><Table.Td>{item.quantity}</Table.Td><Table.Td>{amount(item.unit_price_eur)}</Table.Td><Table.Td>{item.note || (item.is_approximate ? "Approssimato" : "—")}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card></Stack>;
}

function Metric({ label, value, note, positive = false }: { label: string; value: string; note: string; positive?: boolean }) { return <Card withBorder radius="md"><Text size="sm" c="dimmed">{label}</Text><Text className={positive ? "positive metric" : "metric"}>{value}</Text><Text size="xs" c="dimmed">{note}</Text></Card>; }
function Status({ label, value }: { label: string; value: string }) { return <Group justify="space-between" wrap="nowrap"><Text size="sm">{label}</Text><Text size="sm" c="dimmed">{value}</Text></Group>; }
function PortfolioChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range);
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); chart.setOption(points.length ? { grid: { left: 48, right: 16, top: 18, bottom: 28 }, tooltip: { trigger: "axis", valueFormatter: (value: number) => euro.format(value) }, xAxis: { type: "category", data: points.map((point) => point.date), axisLabel: { formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) } }, yAxis: { type: "value", axisLabel: { formatter: (value: number) => euro.format(value) } }, series: [{ type: "line", data: points.map((point) => Number(point.value_eur)), smooth: true, showSymbol: false, areaStyle: { opacity: 0.16 }, lineStyle: { color: "#22d3ee" } }] } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "Nessuna serie storica disponibile", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points]);
  return <div className="chart" ref={element} role="img" aria-label="Grafico del valore del portafoglio" />;
}

function BenchmarkChart({ performance, range }: { performance?: PerformanceSummary; range: string }) {
  const element = useRef<HTMLDivElement>(null);
  const points = withinRange(performance?.points ?? [], range).filter((point) => point.cumulative_return != null);
  const benchmarks = (performance?.benchmarks ?? []).map((benchmark) => ({ ...benchmark, points: withinRange(benchmark.points, range) }));
  useEffect(() => { if (!element.current) return; let disposed = false; let chart: { setOption: (option: object) => void; resize: () => void; dispose: () => void } | undefined; void Promise.all([import("echarts/core"), import("echarts/renderers"), import("echarts/components"), import("echarts/charts")]).then(([echarts, renderers, components, charts]) => { if (disposed || !element.current) return; echarts.use([renderers.SVGRenderer, components.GraphicComponent, components.GridComponent, components.TooltipComponent, components.LegendComponent, components.DataZoomComponent, charts.LineChart]); chart = echarts.init(element.current, undefined, { renderer: "svg" }); const dates = points.map((point) => point.date); const series = [{ name: "Portafoglio TWR", type: "line", data: points.map((point) => Number(point.cumulative_return)), smooth: true, showSymbol: false, lineStyle: { color: "#22d3ee" } }, ...benchmarks.map((benchmark) => ({ name: `${benchmark.name} (${benchmark.methodology === "price_return" ? "price" : "total"})`, type: "line", data: dates.map((day) => Number(benchmark.points.find((point) => point.date === day)?.return ?? NaN)), smooth: true, showSymbol: false }))]; chart.setOption(points.length ? { grid: { left: 52, right: 18, top: 36, bottom: 42 }, legend: { top: 0 }, tooltip: { trigger: "axis", valueFormatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(value) }, dataZoom: [{ type: "inside" }], xAxis: { type: "category", data: dates, axisLabel: { formatter: (value: string) => new Date(value).toLocaleDateString("it-IT", { month: "short", year: "2-digit" }) } }, yAxis: { type: "value", axisLabel: { formatter: (value: number) => new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 0 }).format(value) } }, series } : { series: [], graphic: { type: "text", left: "center", top: "middle", style: { text: "Benchmark o rendimento non disponibili", fill: "#9097a6", fontSize: 14 } } }); }); const resize = () => chart?.resize(); window.addEventListener("resize", resize); return () => { disposed = true; window.removeEventListener("resize", resize); chart?.dispose(); }; }, [points, benchmarks]);
  return <div className="chart" ref={element} role="img" aria-label="Grafico del rendimento del portafoglio rispetto ai benchmark" />;
}

function withinRange<T extends { date: string }>(points: T[], range: string): T[] {
  if (!points.length || range === "Tutto") return points;
  const end = new Date(points.at(-1)!.date);
  const start = new Date(end);
  if (range === "YTD") start.setMonth(0, 1); else start.setMonth(start.getMonth() - Number(range.replace("M", "").replace("Y", "")) * (range.endsWith("Y") ? 12 : 1));
  return points.filter((point) => new Date(point.date) >= start);
}
