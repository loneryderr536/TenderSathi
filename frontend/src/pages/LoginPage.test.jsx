import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { getCompanyId, getToken, getUser } from "../api";
import { AuthProvider } from "../auth";
import { mockApi, renderPage } from "../test/utils";
import LoginPage from "./LoginPage";
import SignupPage from "./SignupPage";

const withAuth = (page) => <AuthProvider>{page}</AuthProvider>;

it("choosing a dashboard asks for that dashboard's login, empty, without logging in", async () => {
  localStorage.clear();
  const calls = mockApi({});
  const ui = userEvent.setup();
  renderPage(withAuth(<LoginPage />));
  await ui.click(screen.getByRole("button", { name: /Government dashboard/ }));
  expect(screen.getByText("Log in to the Government dashboard")).toBeInTheDocument();
  expect(screen.getByLabelText("Email")).toHaveValue("");
  expect(screen.getByLabelText("Password")).toHaveValue("");
  expect(calls).toEqual([]);
  expect(getToken()).toBeNull();
  await ui.click(screen.getByRole("button", { name: /Choose another dashboard/ }));
  expect(screen.getByText("Choose your dashboard")).toBeInTheDocument();
});

it("logs in with the chosen dashboard's role and remembers the business", async () => {
  localStorage.clear();
  const user = { id: 1, email: "owner@shop.in", name: "Owner", role: "business", company_id: 4, department: null };
  const calls = mockApi({ "POST /auth/login": { token: "t-1", user } });
  const ui = userEvent.setup();
  renderPage(withAuth(<LoginPage />));
  await ui.click(screen.getByRole("button", { name: /Business dashboard/ }));
  await ui.type(screen.getByLabelText("Email"), "owner@shop.in");
  await ui.type(screen.getByLabelText("Password"), "long-enough-1");
  await ui.click(screen.getByRole("button", { name: "Log in" }));
  await waitFor(() => expect(getToken()).toBe("t-1"));
  expect(JSON.parse(calls[0].init.body)).toEqual({ email: "owner@shop.in", password: "long-enough-1", role: "business" });
  expect(getUser().role).toBe("business");
  expect(getCompanyId()).toBe(4);
});

it("shows the backend's refusal when the account belongs to another dashboard", async () => {
  localStorage.clear();
  mockApi({ "POST /auth/login": { status: 403, body: { detail: "This is not a platform account. Choose the dashboard that matches your account." } } });
  const ui = userEvent.setup();
  renderPage(withAuth(<LoginPage />), { route: "/?as=platform" });
  expect(screen.getByText("Platform accounts are created by the TenderSathi team.")).toBeInTheDocument();
  await ui.type(screen.getByLabelText("Email"), "owner@shop.in");
  await ui.type(screen.getByLabelText("Password"), "long-enough-1");
  await ui.click(screen.getByRole("button", { name: "Log in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This is not a platform account");
  expect(getToken()).toBeNull();
});

it("signs up a government buyer with their department", async () => {
  localStorage.clear();
  const calls = mockApi({ "POST /auth/signup": { token: "t-2", user: { id: 2, role: "government", name: "Officer" } } });
  const ui = userEvent.setup();
  renderPage(withAuth(<SignupPage />), { route: "/?as=government" });
  expect(screen.getByLabelText(/Government buyer/)).toBeChecked();   // chosen on the login page
  await ui.clear(screen.getByLabelText("Department"));
  await ui.type(screen.getByLabelText("Department"), "Kuttanad Block Panchayat");
  await ui.click(screen.getByRole("button", { name: "Create account" }));
  await waitFor(() => expect(getToken()).toBe("t-2"));
  expect(JSON.parse(calls[0].init.body)).toMatchObject({ role: "government", department: "Kuttanad Block Panchayat" });
});

it("sign-up starts with dummy details filled in", () => {
  localStorage.clear();
  renderPage(withAuth(<SignupPage />));
  expect(screen.getByLabelText("Your name")).toHaveValue("Demo User");
  expect(screen.getByLabelText("Email").value).toMatch(/^demo\d{4}@tendersathi\.demo$/);
});
