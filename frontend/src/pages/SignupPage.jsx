import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { useAuth } from "../auth";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

const ROLE_CHOICES = [
  { value: "business", label: "Small business owner", hint: "Find tenders and prepare bids" },
  { value: "government", label: "Government buyer", hint: "Check tenders for fairness and see who can bid" },
];

export default function SignupPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "business", department: "" });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const { logIn } = useAuth();
  const navigate = useNavigate();
  const signup = useMutation({
    mutationFn: () => request("/auth/signup", { method: "POST", json: form }),
    onSuccess: (session) => {
      logIn(session);
      // A new business owner fills in their profile first; the agents need it.
      navigate(session.user.role === "business" ? "/profile" : "/gov", { replace: true });
    },
  });
  return (
    <div className="mx-auto max-w-md">
      <Card title="Create your TenderSathi account">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); signup.mutate(); }}>
          <fieldset className="space-y-2">
            <legend className="mb-1 text-sm font-medium text-stone-700">I am a</legend>
            {ROLE_CHOICES.map((r) => (
              <label key={r.value} className={`flex cursor-pointer gap-3 rounded-lg border p-3 text-sm ${form.role === r.value ? "border-brand-600 bg-brand-50" : "border-stone-300"}`}>
                <input type="radio" name="role" value={r.value} checked={form.role === r.value} onChange={set("role")} />
                <span><span className="block font-medium">{r.label}</span><span className="text-stone-600">{r.hint}</span></span>
              </label>
            ))}
          </fieldset>
          <Field label="Your name"><input className={inputClass} value={form.name} onChange={set("name")} required /></Field>
          {form.role === "government" && (
            <Field label="Department"><input className={inputClass} value={form.department} onChange={set("department")} placeholder="e.g. Kuttanad Block Panchayat" required /></Field>
          )}
          <Field label="Email"><input type="email" autoComplete="username" className={inputClass} value={form.email} onChange={set("email")} required /></Field>
          <Field label="Password (at least 8 characters)">
            <input type="password" autoComplete="new-password" minLength={8} className={inputClass} value={form.password} onChange={set("password")} required />
          </Field>
          <ErrorMessage error={signup.error} />
          <Button type="submit" className="w-full" disabled={signup.isPending}>{signup.isPending ? "Creating…" : "Create account"}</Button>
        </form>
        <p className="mt-4 text-sm text-stone-600">
          Already have an account? <Link to="/login" className="font-medium text-brand-700 underline">Log in</Link>
        </p>
      </Card>
    </div>
  );
}
