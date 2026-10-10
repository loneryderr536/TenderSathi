import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { setSession } from "../api";
import { AuthProvider } from "../auth";
import { mockApi, renderPage } from "../test/utils";
import PrivatePage from "./PrivatePage";
import PrivateRfqPage from "./PrivateRfqPage";
import TenderPage from "./TenderPage";
import { result } from "../test/samples";

it("lists the owner's requests and refuses an advance outside 25-50%", async () => {
  const calls = mockApi({
    "GET /rfq/mine": [{ id: 7, title: "Dining tables", advance_percent: 30, quotations: 2, lowest: 850000, accepted: null, status: "new" }],
    "GET /gov/tenders": [],
    "POST /rfq": { id: 8 },
  });
  const ui = userEvent.setup();
  renderPage(<PrivatePage />);
  expect(await screen.findByRole("link", { name: "Dining tables" })).toHaveAttribute("href", "/private/rfq/7");
  expect(screen.getByText(/2 quotations · lowest ₹8,50,000/)).toBeInTheDocument();

  await ui.type(screen.getByLabelText("Title"), "Chairs");
  await ui.type(screen.getByLabelText("What you need (scope)"), "240 chairs");
  await ui.type(screen.getByLabelText("Last date for quotations"), "5 Nov");
  await ui.clear(screen.getByLabelText("Advance percent"));
  await ui.type(screen.getByLabelText("Advance percent"), "10");
  expect(screen.getByText("The advance must be between 25% and 50%.")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Post request" })).toBeDisabled();

  await ui.clear(screen.getByLabelText("Advance percent"));
  await ui.type(screen.getByLabelText("Advance percent"), "40");
  await ui.click(screen.getByRole("button", { name: "Post request" }));
  await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/rfq")).toBe(true));
  const body = JSON.parse(calls.find((c) => c.method === "POST").init.body);
  expect(body).toMatchObject({ title: "Chairs", advance_percent: 40, requirements: [], delivery_days: 30 });
});

it("shows quotations, lowest first, and accepts one", async () => {
  const calls = mockApi({
    "GET /gov/tenders/7": { tender: { id: 7, title: "Dining tables", kind: "private", buyer: "Marine Drive Hotels", advance_percent: 30, status: "new" },
                            fairness: null, insights: { running: false, screened: 0, businesses: [], by_rule: [] } },
    "GET /rfq/7/quotations": [
      { id: 1, company_name: "Shop B", company_location: "Kochi", company_udyam: 1, amount: 850000, delivery_days: 50, note: "", status: "submitted" },
      { id: 2, company_name: "Shop A", company_location: "Aluva", company_udyam: 0, amount: 880000, delivery_days: 40, note: "Teak", status: "submitted" },
    ],
    "POST /rfq/7/quotations/1/accept": { status: "awarded" },
  });
  const ui = userEvent.setup();
  renderPage(<PrivateRfqPage />, { path: "/private/rfq/:id", route: "/private/rfq/7" });
  expect(await screen.findByText("Quotations received (2)")).toBeInTheDocument();
  expect(screen.getByText("30% advance on order")).toBeInTheDocument();
  expect(screen.getByText("lowest")).toBeInTheDocument();
  await ui.click(screen.getAllByRole("button", { name: "Accept" })[0]);
  await waitFor(() => expect(calls.some((c) => c.path === "/rfq/7/quotations/1/accept")).toBe(true));
});

it("a business sends its quotation on a private request", async () => {
  localStorage.clear();
  setSession("t", { id: 1, role: "business", name: "John", company_id: 1 });
  const calls = mockApi({
    "GET /tenders/5/result": result({ tender: { kind: "private", advance_percent: 30 } }), "GET /tenders/5/log": [],
    "GET /rfq/5/my-quote": null,
    "POST /rfq/5/quote": { amount: 900000, delivery_days: 40, status: "submitted" },
  });
  const ui = userEvent.setup();
  renderPage(<AuthProvider><TenderPage /></AuthProvider>, { path: "/tenders/:id", route: "/tenders/5" });
  expect(await screen.findByText("Send a quotation")).toBeInTheDocument();
  expect(screen.getByText("30% in advance")).toBeInTheDocument();
  await ui.type(screen.getByLabelText("Your price (₹)"), "900000");
  await ui.type(screen.getByLabelText("Delivery (days)"), "40");
  await ui.click(screen.getByRole("button", { name: "Send quotation" }));
  await waitFor(() => expect(calls.some((c) => c.method === "POST" && c.path === "/rfq/5/quote")).toBe(true));
  expect(JSON.parse(calls.find((c) => c.method === "POST").init.body)).toEqual({ amount: 900000, delivery_days: 40, note: "" });
  localStorage.clear();
});
