import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { request } from "../api";
import { Button, Card, ErrorMessage, Field, Stat, inputClass } from "../components/ui";
import { DraftUpload, FairnessBadge } from "./GovPage";

export const MIN_ADVANCE = 25;
export const MAX_ADVANCE = 50;

export function rupees(amount) {
  return amount === null || amount === undefined ? "—" : `₹${Number(amount).toLocaleString("en-IN")}`;
}

const lines = (text) => text.split("\n").map((l) => l.trim()).filter(Boolean);

function RfqForm() {
  const [form, setForm] = useState({
    title: "", scope: "", requirements: "", documents: "", deadline: "", delivery_days: 30, advance_percent: 30,
  });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const advance = Number(form.advance_percent);
  const advanceOk = advance >= MIN_ADVANCE && advance <= MAX_ADVANCE;
  const post = useMutation({
    mutationFn: () => request("/rfq", { method: "POST", json: {
      ...form, requirements: lines(form.requirements), documents: lines(form.documents),
      delivery_days: Number(form.delivery_days), advance_percent: advance,
    } }),
    onSuccess: ({ id }) => {
      queryClient.invalidateQueries({ queryKey: ["rfq"] });
      navigate(`/private/rfq/${id}`);
    },
  });
  return (
    <Card title="Post a request for quotation">
      <p className="mb-4 text-sm text-stone-600">
        Your request goes to the businesses on TenderSathi. Their agents check if they qualify, and they send you a quotation.
      </p>
      <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); post.mutate(); }}>
        <div className="sm:col-span-2">
          <Field label="Title"><input className={inputClass} value={form.title} onChange={set("title")} placeholder="e.g. Supply of 60 wooden dining tables" required /></Field>
        </div>
        <div className="sm:col-span-2">
          <Field label="What you need (scope)">
            <textarea rows={3} className={inputClass} value={form.scope} onChange={set("scope")} required
                      placeholder="Quantity, specification, where it is needed" />
          </Field>
        </div>
        <Field label="Requirements for suppliers (one per line)">
          <textarea rows={3} className={inputClass} value={form.requirements} onChange={set("requirements")}
                    placeholder={"One similar order of Rs. 5 lakh in 3 years\nValid GST registration"} />
        </Field>
        <Field label="Documents to send (one per line)">
          <textarea rows={3} className={inputClass} value={form.documents} onChange={set("documents")}
                    placeholder={"GST registration certificate\nPAN card"} />
        </Field>
        <Field label="Last date for quotations"><input className={inputClass} value={form.deadline} onChange={set("deadline")} placeholder="e.g. 5 November 2026, 5:00 PM" required /></Field>
        <Field label="Delivery within (days)"><input type="number" min={1} className={inputClass} value={form.delivery_days} onChange={set("delivery_days")} required /></Field>
        <div className="sm:col-span-2">
          <Field label={`Advance on order (${MIN_ADVANCE}% to ${MAX_ADVANCE}%, mandatory)`}>
            <div className="flex items-center gap-3">
              <input type="range" min={MIN_ADVANCE} max={MAX_ADVANCE} step={5} className="flex-1 accent-emerald-700"
                     value={advanceOk ? advance : MIN_ADVANCE} onChange={set("advance_percent")} aria-label="Advance slider" />
              <input type="number" min={MIN_ADVANCE} max={MAX_ADVANCE} className={`${inputClass} w-24`}
                     value={form.advance_percent} onChange={set("advance_percent")} aria-label="Advance percent" required />
              <span className="text-sm font-semibold">%</span>
            </div>
          </Field>
          <p className={`mt-1 text-xs ${advanceOk ? "text-stone-500" : "font-medium text-red-700"}`}>
            {advanceOk
              ? `You pay ${advance}% of the order value when you place the order; small suppliers can start work without borrowing.`
              : `The advance must be between ${MIN_ADVANCE}% and ${MAX_ADVANCE}%.`}
          </p>
        </div>
        <div className="sm:col-span-2 space-y-3">
          <ErrorMessage error={post.error} />
          <Button type="submit" disabled={post.isPending || !advanceOk}>{post.isPending ? "Posting…" : "Post request"}</Button>
        </div>
      </form>
    </Card>
  );
}

const RFQ_STATUS = {
  awarded: ["Awarded", "bg-brand-100 text-brand-700"],
};

export default function PrivatePage() {
  const rfqs = useQuery({ queryKey: ["rfq", "mine"], queryFn: () => request("/rfq/mine") });
  const buyer = useQuery({ queryKey: ["gov", "tenders"], queryFn: () => request("/gov/tenders") });
  const list = rfqs.data || [];
  const drafts = (buyer.data || []).filter((t) => t.kind === "draft");
  const quotes = list.reduce((n, r) => n + r.quotations, 0);
  const avgAdvance = list.length ? Math.round(list.reduce((n, r) => n + r.advance_percent, 0) / list.length) : null;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Owner dashboard</h1>
        <p className="text-sm text-stone-600">For private owners: post requests for quotation and pick the best quote from small businesses.</p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Requests posted" value={list.length} hint={`${list.filter((r) => r.status !== "awarded").length} open`} />
        <Stat label="Quotations received" value={quotes} tone="text-sky-700" />
        <Stat label="Awarded" value={list.filter((r) => r.status === "awarded").length} tone="text-brand-700" />
        <Stat label="Average advance" value={avgAdvance === null ? "—" : `${avgAdvance}%`} hint="paid on order" />
      </div>
      <Card title="Your requests for quotation">
        <ErrorMessage error={rfqs.error} />
        {rfqs.isPending && <p className="text-sm text-stone-500">Loading…</p>}
        {rfqs.data?.length === 0 && <p className="text-sm text-stone-500">No requests yet. Post one below.</p>}
        <ul className="divide-y divide-stone-200">
          {list.map((r) => {
            const [label, style] = RFQ_STATUS[r.status] || ["Open for quotes", "bg-sky-100 text-sky-800"];
            return (
              <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <Link to={`/private/rfq/${r.id}`} className="font-medium text-brand-700 hover:underline">{r.title}</Link>
                  <p className="text-xs text-stone-500">
                    {r.advance_percent}% advance · {r.quotations} quotation{r.quotations === 1 ? "" : "s"}
                    {r.lowest !== null ? ` · lowest ${rupees(r.lowest)}` : ""}{r.accepted ? ` · awarded to ${r.accepted}` : ""}
                  </p>
                </div>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>{label}</span>
              </li>
            );
          })}
        </ul>
      </Card>
      <RfqForm />
      <DraftUpload detailPath="/private/drafts" />
      {drafts.length > 0 && (
        <Card title="Drafts you checked">
          <ul className="divide-y divide-stone-200">
            {drafts.map((t) => (
              <li key={t.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <Link to={`/private/drafts/${t.id}`} className="font-medium text-brand-700 hover:underline">{t.title}</Link>
                <FairnessBadge score={t.fairness_score} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
