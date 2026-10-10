import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { mockApi, renderPage } from "../test/utils";
import GovPage from "./GovPage";
import GovTenderPage from "./GovTenderPage";

it("lists portal tenders and drafts with fairness and screening totals", async () => {
  mockApi({ "GET /gov/tenders": [
    { id: 4, title: "Classroom benches", kind: "portal", buyer: "Kuttanad Block Panchayat", portal: "Kerala e-tender",
      fairness_score: 17, concerns: 5, screened: 7, qualified: 1 },
    { id: 9, title: "My draft", kind: "draft", fairness_score: null, concerns: null, screened: null, qualified: null },
  ] });
  renderPage(<GovPage />);
  expect(await screen.findByRole("link", { name: "Classroom benches" })).toHaveAttribute("href", "/gov/tenders/4");
  expect(screen.getByText("Fairness 17/100")).toBeInTheDocument();
  expect(screen.getByText("1 of 7 businesses qualify")).toBeInTheDocument();
  expect(screen.getByText("Draft, not published")).toBeInTheDocument();
  expect(screen.getByText("Not checked")).toBeInTheDocument();
});

const INSIGHTS = {
  running: false, screened: 7, qualified: 1, msme_screened: 5, msme_qualified: 0,
  by_rule: [{ rule_text: "Turnover of Rs 2 crore", clause: "4.1", page: 1, must_have: true, pass: 2, fail: 5, missing: 0 }],
  businesses: [{ label: "Business A · Udyam MSE · Ernakulam", msme: true, outcome: "excluded", blocked_by: ["clause 4.1"] }],
};

it("shows fairness findings with fixes, and who each rule shuts out", async () => {
  mockApi({ "GET /gov/tenders/4": {
    tender: { id: 4, title: "Classroom benches", kind: "portal", buyer: "Kuttanad", portal: "Kerala e-tender", source_id: "KL/31" },
    fairness: { score: 83, concerns: 1, findings: [{ check_id: "emd_exemption", status: "concern", clause: "6", page: 2,
      title: "EMD exemption for registered micro and small enterprises", explanation: "No MSE exemption.",
      suggestion: "Exempt registered MSEs from EMD.", policy: "Public Procurement Policy for MSEs Order, 2012" }] },
    insights: INSIGHTS,
  } });
  renderPage(<GovTenderPage />, { path: "/gov/tenders/:id", route: "/gov/tenders/4" });
  expect(await screen.findByText("Works against small firms")).toBeInTheDocument();
  expect(screen.getByText("Exempt registered MSEs from EMD.")).toBeInTheDocument();
  expect(screen.getByText("1 of 7")).toBeInTheDocument();
  expect(screen.getByText("0 of 5")).toBeInTheDocument();
  expect(screen.getByText("Shut out by clause 4.1")).toBeInTheDocument();
});

it("starts the fairness check", async () => {
  const calls = mockApi({
    "GET /gov/tenders/9": { tender: { id: 9, title: "Draft", kind: "draft" }, fairness: null,
                            insights: { ...INSIGHTS, screened: 0, businesses: [], by_rule: [] } },
    "POST /gov/tenders/9/fairness": { score: 100, concerns: 0, findings: [] },
  });
  const user = userEvent.setup();
  renderPage(<GovTenderPage />, { path: "/gov/tenders/:id", route: "/gov/tenders/9" });
  await user.click(await screen.findByRole("button", { name: "Run fairness check" }));
  expect(calls.some((c) => c.method === "POST" && c.path === "/gov/tenders/9/fairness")).toBe(true);
});
