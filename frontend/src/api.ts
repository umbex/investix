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
  accounts: AccountPosition[];
};

export type PortfolioSummary = {
  positions: Position[];
  kpis: {
    open_cost_eur: string;
    market_value_eur: string | null;
    realized_pnl_eur: string;
    unrealized_pnl_eur: string | null;
  };
  valuation_status: "available" | "unavailable_without_observation";
};

export type PerformanceSummary = {
  points: { date: string; value_eur: string; external_flow_eur: string }[];
  total_return: string | null;
  methodology: string;
};

export type Operation = {
  id: number;
  account_name: string;
  ticker: string;
  kind: "BUY" | "SELL" | "DIVIDEND" | "FEE" | "SPLIT";
  quantity: string;
  unit_price_eur: string;
  trade_date: string;
  source_order: number;
  fee_eur: string | null;
  dividend_eur: string | null;
};

const apiUrl = (path: string) => "/api" + path;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { credentials: "include", ...init });
  if (!response.ok) throw new Error(response.status === 401 ? "Sessione scaduta" : "Operazione non riuscita");
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) => request<void>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }),
  portfolio: (ticker?: string) => request<PortfolioSummary>("/portfolio" + (ticker ? "?" + new URLSearchParams({ ticker }) : "")),
  performance: (ticker?: string) => request<PerformanceSummary>("/performance" + (ticker ? "?" + new URLSearchParams({ ticker }) : "")),
  operations: () => request<{ items: Operation[]; total: number }>("/operations"),
  createOperation: (payload: Record<string, unknown>) => request<Operation>("/operations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }),
  exportUrl: (ticker?: string) => apiUrl("/portfolio/export.csv" + (ticker ? "?" + new URLSearchParams({ ticker }) : "")),
};
