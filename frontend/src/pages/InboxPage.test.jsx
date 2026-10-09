import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { mockApi, renderPage } from "../test/utils";
import InboxPage from "./InboxPage";

const TENDERS = [
  { id: 2, title: "School desks", deadline: "2026-10-30", emd: "₹50,000", status: "awaiting_approval", reason: null },
  { id: 1, title: "Hospital beds", deadline: null, emd: null, status: "new", reason: null },
];

it("lists tenders with status and links", async () => {
  mockApi({ "GET /tenders": TENDERS });
  renderPage(<InboxPage />);
  const link = await screen.findByRole("link", { name: "School desks" });
  expect(link).toHaveAttribute("href", "/tenders/2");
  expect(screen.getByText("Ready for review")).toBeInTheDocument();
  expect(screen.getByText("₹50,000")).toBeInTheDocument();
});

it("shows an empty state", async () => {
  mockApi({ "GET /tenders": [] });
  renderPage(<InboxPage />);
  expect(await screen.findByText(/No tenders yet/)).toBeInTheDocument();
});

it("uploads a PDF and shows the server's rejection message", async () => {
  const calls = mockApi({
    "GET /tenders": [],
    "POST /tenders": { status: 400, body: { detail: "This looks like a scanned PDF; please use a text PDF" } },
  });
  const user = userEvent.setup();
  renderPage(<InboxPage />);
  const file = new File(["%PDF"], "scan.pdf", { type: "application/pdf" });
  await user.upload(screen.getByLabelText("Tender PDF"), file);
  await user.click(screen.getByRole("button", { name: "Upload" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This looks like a scanned PDF; please use a text PDF");
  const post = calls.find((c) => c.method === "POST");
  expect(post.init.body.get("file").name).toBe("scan.pdf");
});

it("shows an error when the backend is down", async () => {
  mockApi({ "GET /tenders": { status: 500, body: { detail: "Internal Server Error" } } });
  renderPage(<InboxPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Internal Server Error");
});

it("shows days left and lists the nearest deadline first", async () => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 9, 11, 0));
  mockApi({ "GET /tenders": [
    { id: 1, title: "Later tender", deadline: "6 Nov", deadline_at: "2026-11-06T14:00:00", emd: null, status: "new" },
    { id: 2, title: "Urgent tender", deadline: "12 Oct", deadline_at: "2026-10-12T09:00:00", emd: null, status: "awaiting_approval" },
    { id: 3, title: "Changed tender", deadline: null, deadline_at: null, emd: null, status: "changed" },
  ] });
  renderPage(<InboxPage />);
  const links = await screen.findAllByRole("link");
  expect(links.map((l) => l.textContent)).toEqual(["Urgent tender", "Later tender", "Changed tender"]);
  expect(screen.getByText("3 days left")).toHaveClass("text-red-700");
  expect(screen.getByText("28 days left")).toBeInTheDocument();
  expect(screen.getByText("Tender changed")).toBeInTheDocument();
  vi.useRealTimers();
});
