import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { HOME, useAuth } from "../auth";
import { DEMO_ACCOUNTS } from "../demoAccounts";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

export default function LoginPage() {
  // Pre-filled with the business demo login for the hackathon demo.
  const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
  const [password, setPassword] = useState(DEMO_ACCOUNTS[0].password);
  const { logIn } = useAuth();
  const navigate = useNavigate();
  const login = useMutation({
    mutationFn: (credentials) => request("/auth/login", { method: "POST", json: credentials }),
    onSuccess: (session) => {
      logIn(session);
      navigate(HOME[session.user.role], { replace: true });
    },
  });
  const opening = login.isPending ? login.variables?.email : null;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card title="Choose a dashboard">
        <p className="mb-3 text-sm text-stone-600">Opens the dashboard straight away with its demo account.</p>
        <div className="grid gap-3 sm:grid-cols-3">
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.role}
              type="button"
              disabled={login.isPending}
              onClick={() => login.mutate({ email: a.email, password: a.password })}
              className="rounded-xl border border-stone-300 bg-white p-4 text-left hover:border-brand-600 hover:bg-brand-50 disabled:cursor-wait disabled:opacity-60"
            >
              <span className="block font-semibold text-brand-900">{opening === a.email ? "Opening…" : a.label}</span>
              <span className="mt-0.5 block text-xs font-medium text-stone-700">{a.who}</span>
              <span className="mt-1 block text-xs text-stone-500">{a.hint}</span>
            </button>
          ))}
        </div>
        <div className="mt-3"><ErrorMessage error={login.error} /></div>
      </Card>

      <Card title="Or log in with your account">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); login.mutate({ email, password }); }}>
          <Field label="Email">
            <input type="email" autoComplete="username" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Password">
            <input type="password" autoComplete="current-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <Button type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending && opening === email ? "Logging in…" : "Log in"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-stone-600">
          New here? <Link to="/signup" className="font-medium text-brand-700 underline">Create an account</Link>
        </p>
      </Card>
    </div>
  );
}
