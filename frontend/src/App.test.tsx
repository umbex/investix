import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("echarts", () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}));
vi.mock("echarts/core", () => ({ use: vi.fn(), init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }) }));
vi.mock("echarts/renderers", () => ({ SVGRenderer: {} }));
vi.mock("echarts/components", () => ({ GraphicComponent: {}, GridComponent: {}, TooltipComponent: {}, LegendComponent: {}, DataZoomComponent: {} }));
vi.mock("echarts/charts", () => ({ LineChart: {} }));

import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

describe("App", () => {
  it("renders a self-contained synthetic demo without calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    window.history.pushState({}, "", "/?demo=1");

    render(<App />);

    expect((await screen.findAllByText("Demo data")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "Quotes" })).toBeInTheDocument();
    expect(screen.getAllByText("MSFT").length).toBeGreaterThanOrEqual(1);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("renders the English private portfolio shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Investix" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows imported positions after private login", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ bypass: false }) })
      .mockResolvedValueOnce({ ok: true, status: 204 })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          valuation_status: "unavailable_without_observation",
          kpis: { open_cost_eur: "200", market_value_eur: "1234.56", realized_pnl_eur: "0", unrealized_pnl_eur: null },
          positions: [{
            ticker: "VWCE", quantity: "2", open_cost_eur: "200", average_cost_eur: "100", realized_pnl_eur: "0",
            market_value_eur: null, unrealized_pnl_eur: null, market_data_status: "missing",
            accounts: [{ name: "Directa", quantity: "2", open_cost_eur: "200", realized_pnl_eur: "0" }],
          }],
          allocations: [{ ticker: "VWCE", market_value_eur: null, weight: null }],
          account_allocations: [{ account: "Directa", open_cost_eur: "200", weight: "1" }],
        }),
      })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ points: [], total_return: null, methodology: "TWR", benchmarks: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: "ok" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ days: 90, items: [{ ticker: "VWCE", price_eur: "110", change_percent: "10", observed_at: "2026-10-14T15:00:00Z", provider: "twelve-data", points: [{ observed_at: "2026-10-14T15:00:00Z", price_eur: "110" }] }] }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByRole("textbox", { name: /Username/ }), { target: { value: "investix" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Quotes" })).toBeInTheDocument());
    const quotesHeading = screen.getByRole("heading", { name: "Quotes" });
    const positionsHeading = screen.getByRole("heading", { name: "Positions" });
    const valueHeading = screen.getByRole("heading", { name: "Value over time" });
    const benchmarkHeading = screen.getByRole("heading", { name: "Return vs benchmark" });
    const twrLabel = screen.getByText("TWR return");
    expect(screen.queryByText("Quotes available")).not.toBeInTheDocument();
    expect(quotesHeading).toBeInTheDocument();
    expect(screen.getByText(/1,23K€/)).toBeInTheDocument();
    expect(screen.getAllByRole("textbox", { name: /Chart range|Benchmark range|Quotes history/ })).toHaveLength(3);
    expect(twrLabel.compareDocumentPosition(quotesHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(quotesHeading.compareDocumentPosition(positionsHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(positionsHeading.compareDocumentPosition(valueHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Data status" })).not.toBeInTheDocument();
    expect((await screen.findAllByText("VWCE")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Today P&L").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("img", { name: /Market (open|closed)/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Allocazione" })).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Ticker")[0]).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Positions CSV" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Performance CSV" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Quote missing")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByRole("heading", { name: "Data status" })).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/mode");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/auth/login");
    expect(fetchMock.mock.calls[2][0]).toBe("/api/portfolio");
  });

  it("shows correction and cancellation actions in the register", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ bypass: true }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ valuation_status: "unavailable_without_observation", kpis: { open_cost_eur: "100", market_value_eur: null, realized_pnl_eur: "0", unrealized_pnl_eur: null }, positions: [], allocations: [], account_allocations: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ points: [], total_return: null, methodology: "TWR", benchmarks: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ status: "ok" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ days: 90, items: [] }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ total: 1, items: [{ id: 7, account_name: "Directa", ticker: "VWCE", kind: "BUY", quantity: "1", unit_price_eur: "100", trade_date: "2026-01-02", source_order: 1, fee_eur: null, dividend_eur: null, original_unit_price: null, original_currency: null, settlement_date: null, note: null, is_approximate: false }] }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "Quotes" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Register" }));

    expect(await screen.findByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });
});
