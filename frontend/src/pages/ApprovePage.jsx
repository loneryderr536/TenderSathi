import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { apiUrl, request } from "../api";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

export default function ApprovePage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const result = useQuery({ queryKey: ["tender", id, "result"], queryFn: () => request(`/tenders/${id}/result`) });
  const [coverLetter, setCoverLetter] = useState("");
  const [sections, setSections] = useState([]);
  const draft = result.data?.draft;
  useEffect(() => {
    if (draft) {
      setCoverLetter(draft.cover_letter);
      setSections(draft.sections);
    }
  }, [draft]);

  const approve = useMutation({
    mutationFn: () => request(`/tenders/${id}/approve`, { method: "POST", json: { cover_letter: coverLetter, sections } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tender", id] }),
  });

  if (result.error) return <ErrorMessage error={result.error} />;
  if (!result.data) return <p className="text-sm text-stone-500">Loading…</p>;
  const { tender } = result.data;
  const back = <Link to={`/tenders/${id}`} className="text-sm text-brand-700 underline">Back to the tender</Link>;

  if (tender.status === "approved") {
    return (
      <Card title={`${tender.title}: approved`} actions={back}>
        <p className="mb-4 text-sm text-stone-600">
          Download the bid pack, add your price where it says <code>[PRICE: to be filled by owner]</code>, and submit it
          yourself on the government portal.
        </p>
        <a href={apiUrl(`/tenders/${id}/export`)} className="inline-block rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Download bid pack
        </a>
      </Card>
    );
  }
  if (tender.status !== "awaiting_approval" || !draft) {
    return (
      <Card title={tender.title} actions={back}>
        <p className="text-sm text-stone-600">This bid is not ready for approval yet.</p>
      </Card>
    );
  }

  return (
    <Card title={`Review & approve: ${tender.title}`} actions={back}>
      <p className="mb-4 rounded-lg bg-sky-50 p-3 text-sm text-sky-900">
        Read the draft and edit anything you like. Add your price where it says{" "}
        <code>[PRICE: to be filled by owner]</code>. TenderSathi never submits for you: after approving, download the
        bid pack and submit it yourself on the government portal.
      </p>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          approve.mutate();
        }}
      >
        <Field label="Cover letter">
          <textarea className={inputClass} rows={10} value={coverLetter} onChange={(e) => setCoverLetter(e.target.value)} />
        </Field>
        {sections.map((s, i) => (
          <Field key={s.title} label={s.title}>
            <textarea
              className={inputClass}
              rows={6}
              value={s.body}
              onChange={(e) => setSections(sections.map((x, j) => (j === i ? { ...x, body: e.target.value } : x)))}
            />
          </Field>
        ))}
        <ErrorMessage error={approve.error} />
        <Button type="submit" disabled={approve.isPending}>{approve.isPending ? "Approving…" : "Approve bid"}</Button>
      </form>
    </Card>
  );
}
