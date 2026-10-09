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
