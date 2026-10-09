import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { clearCompanyId, getCompanyId, isCompanyGone, request, setCompanyId } from "../api";
import { Button, Card, ErrorMessage, Field, inputClass } from "../components/ui";

const EMPTY = { name: "", products: "", location: "", turnover: "", udyam: false, documents: "", past_orders: [] };
const EMPTY_ORDER = { buyer: "", item: "", value: "", year: "" };

function toForm(company) {
  return { ...company, documents: company.documents.join("\n"),
           past_orders: company.past_orders.map((o) => ({ ...o, year: String(o.year) })) };
}

function toBody(form, id) {
  return {
    ...(id ? { id } : {}),
    name: form.name, products: form.products, location: form.location, turnover: form.turnover, udyam: form.udyam,
    documents: form.documents.split("\n").map((d) => d.trim()).filter(Boolean),
    past_orders: form.past_orders
      .filter((o) => o.buyer.trim() || o.item.trim())
      .map((o) => ({ ...o, year: Number(o.year) || 0 })),
  };
}

export default function ProfilePage() {
  const [companyId, setId] = useState(getCompanyId);
  const [form, setForm] = useState(EMPTY);
  const existing = useQuery({
    queryKey: ["company", companyId],
    queryFn: () => request(`/companies/${companyId}`),
    enabled: Boolean(companyId),
  });
  useEffect(() => {
    if (existing.data) setForm(toForm(existing.data));
  }, [existing.data]);
  const forget = () => {
    clearCompanyId();
    setId(null);
  };
  useEffect(() => {
    if (isCompanyGone(existing.error)) forget();
  }, [existing.error]);

  const save = useMutation({
    mutationFn: async () => {
      try {
        return await request("/companies", { method: "POST", json: toBody(form, companyId) });
      } catch (error) {
        if (!isCompanyGone(error)) throw error;
        forget();   // the saved profile is gone from the server: save this one as new
        return request("/companies", { method: "POST", json: toBody(form, null) });
      }
    },
    onSuccess: ({ id }) => {
      setCompanyId(id);
      setId(id);
    },
  });

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const setOrder = (i, key) => (e) =>
    setForm({ ...form, past_orders: form.past_orders.map((o, j) => (j === i ? { ...o, [key]: e.target.value } : o)) });

  return (
    <Card title="Business profile">
      <p className="mb-4 text-sm text-stone-600">
        Fill this in once. The agents use it to check each tender's rules and to write your bids.
      </p>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Business name"><input className={inputClass} value={form.name} onChange={set("name")} /></Field>
          <Field label="What you make or do"><input className={inputClass} value={form.products} onChange={set("products")} /></Field>
          <Field label="Location"><input className={inputClass} value={form.location} onChange={set("location")} /></Field>
          <Field label="Yearly turnover"><input className={inputClass} value={form.turnover} onChange={set("turnover")} placeholder="₹1.4 crore" /></Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.udyam} onChange={set("udyam")} className="h-4 w-4 accent-brand-600" />
          Udyam / MSE registered
        </label>
        <Field label="Documents you hold (one per line)">
          <textarea className={inputClass} rows={4} value={form.documents} onChange={set("documents")}
                    placeholder={"GST certificate\nPAN card\nUdyam certificate"} />
        </Field>

        <div>
          <h3 className="mb-2 text-sm font-medium text-stone-700">Past orders</h3>
          <div className="space-y-3">
            {form.past_orders.map((order, i) => (
              <div key={i} className="grid gap-2 rounded-lg border border-stone-200 p-3 sm:grid-cols-5">
                <Field label="Buyer"><input className={inputClass} value={order.buyer} onChange={setOrder(i, "buyer")} /></Field>
                <Field label="Item"><input className={inputClass} value={order.item} onChange={setOrder(i, "item")} /></Field>
                <Field label="Value"><input className={inputClass} value={order.value} onChange={setOrder(i, "value")} /></Field>
                <Field label="Year"><input className={inputClass} inputMode="numeric" value={order.year} onChange={setOrder(i, "year")} /></Field>
                <div className="flex items-end">
                  <Button type="button" variant="secondary" className="w-full"
                          onClick={() => setForm({ ...form, past_orders: form.past_orders.filter((_, j) => j !== i) })}>
                    Remove
                  </Button>
                </div>
              </div>
            ))}
          </div>
          <Button type="button" variant="secondary" className="mt-2"
                  onClick={() => setForm({ ...form, past_orders: [...form.past_orders, EMPTY_ORDER] })}>
            Add past order
          </Button>
        </div>

        <ErrorMessage error={(isCompanyGone(existing.error) ? null : existing.error) || save.error} />
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save profile"}</Button>
          {save.isSuccess && <span className="text-sm text-brand-700">Profile saved</span>}
        </div>
      </form>
    </Card>
  );
}
