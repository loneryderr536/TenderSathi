/** Small shared building blocks. */
import { countdown } from "../deadline";

export function Card({ title, children, actions }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm sm:p-6">
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-lg font-semibold">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Button({ variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-stone-300",
    secondary: "border border-stone-300 bg-white text-stone-800 hover:bg-stone-100 disabled:text-stone-400",
  };
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed ${styles[variant]} ${className}`}
      {...props}
    />
  );
}

export function ErrorMessage({ error }) {
  if (!error) return null;
  return (
    <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
      {error.message || String(error)}
    </p>
  );
}

export function Field({ label, children }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-stone-700">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-brand-600 focus:ring-2 focus:ring-brand-100 focus:outline-none";

const STATUS = {
  new: ["New", "bg-stone-100 text-stone-700"],
  running: ["Agents working", "bg-amber-100 text-amber-800"],
  stopped: ["Not eligible", "bg-red-100 text-red-800"],
  failed: ["Failed", "bg-red-100 text-red-800"],
  awaiting_approval: ["Ready for review", "bg-sky-100 text-sky-800"],
  approved: ["Approved", "bg-brand-100 text-brand-700"],
  changed: ["Tender changed", "bg-amber-100 text-amber-800"],
  awarded: ["Awarded", "bg-brand-100 text-brand-700"],
};

export function StatusBadge({ status }) {
  const [label, style] = STATUS[status] || [status, "bg-stone-100 text-stone-700"];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>{label}</span>;
}

const VERDICT = {
  pass: ["Pass", "bg-brand-100 text-brand-700"],
  fail: ["Fail", "bg-red-100 text-red-800"],
  missing: ["Missing", "bg-amber-100 text-amber-800"],
};

export function VerdictBadge({ verdict }) {
  const [label, style] = VERDICT[verdict] || [verdict, "bg-stone-100"];
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}>{label}</span>;
}

/** "21 days left" / "Due today" / "Deadline passed"; red when due within 3 days. */
export function Countdown({ deadlineAt }) {
  const c = countdown(deadlineAt);
  if (!c) return null;
  const style = c.urgent ? "font-semibold text-red-700" : c.passed ? "text-stone-500" : "text-stone-600";
  return <span className={`text-xs ${style}`}>{c.label}</span>;
}

const DECISION = {
  bid: ["Bid", "bg-brand-100 text-brand-700"],
  bid_with_care: ["Bid with care", "bg-amber-100 text-amber-800"],
  no_bid: ["No-bid", "bg-red-100 text-red-800"],
};

/** The bid / no-bid score: "82 · Bid". */
export function ScoreBadge({ score }) {
  if (!score) return null;
  const [label, style] = DECISION[score.decision] || [score.decision, "bg-stone-100"];
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`} title={score.reasons.join("\n")}>
      {score.score} · {label}
    </span>
  );
}

/** A number tile for the dashboards. */
export function Stat({ label, value, hint, tone = "text-stone-900" }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium text-stone-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${tone}`}>{value ?? "—"}</p>
      {hint && <p className="mt-0.5 text-xs text-stone-500">{hint}</p>}
    </div>
  );
}
