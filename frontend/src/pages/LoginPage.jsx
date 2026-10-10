import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { HOME, useAuth } from "../auth";
import { DEMO_ACCOUNTS } from "../demoAccounts";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { logIn } = useAuth();
  const navigate = useNavigate();
  const login = useMutation({
    mutationFn: () => request("/auth/login", { method: "POST", json: { email, password } }),
    onSuccess: (session) => {
      logIn(session);
      navigate(HOME[session.user.role], { replace: true });
    },
  });
  return (
    <div className="mx-auto max-w-md space-y-4">
      <Card title="Log in to TenderSathi">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); login.mutate(); }}>
          <Field label="Email">
            <input type="email" autoComplete="username" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field label="Password">
            <input type="password" autoComplete="current-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <ErrorMessage error={login.error} />
          <Button type="submit" className="w-full" disabled={login.isPending}>{login.isPending ? "Logging in…" : "Log in"}</Button>
        </form>
        <p className="mt-4 text-sm text-stone-600">
          New here? <Link to="/signup" className="font-medium text-brand-700 underline">Create an account</Link>
        </p>
      </Card>
      <Card title="Try a demo account">
        <p className="mb-3 text-sm text-stone-600">Fills in the login for one of the three views.</p>
        <div className="grid gap-2 sm:grid-cols-3">
          {DEMO_ACCOUNTS.map((a) => (
            <Button key={a.role} type="button" variant="secondary" onClick={() => { setEmail(a.email); setPassword(a.password); }}>
              {a.label}
            </Button>
          ))}
        </div>
      </Card>
    </div>
  );
}
