import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { clearCompanyId, getCompanyId, isCompanyGone, request } from "../api";
import { Button, Card, Countdown, ErrorMessage, Field, StatusBadge, inputClass } from "../components/ui";
import { sortByDeadline } from "../deadline";

function UploadForm() {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("file", file);
      if (title.trim()) form.append("title", title.trim());
      return request("/tenders", { method: "POST", form });
    },
    onSuccess: ({ id }) => {
      queryClient.invalidateQueries({ queryKey: ["tenders"] });
      navigate(`/tenders/${id}`);
    },
  });

  return (
    <Card title="Upload a tender">
      <form
        className="grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          upload.mutate();
        }}
      >
        <Field label="Tender PDF">
          <input type="file" accept="application/pdf,.pdf" className={inputClass}
                 onChange={(e) => setFile(e.target.files[0] || null)} />
        </Field>
        <Field label="Title (optional)">
          <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)}
                 placeholder="Defaults to the file name" />
        </Field>
        <Button type="submit" disabled={!file || upload.isPending}>{upload.isPending ? "Uploading…" : "Upload"}</Button>
      </form>
      <div className="mt-3"><ErrorMessage error={upload.error} /></div>
    </Card>
  );
}

/** With a saved profile the server also says which tenders fit it; without one the plain list is shown. */
async function loadTenders() {
  const companyId = getCompanyId();
  if (companyId === null) return request("/tenders");
  try {
    return await request(`/tenders?company_id=${companyId}`);
  } catch (error) {
    if (!isCompanyGone(error)) throw error;
    clearCompanyId();   // the profile was deleted on the server; fall back to the plain list
    return request("/tenders");
  }
}

function MatchBadge({ match }) {
  if (!match) return null;
  return match.fits ? (
    <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
          title={`Mentions: ${match.matched.join(", ")}`}>
      Fits your business{match.in_area ? " · in your area" : ""}
    </span>
  ) : (
    <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">Not a typical fit</span>
  );
}

function TenderList() {
  const [onlyFits, setOnlyFits] = useState(false);
  const tenders = useQuery({ queryKey: ["tenders"], queryFn: loadTenders });
  const canFilter = tenders.data?.some((t) => t.match);
  const shown = tenders.data && onlyFits ? tenders.data.filter((t) => t.match?.fits) : tenders.data;
  return (
    <Card title="Tender inbox">
      <ErrorMessage error={tenders.error} />
      {canFilter && (
        <label className="mb-3 flex items-center gap-2 text-sm text-stone-700">
          <input type="checkbox" checked={onlyFits} onChange={(e) => setOnlyFits(e.target.checked)} />
          Show only tenders that fit my business
        </label>
      )}
      {tenders.isPending && <p className="text-sm text-stone-500">Loading…</p>}
      {tenders.data?.length === 0 && (
        <p className="text-sm text-stone-500">No tenders yet. Upload a tender PDF above to get started.</p>
      )}
      {onlyFits && shown?.length === 0 && (
        <p className="text-sm text-stone-500">None of your tenders match what your business makes.</p>
      )}
      {shown?.length > 0 && (
        <ul className="divide-y divide-stone-200">
          {sortByDeadline(shown).map((t) => (
            <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <Link to={`/tenders/${t.id}`} className="font-medium text-brand-700 hover:underline">{t.title}</Link>
                <p className="text-xs text-stone-500">
                  Deadline: {t.deadline || "—"} · EMD: <span>{t.emd || "—"}</span>
                </p>
              </div>
              <div className="flex items-center gap-3">
                <MatchBadge match={t.match} />
                <Countdown deadlineAt={t.deadline_at} />
                <StatusBadge status={t.status} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function InboxPage() {
  return (
    <div className="space-y-6">
      <UploadForm />
      <TenderList />
    </div>
  );
}
