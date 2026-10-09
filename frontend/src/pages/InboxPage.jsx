import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { Button, Card, ErrorMessage, Field, StatusBadge, inputClass } from "../components/ui";

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

function TenderList() {
  const tenders = useQuery({ queryKey: ["tenders"], queryFn: () => request("/tenders") });
  return (
    <Card title="Tender inbox">
      <ErrorMessage error={tenders.error} />
      {tenders.isPending && <p className="text-sm text-stone-500">Loading…</p>}
      {tenders.data?.length === 0 && (
        <p className="text-sm text-stone-500">No tenders yet. Upload a tender PDF above to get started.</p>
      )}
      {tenders.data?.length > 0 && (
        <ul className="divide-y divide-stone-200">
          {tenders.data.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
              <div>
                <Link to={`/tenders/${t.id}`} className="font-medium text-brand-700 hover:underline">{t.title}</Link>
                <p className="text-xs text-stone-500">
                  Deadline: {t.deadline || "—"} · EMD: <span>{t.emd || "—"}</span>
                </p>
              </div>
              <StatusBadge status={t.status} />
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
