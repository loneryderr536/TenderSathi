const AGENT_NAMES = {
  reader: "Reader", eligibility: "Eligibility", checklist: "Checklist", drafter: "Drafter",
  reviewer: "Reviewer", stop: "Stop", await_approval: "Ready for approval",
};

function tone(message) {
  if (message.startsWith("failed")) return "text-red-700";
  if (message.startsWith("error")) return "text-amber-700";
  if (message === "finished") return "text-brand-700";
  return "text-stone-600";
}

export default function AgentLog({ entries, running }) {
  if (!entries.length && !running) return null;
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
        Agent log
        {running && <span className="h-2 w-2 animate-pulse rounded-full bg-amber-500" aria-label="live" />}
      </h2>
      <ol className="space-y-1 font-mono text-xs" aria-live="polite">
        {entries.map((e, i) => (
          <li key={i} className="flex gap-3">
            <span className="w-32 shrink-0 font-semibold text-stone-800">{AGENT_NAMES[e.agent] || e.agent}</span>
            <span className={tone(e.message)}>{e.message}</span>
          </li>
        ))}
        {running && !entries.length && <li className="text-stone-500">Starting…</li>}
      </ol>
    </section>
  );
}
