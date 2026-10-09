import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { getCompanyId, setCompanyId } from "../api";
import { mockApi, renderPage } from "../test/utils";
import ProfilePage from "./ProfilePage";

it("saves a new profile and remembers its id", async () => {
  const calls = mockApi({ "POST /companies": { id: 4 } });
  const user = userEvent.setup();
  renderPage(<ProfilePage />);

  await user.type(screen.getByLabelText("Business name"), "Ernakulam Woodworks");
  await user.type(screen.getByLabelText("What you make or do"), "desks, tables");
  await user.type(screen.getByLabelText("Location"), "Ernakulam");
  await user.type(screen.getByLabelText("Yearly turnover"), "₹1.4 crore");
  await user.click(screen.getByLabelText("Udyam / MSE registered"));
  await user.type(screen.getByLabelText("Documents you hold (one per line)"), "gst.pdf\npan.pdf");
  await user.click(screen.getByRole("button", { name: "Add past order" }));
  await user.type(screen.getByLabelText("Buyer"), "KSEB");
  await user.type(screen.getByLabelText("Item"), "desks");
  await user.type(screen.getByLabelText("Value"), "₹8 lakh");
  await user.type(screen.getByLabelText("Year"), "2025");
  await user.click(screen.getByRole("button", { name: "Save profile" }));

  await screen.findByText("Profile saved");
  expect(JSON.parse(calls.findLast((c) => c.method === "POST").init.body)).toEqual({
    name: "Ernakulam Woodworks", products: "desks, tables", location: "Ernakulam", turnover: "₹1.4 crore",
    udyam: true, documents: ["gst.pdf", "pan.pdf"],
    past_orders: [{ buyer: "KSEB", item: "desks", value: "₹8 lakh", year: 2025 }],
  });
  expect(getCompanyId()).toBe(4);
});

it("loads the saved profile and updates it by id", async () => {
  setCompanyId(4);
  const calls = mockApi({
    "GET /companies/4": { id: 4, name: "Woodworks", products: "desks", location: "Kochi", turnover: "₹1 crore",
                          udyam: false, documents: ["gst.pdf"], past_orders: [] },
    "POST /companies": { id: 4 },
  });
  const user = userEvent.setup();
  renderPage(<ProfilePage />);
  await waitFor(() => expect(screen.getByLabelText("Business name")).toHaveValue("Woodworks"));
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  await screen.findByText("Profile saved");
  expect(JSON.parse(calls.findLast((c) => c.method === "POST").init.body)).toMatchObject({ id: 4, name: "Woodworks", documents: ["gst.pdf"] });
});

it("shows the server's error", async () => {
  mockApi({ "POST /companies": { status: 422, body: { detail: "Something is wrong" } } });
  const user = userEvent.setup();
  renderPage(<ProfilePage />);
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Something is wrong");
});

it("forgets a saved id the server no longer knows, and saves as new", async () => {
  setCompanyId(9);
  const calls = mockApi({
    "GET /companies/9": { status: 404, body: { detail: "Company not found" } },
    "POST /companies": (init) => (JSON.parse(init.body).id ? { status: 404, body: { detail: "Company not found" } } : { id: 1 }),
  });
  const user = userEvent.setup();
  renderPage(<ProfilePage />);
  await waitFor(() => expect(getCompanyId()).toBeNull());
  expect(screen.queryByRole("alert")).toBeNull();
  await user.type(screen.getByLabelText("Business name"), "Woodworks");
  await user.click(screen.getByRole("button", { name: "Save profile" }));
  await screen.findByText("Profile saved");
  expect(JSON.parse(calls.findLast((c) => c.method === "POST").init.body).id).toBeUndefined();
  expect(getCompanyId()).toBe(1);
});
