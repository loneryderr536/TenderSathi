import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { request } from "../api";
import { Button, Card, ErrorMessage } from "../components/ui";
import { Fairness, Participation } from "./GovTenderPage";
import { rupees } from "./PrivatePage";

const QUOTE_STATUS = {
  submitted: ["Received", "bg-sky-100 text-sky-800"],
  accepted: ["Accepted", "bg-brand-100 text-brand-700"],
  declined: ["Declined", "bg-stone-100 text-stone-600"],
};

function Quotations({ id, awarded }) {
  const queryClient = useQueryClient();
  const quotes = useQuery({ queryKey: ["rfq", id, "quotes"], queryFn: () => request(`/rfq/${id}/quotations`) });
  const accept = useMutation({
    mutationFn: (qid) => request(`/rfq/${id}/quotations/${qid}/accept`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rfq"] });
      queryClient.invalidateQueries({ queryKey: ["gov"] });
    },
  });
  const list = quotes.data || [];
  return (
    <Card title={`Quotations received (${list.length})`}>
      <ErrorMessage error={quotes.error || accept.error} />
      {quotes.data?.length === 0 && (
        <p className="text-sm text-stone-500">No quotations yet. Businesses see your request in their inbox and send quotes here.</p>
      )}
      {list.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-stone-500">
              <tr><th className="py-2 pr-3">Business</th><th className="pr-3">Price</th><th className="pr-3">Delivery</th><th className="pr-3">Note</th><th className="pr-3">Status</th><th /></tr>
            </thead>
            <tbody className="divide-y divide-stone-200">
              {list.map((q, i) => {
                const [label, style] = QUOTE_STATUS[q.status] || [q.status, "bg-stone-100"];
                return (
                  <tr key={q.id}>
                    <td className="py-2 pr-3">
                      <span className="font-medium">{q.company_name}</span>
                      <span className="block text-xs text-stone-500">{q.company_location}{q.company_udyam ? " · Udyam MSE" : ""}</span>
                    </td>
                    <td className="pr-3 font-semibold">{rupees(q.amount)}{i === 0 && list.length > 1 && <span className="ml-1 text-xs font-medium text-brand-700">lowest</span>}</td>
                    <td className="pr-3">{q.delivery_days} days</td>
                    <td className="pr-3 text-stone-600">{q.note || "—"}</td>
                    <td className="pr-3"><span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style}`}>{label}</span></td>
                    <td>
                      {!awarded && (
                        <Button variant="secondary" onClick={() => accept.mutate(q.id)} disabled={accept.isPending}>Accept</Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function PrivateRfqPage() {
  const { id } = useParams();
  const data = useQuery({
    queryKey: ["gov", "tender", id],
    queryFn: () => request(`/gov/tenders/${id}`),
    refetchInterval: (query) => (query.state.data?.insights.running ? 2000 : false),
  });
  if (!data.data) return data.error ? <ErrorMessage error={data.error} /> : <p className="text-sm text-stone-500">Loading…</p>;
  const { tender, fairness, insights } = data.data;
  const awarded = tender.status === "awarded";
  return (
    <div className="space-y-6">
      <div>
        <Link to="/private" className="text-sm text-brand-700 hover:underline">← Owner dashboard</Link>
        <h1 className="mt-1 text-2xl font-semibold">{tender.title}</h1>
        <p className="text-sm text-stone-600">
          Request for quotation · {tender.buyer} · <span className="font-medium">{tender.advance_percent}% advance on order</span>
          {awarded && <span className="ml-2 rounded-full bg-brand-100 px-2 py-0.5 text-xs font-medium text-brand-700">Awarded</span>}
        </p>
      </div>
      <Quotations id={id} awarded={awarded} />
      <Fairness id={id} report={fairness} />
      <Participation id={id} insights={insights} />
    </div>
  );
}
