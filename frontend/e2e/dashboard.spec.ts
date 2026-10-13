import { expect, test } from "@playwright/test";

const portfolio = {
  valuation_status: "available",
  kpis: { open_cost_eur: "200", market_value_eur: "220", realized_pnl_eur: "0", unrealized_pnl_eur: "20" },
  positions: [{
    ticker: "VWCE", quantity: "2", open_cost_eur: "200", average_cost_eur: "100", realized_pnl_eur: "0",
    market_value_eur: "220", unrealized_pnl_eur: "20", market_data_status: "available", last_observed_at: "2026-01-04T18:00:00Z",
    market_data_provider: "fixture", market_data_source_symbol: "VWCE.AS", market_data_venue: "AMS", market_data_fx_provider: null,
    accounts: [{ name: "Directa", quantity: "2", open_cost_eur: "200", realized_pnl_eur: "0" }],
  }],
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/auth/login", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/portfolio**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(portfolio) }));
  await page.route("**/api/performance**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ points: [{ date: "2026-01-04", value_eur: "220", external_flow_eur: "0", cumulative_return: "0.1" }], total_return: "0.1", methodology: "TWR", benchmarks: [] }) }));
  await page.route("**/api/health/worker", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "ok", provider: "disabled" }) }));
});

test("desktop dashboard filters date range and exposes CSV exports", async ({ page }) => {
  const performanceRequests: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/api/performance?")) performanceRequests.push(request.url()); });
  await page.goto("/");
  await page.getByLabel("Utente").fill("investix");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Accedi" }).click();
  await expect(page.getByRole("heading", { name: "Panoramica" })).toBeVisible();
  await expect(page.getByText("VWCE")).toBeVisible();
  await page.getByLabel("Da").fill("2026-01-01");
  await page.getByLabel("A", { exact: true }).fill("2026-01-31");
  await page.getByRole("button", { name: "Applica" }).click();
  await expect.poll(() => performanceRequests.some((url) => url.includes("date_from=2026-01-01") && url.includes("date_to=2026-01-31"))).toBe(true);
  await expect(page.getByRole("link", { name: "Performance CSV" })).toHaveAttribute("href", /date_from=2026-01-01/);
});

test("mobile dashboard keeps the portfolio and worker status visible", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Utente").fill("investix");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Accedi" }).click();
  await expect(page.getByText("VWCE")).toBeVisible();
  await expect(page.getByText("Attivo · provider disabilitato")).toBeVisible();
});
