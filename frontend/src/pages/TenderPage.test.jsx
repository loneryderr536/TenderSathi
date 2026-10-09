import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { setCompanyId } from "../api";
import { NEW_TENDER, result } from "../test/samples";
import { mockApi, renderPage } from "../test/utils";
import TenderPage from "./TenderPage";

const show = () => renderPage(<TenderPage />, { path: "/tenders/:id", route: "/tenders/5" });

it("shows the summary with payment terms", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  show();
  expect(await screen.findByRole("heading", { name: "School desks" })).toBeInTheDocument();
  expect(screen.getByText("30 days after delivery")).toBeInTheDocument();
  expect(screen.getByText("₹50,000")).toBeInTheDocument();
});

it("eligibility tab shows each verdict with clause and page", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  const user = userEvent.setup();
  show();
  await user.click(await screen.findByRole("tab", { name: "Eligibility" }));
  expect(screen.getByText("Pass")).toBeInTheDocument();
  expect(screen.getByText("Turnover is ₹1.4 crore")).toBeInTheDocument();
  expect(screen.getByText("Clause 4.1, page 7")).toBeInTheDocument();
});

it("checklist tab marks what is missing", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  const user = userEvent.setup();
  show();
  await user.click(await screen.findByRole("tab", { name: "Checklist" }));
  expect(screen.getByText("You have it (gst.pdf)")).toBeInTheDocument();
  expect(screen.getByText("You still need it")).toBeInTheDocument();
});

it("shows why a run stopped and that there is no draft", async () => {
  mockApi({
    "GET /tenders/5/result": result({ tender: { status: "stopped",
      reason: "Fails must-have rule(s): Turnover of Rs 1 crore (clause 4.1, page 7): too low" }, draft: null, review: null }),
    "GET /tenders/5/log": [],
  });
  const user = userEvent.setup();
  show();
  expect(await screen.findByRole("alert")).toHaveTextContent("Fails must-have rule(s): Turnover of Rs 1 crore");
  await user.click(screen.getByRole("tab", { name: "Draft" }));
  expect(screen.getByText(/No draft/)).toBeInTheDocument();
});

it("disables Run until a profile exists", async () => {
  mockApi({ "GET /tenders/5/result": NEW_TENDER, "GET /tenders/5/log": [] });
  show();
  expect(await screen.findByRole("button", { name: "Run the agents" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "Fill in your business profile" })).toHaveAttribute("href", "/profile");
});

it("starts a run with the saved profile and shows the live log", async () => {
  setCompanyId(3);
  let status = "new";
  const calls = mockApi({
    "GET /tenders/5/result": () => (status === "new" ? NEW_TENDER : result({ tender: { status: "running" } })),
    "GET /tenders/5/log": () => (status === "new" ? [] : [{ agent: "reader", message: "started", created_at: "x" }]),
    "POST /tenders/5/run": () => { status = "running"; return { run_id: "abc" }; },
  });
  const user = userEvent.setup();
  show();
  await user.click(await screen.findByRole("button", { name: "Run the agents" }));
  expect(JSON.parse(calls.find((c) => c.method === "POST").init.body)).toEqual({ company_id: 3 });
  await waitFor(() => expect(screen.getByRole("button", { name: "Agents working…" })).toBeDisabled());
  expect(await screen.findByText("Reader")).toBeInTheDocument();
  expect(screen.getByText("started")).toBeInTheDocument();
});

it("links to approval when the bid is ready", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  show();
  expect(await screen.findByRole("link", { name: "Review & approve the bid" })).toHaveAttribute("href", "/tenders/5/approve");
});

it("forgets a stale profile id when the server says the company is gone", async () => {
  setCompanyId(9);
  mockApi({
    "GET /tenders/5/result": NEW_TENDER, "GET /tenders/5/log": [],
    "POST /tenders/5/run": { status: 404, body: { detail: "Company not found" } },
  });
  const user = userEvent.setup();
  show();
  await user.click(await screen.findByRole("button", { name: "Run the agents" }));
  expect(await screen.findByRole("link", { name: "Fill in your business profile" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Run the agents" })).toBeDisabled();
});

it("keeps showing the tender when one poll fails", async () => {
  let fail = false;
  mockApi({
    "GET /tenders/5/result": () => (fail ? { status: 500, body: { detail: "Internal Server Error" } } : result()),
    "GET /tenders/5/log": [],
  });
  const { client } = show();
  await screen.findByRole("heading", { name: "School desks" });
  fail = true;
  await client.refetchQueries({ queryKey: ["tender", "5", "result"] });
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Internal Server Error"));
  expect(screen.getByRole("heading", { name: "School desks" })).toBeInTheDocument();
});

it("opens the tab named in the link", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  renderPage(<TenderPage />, { path: "/tenders/:id", route: "/tenders/5?tab=checklist" });
  expect(await screen.findByRole("tab", { name: "Checklist" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByText("You still need it")).toBeInTheDocument();
});

it("falls back to Summary for an unknown tab", async () => {
  mockApi({ "GET /tenders/5/result": result(), "GET /tenders/5/log": [] });
  renderPage(<TenderPage />, { path: "/tenders/:id", route: "/tenders/5?tab=nope" });
  expect(await screen.findByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
});

const CHANGES = { changes: [{ field: "deadline", before: "30 October 2026", after: "6 November 2026",
                              summary: "The deadline was extended by a week." }], affects_eligibility: true };

it("shows the countdown next to the title", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 28, 10, 0));
  mockApi({ "GET /tenders/5/result": result({ tender: { deadline_at: "2026-10-30T15:00:00" } }), "GET /tenders/5/log": [] });
  show();
  expect(await screen.findByText("2 days left")).toBeInTheDocument();
  vi.useRealTimers();
});

it("shows what a corrigendum changed and asks for a new run", async () => {
  setCompanyId(3);
  mockApi({ "GET /tenders/5/result": result({ tender: { status: "changed" }, changes: CHANGES }), "GET /tenders/5/log": [] });
  show();
  expect(await screen.findByText("The deadline was extended by a week.")).toBeInTheDocument();
  expect(screen.getByText("30 October 2026 → 6 November 2026")).toBeInTheDocument();
  expect(screen.getByText(/eligibility rules changed/i)).toBeInTheDocument();
  expect(screen.getByText(/Run the agents again/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Run again" })).toBeEnabled();
});

it("uploads a corrigendum and shows the changes", async () => {
  setCompanyId(3);
  let changed = false;
  const calls = mockApi({
    "GET /tenders/5/result": () => (changed ? result({ tender: { status: "changed" }, changes: CHANGES }) : result()),
    "GET /tenders/5/log": [],
    "POST /tenders/5/corrigendum": () => { changed = true; return CHANGES; },
  });
  const user = userEvent.setup();
  show();
  await user.upload(await screen.findByLabelText("Changed tender PDF (corrigendum)"),
                    new File(["%PDF"], "corr.pdf", { type: "application/pdf" }));
  await user.click(screen.getByRole("button", { name: "Check what changed" }));
  expect(await screen.findByText("The deadline was extended by a week.")).toBeInTheDocument();
  expect(calls.find((c) => c.method === "POST").init.body.get("file").name).toBe("corr.pdf");
});

it("shows why a corrigendum was refused", async () => {
  mockApi({
    "GET /tenders/5/result": result(), "GET /tenders/5/log": [],
    "POST /tenders/5/corrigendum": { status: 502, body: { detail: "Could not compare the two versions: Groq is down" } },
  });
  const user = userEvent.setup();
  show();
  await user.upload(await screen.findByLabelText("Changed tender PDF (corrigendum)"),
                    new File(["%PDF"], "corr.pdf", { type: "application/pdf" }));
  await user.click(screen.getByRole("button", { name: "Check what changed" }));
  expect(await screen.findByText("Could not compare the two versions: Groq is down")).toBeInTheDocument();
});

it("hides the corrigendum form before the tender has been read", async () => {
  mockApi({ "GET /tenders/5/result": NEW_TENDER, "GET /tenders/5/log": [] });
  show();
  await screen.findByRole("button", { name: "Run the agents" });
  expect(screen.queryByLabelText("Changed tender PDF (corrigendum)")).toBeNull();
});
