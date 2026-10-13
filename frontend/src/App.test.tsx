import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("echarts", () => ({
  init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }),
}));
vi.mock("echarts/core", () => ({ use: vi.fn(), init: () => ({ setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn() }) }));
vi.mock("echarts/renderers", () => ({ SVGRenderer: {} }));
vi.mock("echarts/components", () => ({ GraphicComponent: {} }));

import { App } from "./App";

describe("App", () => {
  it("renders the Italian private portfolio shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Investix" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accedi" })).toBeInTheDocument();
  });
});
