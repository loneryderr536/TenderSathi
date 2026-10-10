import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { Button, Card, ErrorMessage, Field, Stat, inputClass } from "../components/ui";

export function FairnessBadge({ score }) {
  if (score === null || score === undefined) return <span className="text-xs text-stone-500">Not checked</span>;
  const style = score >= 80 ? "bg-brand-100 text-brand-700" : score >= 50 ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800";
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}>Fairness {score}/100</span>;
}

function DraftUpload() {
  const [file, setFile] = useState(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("file", file);
      return request("/gov/drafts", { method: "POST", form });
    },
    onSuccess: ({ id }) => {
      queryClient.invalidateQueries({ queryKey: ["gov"] });
      navigate(`/gov/tenders/${id}`);
    },
  });
  return (
    <Card title="Check a draft tender before you publish it">
      <p className="mb-3 text-sm text-stone-600">
        The Fairness agent reads your draft and flags clauses that shut out micro and small enterprises, startups
        and local suppliers, citing the clause and the policy, with a fix you can paste in.
      </p>
      <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); upload.mutate(); }}>
        <div className="min-w-60 flex-1">
          <Field label="Draft tender PDF">
            <input type="file" accept="application/pdf,.pdf" className={inputClass} onChange={(e) => setFile(e.target.files[0] || null)} />
          </Field>
        </div>
        <Button type="submit" disabled={!file || upload.isPending}>{upload.isPending ? "Uploading…" : "Upload draft"}</Button>
      </form>
      <div className="mt-3"><ErrorMessage error={upload.error} /></div>
    </Card>
  );
}

export default function GovPage() {
  const tenders = useQuery({ queryKey: ["gov", "tenders"], queryFn: () => request("/gov/tenders") });
  const list = tenders.data || [];
  const checked = list.filter((t) => t.fairness_score !== null);
  const concerns = checked.reduce((n, t) => n + (t.concerns || 0), 0);
  const screened = list.filter((t) => t.screened);
  const avgQualify = screened.length
    ? Math.round((100 * screened.reduce((n, t) => n + t.qualified / t.screened, 0)) / screened.length)
    : null;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Buyer dashboard</h1>
        <p className="text-sm text-stone-600">For government departments: make tenders that local small businesses can actually win.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Tenders on the portals" value={list.filter((t) => t.kind === "portal").length} hint="brought in by the Scout" />
        <Stat label="Fairness checks run" value={checked.length} hint={`${list.filter((t) => t.kind === "draft").length} drafts`} />
        <Stat label="Clauses flagged" value={concerns} hint="that work against small firms" tone={concerns ? "text-red-700" : "text-stone-900"} />
        <Stat label="Businesses that qualify" value={avgQualify === null ? "—" : `${avgQualify}%`} hint="average, screened tenders" tone="text-brand-700" />
      </div>
      <DraftUpload />
      <Card title="Tenders">
        <ErrorMessage error={tenders.error} />
        {tenders.isPending && <p className="text-sm text-stone-500">Loading…</p>}
        {tenders.data?.length === 0 && (
          <p className="text-sm text-stone-500">No tenders yet. Upload a draft above, or run the Scout from the Platform view.</p>
        )}
        <ul className="divide-y divide-stone-200">
          {list.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <Link to={`/gov/tenders/${t.id}`} className="font-medium text-brand-700 hover:underline">{t.title}</Link>
                <p className="text-xs text-stone-500">
                  {t.kind === "draft" ? "Draft, not published" : `${t.buyer} · ${t.portal}`}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {t.screened ? (
                  <span className="text-xs text-stone-600">{t.qualified} of {t.screened} businesses qualify</span>
                ) : null}
                <FairnessBadge score={t.fairness_score} />
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
