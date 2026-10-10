import { screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { mockApi, renderPage } from "../test/utils";
import AdminPage from "./AdminPage";

it("shows agent health, scout sweeps and owner-checked accuracy", async () => {
  mockApi({ "GET /admin/stats": {
    tenders: 5, by_status: { awaiting_approval: 2 }, by_source: { GeM: 2 }, businesses: 7, msme_businesses: 5,
    agents: [{ agent: "reader", model: "openai/gpt-oss-20b", runs: 3, avg_seconds: 4.5, retries: 1, failures: 0 }],
    runs: [{ run_id: "r1", tender_id: 1, title: "School desks", last: "await_approval finished", seconds: 41, failed: false }],
    accuracy: [{ agent: "eligibility", judged: 4, correct: 3, accuracy: 75 }],
    scout_runs: [{ id: 1, message: "5 new tender(s); 3 fit the business and went to the agents", created_at: "2026-10-10 06:00:00" }],
    scout_interval_seconds: 0,
  } });
  renderPage(<AdminPage />);
  expect(await screen.findByText("75%")).toBeInTheDocument();
  expect(screen.getByText("openai/gpt-oss-20b")).toBeInTheDocument();
  expect(screen.getByText("4.5s")).toBeInTheDocument();
  expect(screen.getByText(/3 fit the business/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "School desks" })).toHaveAttribute("href", "/tenders/1");
});
