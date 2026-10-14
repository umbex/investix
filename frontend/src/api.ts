export type AccountPosition = {
  name: string;
  quantity: string;
  open_cost_eur: string;
  realized_pnl_eur: string;
};

export type Position = {
  ticker: string;
  quantity: string;
  open_cost_eur: string;
  average_cost_eur: string;
  realized_pnl_eur: string;
  market_value_eur: string | null;
  unrealized_pnl_eur: string | null;
  market_data_status: "available" | "missing";
  last_observed_at: string | null;
  market_data_provider: string | null;
  market_data_source_symbol: string | null;
  market_data_venue: string | null;
  market_data_fx_provider: string | null;
  accounts: AccountPosition[];
};

export type PortfolioSummary = {
  positions: Position[];
  allocations: { ticker: string; market_value_eur: string | null; weight: string | null; open_cost_eur: string; cost_weight: string | null; accounts: { account: string; open_cost_eur: string; weight: string | null }[] }[];
  account_allocations: { account: string; open_cost_eur: string; weight: string | null }[];
  kpis: {
    open_cost_eur: string;
    market_value_eur: string | null;
    realized_pnl_eur: string;
    unrealized_pnl_eur: string | null;
  };
  valuation_status: "available" | "unavailable_without_observation";
};

export type WorkerHealth = {
  status: "ok" | "unknown" | "not_configured";
  updated_at?: string;
  provider?: string;
  detail?: string;
};

export type QuotesSummary = {
  days: number;
  items: {
    ticker: string;
    price_eur: string | null;
    change_percent: string | null;
    observed_at: string | null;
    provider: string | null;
    quote_symbol?: string | null;
    quote_venue?: string | null;
    watch?: boolean;
    has_position?: boolean;
    points: { observed_at: string; price_eur: string }[];
  }[];
};

export type LiveQuotesSummary = {
  status: "fresh" | "pending" | "stale" | "quota_exhausted" | "provider_disabled" | "error";
  items: {
    ticker: string;
    price: string;
    price_eur: string | null;
    currency: string;
    change_percent: string | null;
    observed_at: string;
    provider: string;
    status: "fresh" | "stale";
  }[];
  statuses: Record<string, string>;
  credits_used: number;
  retry_after: number | null;
};

export type InstrumentLookupResult = {
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  type: string;
};

export type InstrumentCatalogItem = {
  ticker: string;
  quote_symbol: string | null;
  quote_venue: string | null;
  quote_currency: string | null;
  watch: boolean;
  has_position: boolean;
};

export type BenchmarkConfig = {
  name: string;
  ticker: string;
  quote_symbol: string;
  quote_venue: string;
  quote_currency: string;
  methodology: "price_return" | "total_return";
  active: boolean;
  note?: string | null;
};

export type PerformanceSummary = {
  points: { date: string; value_eur: string; external_flow_eur: string; cumulative_return: string | null }[];
  total_return: string | null;
  methodology: string;
  benchmarks: {
    name: string;
    ticker: string;
    quote_currency: string;
    methodology: "price_return" | "total_return";
    points: { date: string; return: string }[];
  }[];
};

export type Operation = {
  id: number;
  account_name: string;
  ticker: string;
  kind: "BUY" | "SELL" | "OPENING_BALANCE" | "DIVIDEND" | "FEE" | "SPLIT" | "TRANSFER_IN" | "TRANSFER_OUT" | "ADJUSTMENT";
  quantity: string;
  unit_price_eur: string;
  trade_date: string;
  source_order: number;
  fee_eur: string | null;
  dividend_eur: string | null;
  original_unit_price: string | null;
  original_currency: string | null;
  settlement_date: string | null;
  note: string | null;
  is_approximate: boolean;
};

const apiUrl = (path: string) => "/api" + path;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { credentials: "include", ...init });
  if (!response.ok) throw new Error(response.status === 401 ? "Sessione scaduta" : "Operazione non riuscita");
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export const api = {
  authMode: () => request<{ bypass: boolean }>("/auth/mode"),
  login: (username: string, password: string) => request<void>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }),
  portfolio: (ticker?: string, account?: string) => {
    const params = new URLSearchParams();
    if (ticker) params.set("ticker", ticker);
    if (account) params.set("account", account);
    const query = params.toString();
    return request<PortfolioSummary>("/portfolio" + (query ? `?${query}` : ""));
  },
  performance: (ticker?: string, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams();
    if (ticker) params.set("ticker", ticker);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const query = params.toString();
    return request<PerformanceSummary>("/performance" + (query ? `?${query}` : ""));
  },
  operations: () => request<{ items: Operation[]; total: number }>("/operations"),
  createOperation: (payload: Record<string, unknown>) => request<Operation>("/operations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  reviseOperation: (id: number, payload: Record<string, unknown>) => request<Operation>(`/operations/${id}/revise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  cancelOperation: (id: number, reason: string) => request<void>(`/operations/${id}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  }),
  exportUrl: (ticker?: string, account?: string) => {
    const params = new URLSearchParams();
    if (ticker) params.set("ticker", ticker);
    if (account) params.set("account", account);
    const query = params.toString();
    return apiUrl("/portfolio/export.csv" + (query ? `?${query}` : ""));
  },
  performanceExportUrl: (ticker?: string, dateFrom?: string, dateTo?: string) => {
    const params = new URLSearchParams();
    if (ticker) params.set("ticker", ticker);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const query = params.toString();
    return apiUrl("/performance/export.csv" + (query ? `?${query}` : ""));
  },
  workerHealth: () => request<WorkerHealth>("/health/worker"),
  quotes: (days: number) => request<QuotesSummary>(`/quotes?days=${days}`),
  liveQuotes: (symbols: string[], sessionId: string) => request<LiveQuotesSummary>(`/quotes/live?symbols=${encodeURIComponent(symbols.join(","))}&session_id=${encodeURIComponent(sessionId)}`),
  lookupInstrument: (query: string) => request<{ status: string; items: InstrumentLookupResult[]; message?: string }>(`/instruments/lookup?query=${encodeURIComponent(query)}`),
  instrumentCatalog: () => request<InstrumentCatalogItem[]>("/instruments/catalog"),
  setWatchInstrument: (ticker: string, payload: { quote_symbol: string; quote_venue: string; quote_currency: string; watch: boolean }) => request<InstrumentCatalogItem>(`/instruments/watch/${encodeURIComponent(ticker)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  benchmarks: () => request<BenchmarkConfig[]>("/benchmarks"),
  configureBenchmark: (ticker: string, payload: BenchmarkConfig) => request<BenchmarkConfig>(`/benchmarks/${encodeURIComponent(ticker)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
};
