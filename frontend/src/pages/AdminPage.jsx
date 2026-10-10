import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { getCompanyId, request } from "../api";
import { Button, Card, ErrorMessage, Stat } from "../components/ui";

const AGENT_LABEL = {
  scout: "Scout", reader: "Reader", tracker: "Tracker", eligibility: "Eligibility", checklist: "Checklist",
  drafter: "Drafter", reviewer: "Reviewer", stop: "Stop", await_approval: "Ready for approval",
};

function Counts({ title, counts }) {
  const entries = Object.entries(counts || {});
  return (
    <Card title={title}>
      {entries.length === 0 ? <p className="text-sm text-stone-500">Nothing yet.</p> : (
        <ul className="space-y-1 text-sm">
          {entries.map(([k, v]) => (
            <li key={k} className="flex justify-between"><span>{k.replaceAll("_", " ")}</span><span className="font-semibold">{v}</span></li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ScoutPanel({ runs, interval }) {
  const queryClient = useQueryClient();
  const sweep = useMutation({
    mutationFn: () => request("/scout/run", { method: "POST", json: { company_id: getCompanyId() } }),
    onSuccess: () => queryClient.invalidateQueries(),
  });
  return (
    <Card
      title="Scout agent"
      actions={<Button onClick={() => sweep.mutate()} disabled={sweep.isPending}>{sweep.isPending ? "Sweeping…" : "Sweep the portals now"}</Button>}
    >
      <p className="mb-3 text-sm text-stone-600">
        Watches GeM, CPPP and Kerala e-tender listings.{" "}
        {interval ? `Sweeps on its own every ${interval} seconds.` : "Automatic sweeps are off (set SCOUT_INTERVAL_SECONDS)."}
      </p>
      <ErrorMessage error={sweep.error} />
      {runs.length === 0 ? <p className="text-sm text-stone-500">No sweeps yet.</p> : (
        <ul className="divide-y divide-stone-200 text-sm">
          {runs.map((r) => (
            <li key={r.id} className="flex flex-wrap justify-between gap-2 py-2">
              <span>{r.message}</span>
              <span className="text-xs text-stone-500">{r.created_at} UTC</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function AdminPage() {
  const stats = useQuery({ queryKey: ["admin"], queryFn: () => request("/admin/stats"), refetchInterval: 3000 });
  if (!stats.data) return stats.error ? <ErrorMessage error={stats.error} /> : <p className="text-sm text-stone-500">Loading…</p>;
  const s = stats.data;
  const totalRuns = s.agents.find((a) => a.agent === "reader")?.runs ?? 0;
  const retries = s.agents.reduce((n, a) => n + a.retries, 0);
  const failures = s.agents.reduce((n, a) => n + a.failures, 0);
  const eligibility = s.accuracy.find((a) => a.agent === "eligibility");
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Platform health</h1>
        <p className="text-sm text-stone-600">What the agents are doing, how fast, how often they fail, and how often owners agree with them.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Tenders" value={s.tenders} hint={`${s.by_status.running || 0} being worked on`} />
        <Stat label="Businesses" value={s.businesses} hint={`${s.msme_businesses} Udyam MSEs`} />
        <Stat label="Agent runs" value={totalRuns} hint={`${retries} retries · ${failures} failures`} tone={failures ? "text-red-700" : "text-stone-900"} />
        <Stat label="Owner-checked accuracy" value={eligibility ? `${eligibility.accuracy}%` : "—"}
              hint={eligibility ? `eligibility, ${eligibility.judged} verdicts judged` : "owners mark verdicts right or wrong"} tone="text-brand-700" />
      </div>
      <ScoutPanel runs={s.scout_runs} interval={s.scout_interval_seconds} />
      <Card title="Agents">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr><th className="py-2 pr-3">Agent</th><th className="pr-3">Model</th><th className="pr-3">Runs</th><th className="pr-3">Avg time</th><th className="pr-3">Retries</th><th>Failures</th></tr>
            </thead>
            <tbody className="divide-y divide-stone-200">
              {s.agents.map((a) => (
                <tr key={a.agent}>
                  <td className="py-2 pr-3 font-medium">{AGENT_LABEL[a.agent] || a.agent}</td>
                  <td className="pr-3 font-mono text-xs">{a.model}</td>
                  <td className="pr-3">{a.runs}</td>
                  <td className="pr-3">{a.avg_seconds === null ? "—" : `${a.avg_seconds}s`}</td>
                  <td className={`pr-3 ${a.retries ? "text-amber-700" : ""}`}>{a.retries}</td>
                  <td className={a.failures ? "font-semibold text-red-700" : ""}>{a.failures}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {s.agents.length === 0 && <p className="py-2 text-sm text-stone-500">No agent has run yet.</p>}
        </div>
      </Card>
      <Card title="Recent runs">
        {s.runs.length === 0 ? <p className="text-sm text-stone-500">No runs yet.</p> : (
          <ul className="divide-y divide-stone-200 text-sm">
            {s.runs.map((r) => (
              <li key={r.run_id} className="flex flex-wrap justify-between gap-2 py-2">
                <Link to={`/tenders/${r.tender_id}`} className="text-brand-700 hover:underline">{r.title}</Link>
                <span className={`text-xs ${r.failed ? "font-semibold text-red-700" : "text-stone-600"}`}>
                  {r.last.replace("await_approval", "ready for approval")} · {Math.round(r.seconds)}s
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <div className="grid gap-6 sm:grid-cols-2">
        <Counts title="Tenders by source" counts={s.by_source} />
        <Counts title="Tenders by status" counts={s.by_status} />
      </div>
    </div>
  );
}
