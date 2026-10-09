import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { result } from "../test/samples";
import { mockApi, renderPage } from "../test/utils";
import ApprovePage from "./ApprovePage";

const show = () => renderPage(<ApprovePage />, { path: "/tenders/:id/approve", route: "/tenders/5/approve" });

it("approves with the owner's edits, then offers the export", async () => {
  let status = "awaiting_approval";
  const calls = mockApi({
    "GET /tenders/5/result": () => result({ tender: { status } }),
    "POST /tenders/5/approve": () => { status = "approved"; return { status: "approved" }; },
  });
  const user = userEvent.setup();
  show();
  const letter = await screen.findByLabelText("Cover letter");
  await user.clear(letter);
  await user.type(letter, "Respected Sir, [[PRICE: ₹4.2 lakh]");
  await user.clear(screen.getByLabelText("Experience"));
  await user.type(screen.getByLabelText("Experience"), "250 desks");
  await user.click(screen.getByRole("button", { name: "Approve bid" }));

  const link = await screen.findByRole("link", { name: "Download bid pack" });
  expect(link).toHaveAttribute("href", "http://localhost:8000/tenders/5/export");
  expect(JSON.parse(calls.find((c) => c.method === "POST").init.body)).toEqual({
    cover_letter: "Respected Sir, [PRICE: ₹4.2 lakh]",
    sections: [{ title: "Experience", body: "250 desks" }],
  });
});

it("shows the server's message when approval is refused", async () => {
  mockApi({
    "GET /tenders/5/result": result(),
    "POST /tenders/5/approve": { status: 400, body: { detail: "Cover letter cannot be empty" } },
  });
  const user = userEvent.setup();
  show();
  await user.clear(await screen.findByLabelText("Cover letter"));
  await user.click(screen.getByRole("button", { name: "Approve bid" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Cover letter cannot be empty");
  expect(screen.queryByRole("link", { name: "Download bid pack" })).toBeNull();
});

it("reminds the owner to add the price and submit themselves", async () => {
  mockApi({ "GET /tenders/5/result": result() });
  show();
  expect(await screen.findByText(/add your price/i)).toBeInTheDocument();
  expect(screen.getByText(/submit it yourself on the government portal/i)).toBeInTheDocument();
});

it("says when the bid is not ready yet", async () => {
  mockApi({ "GET /tenders/5/result": result({ tender: { status: "running" }, draft: null }) });
  show();
  await waitFor(() => expect(screen.getByText(/not ready for approval/i)).toBeInTheDocument());
  expect(screen.queryByRole("button", { name: "Approve bid" })).toBeNull();
});
