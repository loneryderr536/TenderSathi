import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { getCompanyId, getToken, getUser } from "../api";
import { AuthProvider } from "../auth";
import { mockApi, renderPage } from "../test/utils";
import LoginPage from "./LoginPage";
import SignupPage from "./SignupPage";

const withAuth = (page) => <AuthProvider>{page}</AuthProvider>;

it("logs in with a demo account and remembers the session and the business", async () => {
  localStorage.clear();
  const user = { id: 1, email: "owner@tendersathi.demo", name: "Owner", role: "business", company_id: 4, department: null };
  const calls = mockApi({ "POST /auth/login": { token: "t-1", user } });
  const ui = userEvent.setup();
  renderPage(withAuth(<LoginPage />));
  await ui.click(screen.getByRole("button", { name: "Business owner" }));
  await ui.click(screen.getByRole("button", { name: "Log in" }));
  await waitFor(() => expect(getToken()).toBe("t-1"));
  expect(JSON.parse(calls[0].init.body).email).toBe("owner@tendersathi.demo");
  expect(getToken()).toBe("t-1");
  expect(getUser().role).toBe("business");
  expect(getCompanyId()).toBe(4);
});

it("shows a wrong-password message", async () => {
  localStorage.clear();
  mockApi({ "POST /auth/login": { status: 401, body: { detail: "Wrong email or password" } } });
  const ui = userEvent.setup();
  renderPage(withAuth(<LoginPage />));
  await ui.type(screen.getByLabelText("Email"), "a@b.in");
  await ui.type(screen.getByLabelText("Password"), "nope-nope");
  await ui.click(screen.getByRole("button", { name: "Log in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password");
  expect(getToken()).toBeNull();
});

it("signs up a government buyer with their department", async () => {
  localStorage.clear();
  const calls = mockApi({ "POST /auth/signup": { token: "t-2", user: { id: 2, role: "government", name: "Officer" } } });
  const ui = userEvent.setup();
  renderPage(withAuth(<SignupPage />));
  await ui.click(screen.getByLabelText(/Government buyer/));
  await ui.type(screen.getByLabelText("Your name"), "Officer");
  await ui.type(screen.getByLabelText("Department"), "Kuttanad Block Panchayat");
  await ui.type(screen.getByLabelText("Email"), "officer@gov.in");
  await ui.type(screen.getByLabelText(/Password/), "long-enough-1");
  await ui.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() => expect(getToken()).toBe("t-2"));
  expect(JSON.parse(calls[0].init.body)).toMatchObject({ role: "government", department: "Kuttanad Block Panchayat" });
});
