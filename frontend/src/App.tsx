import { AppShell, Badge, Button, Card, Group, Loader, MantineProvider, Modal, NumberInput, Select, SimpleGrid, Stack, Table, Text, TextInput, Title, Tooltip } from "@mantine/core";
import { FormEvent, useEffect, useRef, useState } from "react";

import { api, type Operation, type PerformanceSummary, type PortfolioSummary, type QuotesSummary, type WorkerHealth } from "./api";
import "./styles.css";

const euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
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
const percent = (value: string | null | undefined) => value == null ? "N/D" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 1 }).format(Number(value));
const chartText = "#b8c2d0";

export function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [page, setPage] = useState<"dashboard" | "operations">("dashboard");
  useEffect(() => { void api.authMode().then(({ bypass }) => { if (bypass) setAuthenticated(true); }).catch(() => undefined); }, []);
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
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth>({ status: "unknown" });
  const [quotes, setQuotes] = useState<QuotesSummary>();
  const [quoteRange, setQuoteRange] = useState("90");
  const [range, setRange] = useState("Tutto");
  const [ticker, setTicker] = useState("");
  const [account, setAccount] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const load = async (filter = ticker) => { setError(""); try { const nextSummary = await api.portfolio(filter || undefined, account || undefined); try { setPerformance(await api.performance(filter || undefined, dateFrom || undefined, dateTo || undefined)); } catch { setPerformance(undefined); } try { setWorkerHealth(await api.workerHealth()); } catch { setWorkerHealth({ status: "unknown" }); } try { setQuotes(await api.quotes(Number(quoteRange))); } catch { setQuotes(undefined); } setSummary(nextSummary); } catch (reason) { setError(reason instanceof Error ? reason.message : "Dati non disponibili"); } };
  useEffect(() => { void load(""); }, []);
  const changeQuoteRange = (value: string | null) => { const nextRange = value || "90"; setQuoteRange(nextRange); void api.quotes(Number(nextRange)).then(setQuotes).catch(() => setQuotes(undefined)); };
  const positions = summary?.positions ?? [];
  return <Stack gap="lg" className="dashboard">
    <Group justify="space-between" align="end" className="dashboard-title"><div><Text c="dimmed">Portafoglio privato</Text><Title order={2}>Panoramica</Title></div><Badge color={summary?.valuation_status === "available" ? "teal" : "yellow"}>{summary?.valuation_status === "available" ? "Quotazioni disponibili" : "Quotazioni mancanti"}</Badge></Group>
    <Group className="filter-bar" align="end"><Select label="Ticker" placeholder="Tutti" clearable value={ticker || null} onChange={(value) => setTicker(value || "")} data={positions.map((position) => position.ticker)} /><Select label="Account" placeholder="Tutti" clearable value={account || null} onChange={(value) => setAccount(value || "")} data={Array.from(new Set(positions.flatMap((position) => position.accounts.map((item) => item.name)))).sort()} /><TextInput label="Da" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.currentTarget.value)} /><TextInput label="A" type="date" value={dateTo} onChange={(event) => setDateTo(event.currentTarget.value)} /><Button onClick={() => void load()}>Applica</Button><Button variant="subtle" onClick={() => { setTicker(""); setAccount(""); setDateFrom(""); setDateTo(""); void load(""); }}>Azzera</Button></Group>
    {error && <Card withBorder><Text c="red">{error}</Text><Button mt="sm" size="xs" onClick={() => void load()}>Riprova</Button></Card>}
    {!summary && !error ? <Group justify="center" py="xl"><Loader aria-label="Caricamento portafoglio" /></Group> : <><SimpleGrid cols={{ base: 1, xs: 2, md: 4 }} spacing="md"><Metric label="Valore portafoglio" value={amount(summary?.kpis.market_value_eur)} note={summary?.valuation_status === "available" ? "Ultima osservazione persistita" : "Quotazioni mancanti"} /><Metric label="Capitale aperto" value={amount(summary?.kpis.open_cost_eur)} note="Costo ricostruito dal ledger" /><Metric label="P&L realizzato" value={amount(summary?.kpis.realized_pnl_eur)} note="Vendite registrate" positive={Number(summary?.kpis.realized_pnl_eur) > 0} /><Metric label="P&L non realizzato" value={amount(summary?.kpis.unrealized_pnl_eur)} note="Disponibile con quotazioni EOD" positive={Number(summary?.kpis.unrealized_pnl_eur) > 0} /></SimpleGrid>
      <Card withBorder radius="md"><Group justify="space-between" align="center"><Title order={3}>Quotazioni</Title><Select aria-label="Storico quotazioni" size="xs" value={quoteRange} onChange={changeQuoteRange} data={[{ value: "30", label: "1M" }, { value: "90", label: "3M" }, { value: "180", label: "6M" }, { value: "365", label: "1Y" }, { value: "3650", label: "Tutto" }]} /></Group><QuotesTable quotes={quotes} /></Card>
      <Card withBorder radius="md" className="positions"><Group justify="space-between"><Title order={3}>Posizioni</Title><Button variant="subtle" size="xs" onClick={onOpenRegistry}>Registro operazioni</Button></Group><PositionTable positions={positions} totalOpenCost={summary!.kpis.open_cost_eur} totalMarketValue={summary!.kpis.market_value_eur} /></Card>
      <SimpleGrid cols={{ base: 1, md: 3 }} spacing="md"><Card withBorder radius="md" className="chart-card" style={{ gridColumn: "span 2" }}><Group justify="space-between"><Title order={3}>Valore nel tempo</Title><Group gap="xs"><Select aria-label="Intervallo grafico" size="xs" value={range} onChange={(value) => setRange(value || "Tutto")} data={["1M", "3M", "6M", "YTD", "1Y", "2Y", "Tutto"]} /><Badge variant="outline">EUR</Badge></Group></Group><PortfolioChart performance={performance} range={range} /><Text size="xs" c="dimmed">{performance?.methodology || "Serie non disponibile: servono osservazioni storiche valide."}</Text></Card><Card withBorder radius="md"><Title order={3}>Stato dati</Title><Stack mt="md" gap="sm"><Status label="Ledger" value={String(positions.length) + " strumenti"} /><Status label="Provider prezzi" value={summary?.valuation_status === "available" ? "Osservazioni persistite" : "Nessuna osservazione"} /><Status label="Worker EOD" value={workerHealth.status === "ok" ? `Attivo${workerHealth.provider === "disabled" ? " · provider disabilitato" : ""}` : workerHealth.status === "not_configured" ? "Non configurato" : "Non verificato"} /><Status label="Rendimento TWR" value={performance?.total_return == null ? "N/D" : new Intl.NumberFormat("it-IT", { style: "percent", maximumFractionDigits: 2 }).format(Number(performance.total_return))} /><Status label="Ultima quotazione" value={latestObservation(positions)} /></Stack></Card></SimpleGrid>
      <Card withBorder radius="md" className="chart-card"><Group justify="space-between"><Title order={3}>Rendimento vs benchmark</Title><Badge variant="outline">Base comune 0%</Badge></Group><BenchmarkChart performance={performance} range={range} /><Text size="xs" c="dimmed">I benchmark price-return escludono i dividendi: la comparabilità è indicata nella legenda.</Text></Card></>}
  </Stack>;
}

function PositionTable({ positions, totalOpenCost, totalMarketValue }: { positions: PortfolioSummary["positions"]; totalOpenCost: string; totalMarketValue: string | null }) {
  if (!positions.length) return <Text c="dimmed" mt="md">Nessuna posizione per il filtro selezionato.</Text>;
  return <Table.ScrollContainer minWidth={680}><Table mt="md" striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Strumento</Table.Th><Table.Th>Quantità</Table.Th><Table.Th>Costo EUR</Table.Th><Table.Th>Valore</Table.Th><Table.Th>P&L realizzato</Table.Th><Table.Th>Stato</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{positions.map((position) => <Table.Tr key={position.ticker}><Table.Td><Text fw={600}>{position.ticker}</Text><Text size="xs" c="dimmed">{position.accounts.map((item) => item.name).join(" · ")}</Text></Table.Td><Table.Td>{Number(position.quantity).toLocaleString("it-IT")}</Table.Td><Table.Td><Text>{amount(position.open_cost_eur)}</Text><Text size="xs" c="dimmed">{percent(totalOpenCost && Number(totalOpenCost) ? String(Number(position.open_cost_eur) / Number(totalOpenCost)) : null)}</Text></Table.Td><Table.Td><Text>{amount(position.market_value_eur)}</Text><Text size="xs" c="dimmed">{percent(position.market_value_eur && totalMarketValue ? String(Number(position.market_value_eur) / Number(totalMarketValue)) : null)}</Text></Table.Td><Table.Td>{amount(position.realized_pnl_eur)}</Table.Td><Table.Td><Tooltip label={marketStatusLabel(position)}><span className={`market-status-icon ${position.market_data_status}`} role="img" aria-label={position.market_data_status === "available" ? "Quotazione disponibile" : "Quotazione mancante"}>{position.market_data_status === "available" ? "✓" : "!"}</span></Tooltip></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>;
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

function QuotesTable({ quotes }: { quotes?: QuotesSummary }) {
  if (!quotes?.items?.length) return <Text c="dimmed" mt="md">Quotazioni non disponibili.</Text>;
  return <Table.ScrollContainer minWidth={680}><Table mt="md" striped><Table.Thead><Table.Tr><Table.Th>Ticker</Table.Th><Table.Th>Ultimo</Table.Th><Table.Th>Variazione</Table.Th><Table.Th>Trend</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{quotes.items.map((item) => <Table.Tr key={item.ticker}><Table.Td><Text fw={600}>{item.ticker}</Text><Text size="xs" c="dimmed">{new Date(item.observed_at).toLocaleString("it-IT")}</Text></Table.Td><Table.Td>{amount(item.price_eur)}</Table.Td><Table.Td c={item.change_percent == null ? "dimmed" : Number(item.change_percent) >= 0 ? "teal" : "red"}>{item.change_percent == null ? "N/D" : `${Number(item.change_percent).toLocaleString("it-IT", { maximumFractionDigits: 2 })}%`}</Table.Td><Table.Td><Sparkline points={item.points.map((point) => Number(point.price_eur))} label={`Trend ${item.ticker}`} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>;
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
  const load = async () => { try { setItems((await api.operations()).items); } catch (reason) { setError(reason instanceof Error ? reason.message : "Registro non disponibile"); } };
  const startEdit = (item: Operation) => { setEditing(item); setReason(""); setQuantity(item.quantity); setPrice(item.unit_price_eur); setTradeDate(item.trade_date); setNote(item.note || ""); setError(""); };
  const revise = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (!editing || !reason.trim()) return; try { await api.reviseOperation(editing.id, { reason: reason.trim(), quantity, unit_price_eur: price, trade_date: tradeDate, note: note || null }); setEditing(null); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile correggere il movimento"); } };
  const cancel = async (item: Operation) => { if (!window.confirm(`Annullare il movimento ${item.ticker} del ${item.trade_date}?`)) return; const cancellationReason = window.prompt("Motivo dell'annullamento"); if (!cancellationReason?.trim()) return; try { await api.cancelOperation(item.id, cancellationReason.trim()); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile annullare il movimento"); } };
  useEffect(() => { void load(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const values = new FormData(event.currentTarget);
    try { await api.createOperation({ account_name: values.get("account"), ticker: values.get("ticker"), kind: values.get("kind"), quantity: parseNumericInput(values.get("quantity")), unit_price_eur: parseNumericInput(values.get("price")), original_unit_price: values.get("original_price") ? parseNumericInput(values.get("original_price")) : null, original_currency: values.get("original_currency") || null, trade_date: values.get("date"), settlement_date: values.get("settlement_date") || null, note: values.get("note") || null, is_approximate: values.get("is_approximate") === "on", source_order: 0 }); event.currentTarget.reset(); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Impossibile registrare il movimento"); }
  }
  return <Stack gap="lg" className="dashboard"><div><Text c="dimmed">Ledger con audit</Text><Title order={2}>Registro operazioni</Title></div><Card withBorder><form onSubmit={submit}><SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}><TextInput required name="account" label="Account" /><TextInput required name="ticker" label="Ticker" /><Select required name="kind" label="Tipo" data={[{ value: "BUY", label: "Acquisto" }, { value: "SELL", label: "Vendita" }, { value: "OPENING_BALANCE", label: "Saldo iniziale" }, { value: "TRANSFER_IN", label: "Trasferimento in entrata" }, { value: "TRANSFER_OUT", label: "Trasferimento in uscita" }, { value: "ADJUSTMENT", label: "Rettifica" }, { value: "DIVIDEND", label: "Dividendo" }, { value: "FEE", label: "Commissione" }]} /><NumberInput required name="quantity" label="Quantità" decimalScale={6} /><NumberInput required name="price" label="Prezzo EUR" min={0} decimalScale={4} /><TextInput name="original_price" label="Prezzo originale" /><TextInput name="original_currency" label="Valuta originale" maxLength={8} /><TextInput required name="date" type="date" label="Data" defaultValue={new Date().toISOString().slice(0, 10)} /><TextInput name="settlement_date" type="date" label="Data regolamento" /><TextInput name="note" label="Nota" /><label><input name="is_approximate" type="checkbox" /> Dato approssimativo</label></SimpleGrid><Button mt="md" type="submit">Registra movimento</Button></form></Card>{error && <Text c="red">{error}</Text>}<Card withBorder><Table.ScrollContainer minWidth={900}><Table><Table.Thead><Table.Tr><Table.Th>Data</Table.Th><Table.Th>Account</Table.Th><Table.Th>Ticker</Table.Th><Table.Th>Tipo</Table.Th><Table.Th>Quantità</Table.Th><Table.Th>Prezzo</Table.Th><Table.Th>Contesto</Table.Th><Table.Th>Azioni</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}><Table.Td>{new Date(item.trade_date).toLocaleDateString("it-IT")}</Table.Td><Table.Td>{item.account_name}</Table.Td><Table.Td>{item.ticker}</Table.Td><Table.Td>{item.kind}</Table.Td><Table.Td>{item.quantity}</Table.Td><Table.Td>{amount(item.unit_price_eur)}</Table.Td><Table.Td>{item.note || (item.is_approximate ? "Approssimato" : "—")}</Table.Td><Table.Td><Group gap="xs" wrap="nowrap"><Button size="xs" variant="light" onClick={() => startEdit(item)}>Modifica</Button><Button size="xs" variant="subtle" color="red" onClick={() => void cancel(item)}>Annulla</Button></Group></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer></Card><Modal opened={editing !== null} onClose={() => setEditing(null)} title={editing ? `Correggi ${editing.ticker}` : "Correggi movimento"}><form onSubmit={revise}><Stack><TextInput label="Motivazione" required value={reason} onChange={(event) => setReason(event.currentTarget.value)} /><NumberInput label="Quantità" required value={quantity} onChange={(value) => setQuantity(String(value))} min={0} decimalScale={6} /><NumberInput label="Prezzo EUR" required value={price} onChange={(value) => setPrice(String(value))} min={0} decimalScale={4} /><TextInput label="Data" type="date" required value={tradeDate} onChange={(event) => setTradeDate(event.currentTarget.value)} /><TextInput label="Nota" value={note} onChange={(event) => setNote(event.currentTarget.value)} /><Group justify="flex-end"><Button variant="subtle" onClick={() => setEditing(null)}>Chiudi</Button><Button type="submit">Salva correzione</Button></Group></Stack></form></Modal></Stack>;
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
  if (range === "YTD") start.setMonth(0, 1); else start.setMonth(start.getMonth() - Number(range.replace("M", "").replace("Y", "")) * (range.endsWith("Y") ? 12 : 1));
  return points.filter((point) => new Date(point.date) >= start);
}
