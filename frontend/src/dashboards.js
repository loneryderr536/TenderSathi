/** The three dashboards a person can log in to. Choosing one only picks it; the login still needs that account. */
export const DASHBOARDS = [
  { role: "business", label: "Business dashboard", who: "Small business owners",
    hint: "Find tenders, check eligibility, prepare bids", canSignUp: true },
  { role: "government", label: "Government dashboard", who: "Government buyers",
    hint: "Fairness check and who can bid", canSignUp: true },
  { role: "platform", label: "Platform dashboard", who: "TenderSathi team",
    hint: "Agent health, Scout and accuracy", canSignUp: false },
];
