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
});

describe("App", () => {
  it("renders the Italian private portfolio shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Investix" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accedi" })).toBeInTheDocument();
  });

  it("shows imported positions after private login", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 204 })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          valuation_status: "unavailable_without_observation",
          kpis: { open_cost_eur: "200", market_value_eur: null, realized_pnl_eur: "0", unrealized_pnl_eur: null },
          positions: [{
            ticker: "VWCE", quantity: "2", open_cost_eur: "200", average_cost_eur: "100", realized_pnl_eur: "0",
            market_value_eur: null, unrealized_pnl_eur: null, market_data_status: "missing",
            accounts: [{ name: "Directa", quantity: "2", open_cost_eur: "200", realized_pnl_eur: "0" }],
          }],
        }),
      })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ points: [], total_return: null, methodology: "TWR", benchmarks: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByRole("textbox", { name: /Utente/ }), { target: { value: "investix" } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: "password" } });
    fireEvent.click(screen.getByRole("button", { name: "Accedi" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Panoramica" })).toBeInTheDocument());
    expect(await screen.findByText("VWCE")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/login");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/portfolio");
  });
});
