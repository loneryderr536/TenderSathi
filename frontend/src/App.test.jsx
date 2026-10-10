import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import App from "./App";
import { getCompanyId } from "./api";
import { mockApi } from "./test/utils";

function renderApp(route) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[route]}><App /></MemoryRouter>
    </QueryClientProvider>,
  );
}

it("remembers the profile id given in the link from the demo loader", async () => {
  mockApi({ "GET /tenders": [] });
  renderApp("/?company=3");
  await waitFor(() => expect(getCompanyId()).toBe(3));
  expect(await screen.findByText(/No tenders yet/)).toBeInTheDocument();
});

it("ignores a bad company value", async () => {
  mockApi({ "GET /tenders": [] });
  renderApp("/?company=abc");
  await screen.findByText(/No tenders yet/);
  expect(getCompanyId()).toBeNull();
});

it("switches between the business, government and platform views", async () => {
  mockApi({ "GET /gov/tenders": [] });
  renderApp("/gov");
  expect(await screen.findByText("Buyer dashboard", { selector: "h1" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Government" })).toHaveAttribute("aria-current", "true");
  expect(screen.getByRole("link", { name: "Business" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: "Platform" })).toHaveAttribute("href", "/admin");
  expect(screen.queryByRole("link", { name: "Business profile" })).not.toBeInTheDocument();
});
