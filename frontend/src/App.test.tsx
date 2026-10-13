import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("renders the Italian private portfolio shell", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Investix" })).toBeInTheDocument();
    expect(screen.getByText("Portafoglio privato")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Panoramica" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Posizioni" })).toBeInTheDocument();
  });
});
