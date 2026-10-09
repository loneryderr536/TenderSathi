/** Small shared building blocks. */

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
