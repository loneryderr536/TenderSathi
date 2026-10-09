import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { clearCompanyId, getCompanyId, isCompanyGone, pollInterval, request } from "../api";
import AgentLog from "../components/AgentLog";
import Tabs from "../components/Tabs";
import { Button, Countdown, ErrorMessage, Field, StatusBadge, VerdictBadge, inputClass } from "../components/ui";

const Empty = ({ children }) => <p className="text-sm text-stone-500">{children}</p>;

function Summary({ tender, facts }) {
  const rows = [["Deadline", tender.deadline], ["EMD (deposit)", tender.emd], ["Payment terms", tender.payment_terms]];
  return (
    <div className="space-y-4">
      <dl className="grid gap-3 sm:grid-cols-3">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg bg-stone-50 p-3">
            <dt className="text-xs text-stone-500">{label}</dt>
            <dd className="font-medium">{value || "—"}</dd>
          </div>
        ))}
      </dl>
      {facts ? (
        <>
          <h3 className="text-sm font-semibold">Key rules</h3>
          <ul className="space-y-1 text-sm">
            {facts.rules.map((r) => (
              <li key={r.text}>
                {r.text} <span className="text-xs text-stone-500">(clause {r.clause}, page {r.page}{r.must_have ? ", mandatory" : ""})</span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <Empty>Run the agents to read this tender.</Empty>
      )}
    </div>
  );
}

function Eligibility({ verdicts }) {
  if (!verdicts) return <Empty>No eligibility check yet.</Empty>;
  return (
    <ul className="divide-y divide-stone-200">
      {verdicts.verdicts.map((v) => (
        <li key={v.rule_text} className="flex flex-wrap items-start gap-3 py-3">
          <VerdictBadge verdict={v.verdict} />
          <div className="min-w-0 flex-1">
            <p className="font-medium">{v.rule_text}{v.must_have && <span className="ml-2 text-xs text-red-700">must-have</span>}</p>
            <p className="text-sm text-stone-600">{v.reason}</p>
            <p className="text-xs text-stone-500">Clause {v.clause}, page {v.page}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function Checklist({ checklist }) {
  if (!checklist) return <Empty>No checklist yet.</Empty>;
  return (
    <ul className="divide-y divide-stone-200">
      {checklist.items.map((i) => (
        <li key={i.document} className="flex flex-wrap items-center justify-between gap-2 py-3">
          <span className="font-medium">{i.document}</span>
          {i.status === "have" ? (
            <span className="text-sm text-brand-700">You have it ({i.matched_file})</span>
          ) : (
            <span className="text-sm font-medium text-amber-700">You still need it</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function Draft({ draft }) {
  if (!draft) return <Empty>No draft. A draft is written only when the business qualifies.</Empty>;
  return (
    <article className="space-y-4 text-sm leading-relaxed">
      <section>
        <h3 className="mb-1 font-semibold">Cover letter</h3>
        <p className="whitespace-pre-wrap">{draft.cover_letter}</p>
      </section>
      {draft.sections.map((s) => (
        <section key={s.title}>
          <h3 className="mb-1 font-semibold">{s.title}</h3>
          <p className="whitespace-pre-wrap">{s.body}</p>
        </section>
      ))}
    </article>
  );
}

function Compliance({ review }) {
  if (!review) return <Empty>No compliance check yet.</Empty>;
  return (
    <div className="space-y-3">
      {review.gaps.length > 0 && (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          Not yet answered in the draft: {review.gaps.join("; ")}
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-stone-500">
            <tr><th className="py-2 pr-3">Rule</th><th className="pr-3">Mandatory</th><th className="pr-3">Covered</th><th>Where</th></tr>
          </thead>
          <tbody className="divide-y divide-stone-200">
            {review.matrix.map((r) => (
              <tr key={r.rule_text}>
                <td className="py-2 pr-3">{r.rule_text}</td>
                <td className="pr-3">{r.must_have ? "Yes" : "No"}</td>
                <td className={`pr-3 font-medium ${r.covered ? "text-brand-700" : "text-red-700"}`}>{r.covered ? "Yes" : "No"}</td>
                <td>{r.where || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RunControls({ id, status }) {
  const [companyId, setCompanyIdState] = useState(getCompanyId);
  const queryClient = useQueryClient();
  const run = useMutation({
    mutationFn: () => request(`/tenders/${id}/run`, { method: "POST", json: { company_id: companyId } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tender", id] }),
    onError: (error) => {
      if (isCompanyGone(error)) {
        clearCompanyId();
        setCompanyIdState(null);
      }
    },
  });
  const running = status === "running";
  const label = running || run.isPending ? "Agents working…" : status === "new" ? "Run the agents" : "Run again";
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button onClick={() => run.mutate()} disabled={!companyId || running || run.isPending || status === "approved"}>
        {label}
      </Button>
      {!companyId && (
        <Link to="/profile" className="text-sm text-brand-700 underline">Fill in your business profile</Link>
      )}
      {status === "awaiting_approval" && (
        <Link to={`/tenders/${id}/approve`} className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
          Review & approve the bid
        </Link>
      )}
      {status === "approved" && (
        <Link to={`/tenders/${id}/approve`} className="text-sm text-brand-700 underline">Download the bid pack</Link>
      )}
      <ErrorMessage error={run.error} />
    </div>
  );
}

const TAB_NAMES = ["summary", "eligibility", "checklist", "draft", "compliance"];

function ChangesBanner({ changes, status }) {
  if (!changes) return null;
  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
      <h2 className="mb-2 font-semibold">This tender was changed (corrigendum)</h2>
      {changes.changes.length === 0 ? (
        <p>No changes that matter to your bid were found.</p>
      ) : (
        <ul className="space-y-2">
          {changes.changes.map((c, i) => (
            <li key={i}>
              <p>{c.summary}</p>
              <p className="text-xs text-amber-800">{`${c.before} → ${c.after}`}</p>
            </li>
          ))}
        </ul>
      )}
      {changes.affects_eligibility && (
        <p className="mt-2 font-medium">Eligibility rules changed: check the eligibility report again.</p>
      )}
      {status === "changed" && <p className="mt-2">Run the agents again to update your bid for the new version.</p>}
    </section>
  );
}

function CorrigendumForm({ id }) {
  const [file, setFile] = useState(null);
  const queryClient = useQueryClient();
  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("file", file);
      return request(`/tenders/${id}/corrigendum`, { method: "POST", form });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tender", id] }),
  });
  return (
    <form
      className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-white p-4 shadow-sm"
      onSubmit={(e) => {
        e.preventDefault();
        upload.mutate();
      }}
    >
      <div className="min-w-60 flex-1">
        <Field label="Changed tender PDF (corrigendum)">
          <input type="file" accept="application/pdf,.pdf" className={inputClass}
                 onChange={(e) => setFile(e.target.files[0] || null)} />
        </Field>
      </div>
      <Button type="submit" variant="secondary" disabled={!file || upload.isPending}>
        {upload.isPending ? "Comparing…" : "Check what changed"}
      </Button>
      <div className="w-full"><ErrorMessage error={upload.error} /></div>
    </form>
  );
}

export default function TenderPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const initialTab = Math.max(0, TAB_NAMES.indexOf(params.get("tab")));   // ?tab=checklist opens that tab
  const queryClient = useQueryClient();
  const result = useQuery({
    queryKey: ["tender", id, "result"],
    queryFn: () => request(`/tenders/${id}/result`),
    refetchInterval: (query) => pollInterval(query.state.data?.tender.status),
  });
  const status = result.data?.tender.status;
  const log = useQuery({
    queryKey: ["tender", id, "log"],
    queryFn: () => request(`/tenders/${id}/log`),
    refetchInterval: pollInterval(status),
  });
  // One last log fetch when a run ends, so the final lines show.
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: ["tender", id, "log"] });
  }, [status, id, queryClient]);

  if (!result.data) {
    return result.error ? <ErrorMessage error={result.error} /> : <p className="text-sm text-stone-500">Loading…</p>;
  }
  const { tender, facts, verdicts, checklist, draft, review, changes } = result.data;

  return (
    <div className="space-y-6">
      <ErrorMessage error={result.error} />
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{tender.title}</h1>
          <StatusBadge status={tender.status} />
          <Countdown deadlineAt={tender.deadline_at} />
        </div>
        {tender.reason && (
          <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {tender.reason}
          </p>
        )}
        <RunControls id={id} status={tender.status} />
      </div>
      <ChangesBanner changes={changes} status={tender.status} />
      <AgentLog entries={log.data || []} running={tender.status === "running"} />
      <Tabs
        key={id}
        initial={initialTab}
        tabs={[
          { label: "Summary", content: <Summary tender={tender} facts={facts} /> },
          { label: "Eligibility", content: <Eligibility verdicts={verdicts} /> },
          { label: "Checklist", content: <Checklist checklist={checklist} /> },
          { label: "Draft", content: <Draft draft={draft} /> },
          { label: "Compliance", content: <Compliance review={review} /> },
        ]}
      />
      {facts && tender.status !== "running" && <CorrigendumForm id={id} />}
    </div>
  );
}
