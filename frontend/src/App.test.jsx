import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { expect, it } from "vitest";
import App from "./App";
import { clearSession, getCompanyId, setSession } from "./api";
import { mockApi } from "./test/utils";

const PLATFORM = { id: 9, email: "admin@x.in", name: "Admin", role: "platform", company_id: null, department: null };

function renderApp(route, user = PLATFORM) {
  clearSession();
  if (user) setSession("token-1", user);
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

it("shows the login page when nobody is logged in", async () => {
  renderApp("/admin", null);
  expect(await screen.findByText("Log in to TenderSathi")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/signup");
});

it("a government buyer is kept to the government view", async () => {
  mockApi({ "GET /gov/tenders": [] });
  renderApp("/admin", { ...PLATFORM, role: "government", name: "Officer" });
  expect(await screen.findByText("Buyer dashboard", { selector: "h1" })).toBeInTheDocument();
  expect(screen.queryByRole("group", { name: "View as" })).not.toBeInTheDocument();
  expect(screen.getByText("Officer · Government")).toBeInTheDocument();
});
