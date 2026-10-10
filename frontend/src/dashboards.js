/** The three dashboards a person can log in to. Choosing one only picks it; the login still needs that account.
 *  demoEmail: the dummy account (password pass123, from data/demo_accounts.json) its login form starts with. */
export const DASHBOARDS = [
  { role: "business", label: "Business dashboard", who: "Small business owners",
    hint: "Find tenders, check eligibility, prepare bids", canSignUp: true, demoEmail: "john@gmail.com" },
  { role: "government", label: "Government dashboard", who: "Government buyers",
    hint: "Fairness check and who can bid", canSignUp: true, demoEmail: "mary@gmail.com" },
  { role: "platform", label: "Platform dashboard", who: "TenderSathi team",
    hint: "Agent health, Scout and accuracy", canSignUp: false, demoEmail: "admin@gmail.com" },
];

export const DEMO_PASSWORD = "pass123";
