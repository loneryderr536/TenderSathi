import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { request } from "../api";
import { HOME, useAuth } from "../auth";
import { DASHBOARDS, DEMO_PASSWORD } from "../dashboards";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

/** Step 1: choose a dashboard. */
function ChooseDashboard({ onChoose }) {
  return (
    <Card title="Choose your dashboard">
      <p className="mb-3 text-sm text-stone-600">Then log in with the account for that dashboard.</p>
      <div className="grid gap-3 sm:grid-cols-3">
        {DASHBOARDS.map((d) => (
          <button
            key={d.role}
            type="button"
            onClick={() => onChoose(d.role)}
            className="rounded-xl border border-stone-300 bg-white p-4 text-left hover:border-brand-600 hover:bg-brand-50"
          >
            <span className="block font-semibold text-brand-900">{d.label}</span>
            <span className="mt-0.5 block text-xs font-medium text-stone-700">{d.who}</span>
            <span className="mt-1 block text-xs text-stone-500">{d.hint}</span>
          </button>
        ))}
      </div>
      <p className="mt-4 text-sm text-stone-600">
        New here? <Link to="/signup" className="font-medium text-brand-700 underline">Create an account</Link>
      </p>
    </Card>
  );
}

/** Step 2: the email and password of an account that belongs to the chosen dashboard. */
function LoginForm({ dashboard, onBack }) {
  // Hackathon demo: the form starts with this dashboard's dummy account, so it logs in with one click.
  const [email, setEmail] = useState(dashboard.demoEmail);
  const [password, setPassword] = useState(DEMO_PASSWORD);
  const { logIn } = useAuth();
  const navigate = useNavigate();
  const login = useMutation({
    mutationFn: () => request("/auth/login", { method: "POST", json: { email, password, role: dashboard.role } }),
    onSuccess: (session) => {
      logIn(session);
      navigate(HOME[session.user.role], { replace: true });
    },
  });
  return (
    <Card title={`Log in to the ${dashboard.label}`}>
      <button type="button" onClick={onBack} className="mb-4 text-sm text-brand-700 hover:underline">
        ← Choose another dashboard
      </button>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); login.mutate(); }}>
        <Field label="Email">
          <input type="email" autoComplete="username" autoFocus className={inputClass} value={email}
                 onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password">
          <input type="password" autoComplete="current-password" className={inputClass} value={password}
                 onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <ErrorMessage error={login.error} />
        <Button type="submit" className="w-full" disabled={login.isPending}>{login.isPending ? "Logging in…" : "Log in"}</Button>
      </form>
      <p className="mt-4 text-sm text-stone-600">
        {dashboard.canSignUp ? (
          <>New here? <Link to={`/signup?as=${dashboard.role}`} className="font-medium text-brand-700 underline">Create an account</Link></>
        ) : (
          "Platform accounts are created by the TenderSathi team."
        )}
      </p>
    </Card>
  );
}

export default function LoginPage() {
  // The chosen dashboard lives in the address (/login?as=government), so a link can open its login directly.
  const [params, setParams] = useSearchParams();
  const dashboard = DASHBOARDS.find((d) => d.role === params.get("as"));
  return (
    <div className="mx-auto max-w-2xl">
      {dashboard ? (
        <div className="mx-auto max-w-md">
          <LoginForm key={dashboard.role} dashboard={dashboard} onBack={() => setParams({})} />
        </div>
      ) : (
        <ChooseDashboard onChoose={(role) => setParams({ as: role })} />
      )}
    </div>
  );
}
