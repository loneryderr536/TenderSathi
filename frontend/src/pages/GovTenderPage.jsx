import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { request } from "../api";
import { Button, Card, ErrorMessage, Stat } from "../components/ui";
import { FairnessBadge } from "./GovPage";

const STATUS = {
  ok: ["Meets policy", "bg-brand-100 text-brand-700"],
  concern: ["Works against small firms", "bg-red-100 text-red-800"],
  not_found: ["Not stated", "bg-stone-100 text-stone-700"],
};

function Fairness({ id, report }) {
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: () => request(`/gov/tenders/${id}/fairness`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gov"] }),
  });
  return (
    <Card
      title="Fairness check"
      actions={
        <Button onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? "Fairness agent reading…" : report ? "Check again" : "Run fairness check"}
        </Button>
      }
    >
      <ErrorMessage error={run.error} />
      {!report && !run.isPending && (
        <p className="text-sm text-stone-500">
          Checks EMD exemption, tender fees, turnover and experience demands, brand-locked specifications, and time to
          bid, against small-business procurement policy. Each check reads only the clauses the memory finds for it.
        </p>
      )}
      {report && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <FairnessBadge score={report.score} />
            <span className="text-sm text-stone-600">{report.concerns} of {report.findings.length} checks need a change</span>
          </div>
          <ul className="space-y-3">
            {[...report.findings].sort((a, b) => (a.status === "concern" ? -1 : 0) - (b.status === "concern" ? -1 : 0)).map((f) => {
              const [label, style] = STATUS[f.status] || STATUS.not_found;
              return (
                <li key={f.check_id} className="rounded-lg border border-stone-200 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}>{label}</span>
                    <span className="font-medium">{f.title}</span>
                    {f.clause && <span className="text-xs text-stone-500">clause {f.clause}, page {f.page}</span>}
                  </div>
                  <p className="mt-1 text-stone-700">{f.explanation}</p>
                  {f.suggestion && (
                    <p className="mt-2 rounded bg-brand-50 p-2 text-brand-900"><span className="font-semibold">Suggested fix: </span>{f.suggestion}</p>
                  )}
                  <p className="mt-1 text-xs text-stone-500">Policy: {f.policy}</p>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Card>
  );
}

function Participation({ id, insights }) {
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: () => request(`/gov/tenders/${id}/screen`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["gov", "tender", id] }),
  });
  const busy = insights.running || run.isPending;
  return (
    <Card
      title="Who can bid?"
      actions={
        <Button variant="secondary" onClick={() => run.mutate()} disabled={busy}>
          {busy ? "Screening businesses…" : insights.screened ? "Screen again" : "Screen registered businesses"}
        </Button>
      }
    >
      <ErrorMessage error={run.error} />
      {!insights.screened && !busy && (
        <p className="text-sm text-stone-500">
          The Eligibility agent checks every business registered on TenderSathi against this tender's rules, and shows
          which rule shuts out how many. Only totals and anonymous labels are shown.
        </p>
      )}
      {insights.screened > 0 && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Stat label="Businesses that qualify" value={`${insights.qualified} of ${insights.screened}`} tone="text-brand-700" />
            <Stat label="Micro & small enterprises" value={`${insights.msme_qualified} of ${insights.msme_screened}`} hint="qualify" />
            <Stat label="Shut out" value={insights.screened - insights.qualified} tone={insights.screened - insights.qualified ? "text-red-700" : "text-stone-900"} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Which rule shuts businesses out</h3>
            <ul className="space-y-2">
              {insights.by_rule.map((r) => {
                const total = r.pass + r.fail + r.missing || 1;
                return (
                  <li key={r.rule_text} className="text-sm">
                    <div className="flex flex-wrap justify-between gap-2">
                      <span>{r.rule_text} <span className="text-xs text-stone-500">(clause {r.clause}{r.must_have ? ", mandatory" : ""})</span></span>
                      <span className="text-xs font-medium text-red-700">{r.fail} fail</span>
                    </div>
                    <div className="mt-1 flex h-2 overflow-hidden rounded-full bg-stone-100" aria-hidden="true">
                      <div className="bg-brand-600" style={{ width: `${(100 * r.pass) / total}%` }} />
                      <div className="bg-amber-400" style={{ width: `${(100 * r.missing) / total}%` }} />
                      <div className="bg-red-600" style={{ width: `${(100 * r.fail) / total}%` }} />
                    </div>
                  </li>
                );
              })}
            </ul>
            <p className="mt-2 text-xs text-stone-500">Green: meets the rule · amber: can't tell from the profile · red: fails.</p>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold">Businesses screened</h3>
            <ul className="divide-y divide-stone-200 text-sm">
              {insights.businesses.map((b) => (
                <li key={b.label} className="flex flex-wrap justify-between gap-2 py-2">
                  <span>{b.label}</span>
                  <span className={b.outcome === "qualifies" ? "text-brand-700" : "text-red-700"}>
                    {b.outcome === "qualifies" ? "Qualifies" : `Shut out by ${b.blocked_by.join(", ")}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </Card>
  );
}

export default function GovTenderPage() {
  const { id } = useParams();
  const data = useQuery({
    queryKey: ["gov", "tender", id],
    queryFn: () => request(`/gov/tenders/${id}`),
    refetchInterval: (query) => (query.state.data?.insights.running ? 2000 : false),
  });
  if (!data.data) return data.error ? <ErrorMessage error={data.error} /> : <p className="text-sm text-stone-500">Loading…</p>;
  const { tender, fairness, insights } = data.data;
  return (
    <div className="space-y-6">
      <div>
        <Link to="/gov" className="text-sm text-brand-700 hover:underline">← Buyer dashboard</Link>
        <h1 className="mt-1 text-2xl font-semibold">{tender.title}</h1>
        <p className="text-sm text-stone-600">
          {tender.kind === "draft" ? "Draft, not published yet" : `${tender.buyer} · ${tender.portal} (${tender.source_id})`}
        </p>
      </div>
      <Fairness id={id} report={fairness} />
      <Participation id={id} insights={insights} />
    </div>
  );
}
