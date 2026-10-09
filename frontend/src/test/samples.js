export function result(overrides = {}) {
  const base = {
    tender: { id: 5, title: "School desks", status: "awaiting_approval", reason: null,
              deadline: "2026-10-30", emd: "₹50,000", payment_terms: "30 days after delivery" },
    facts: { deadline: "2026-10-30", emd: "₹50,000", payment_terms: "30 days after delivery",
             rules: [{ text: "Turnover of Rs 1 crore", clause: "4.1", page: 7, must_have: true }],
             required_documents: ["GST certificate", "ISO 9001"] },
    verdicts: { verdicts: [{ rule_text: "Turnover of Rs 1 crore", verdict: "pass", reason: "Turnover is ₹1.4 crore",
                             clause: "4.1", page: 7, must_have: true }] },
    checklist: { items: [{ document: "GST certificate", status: "have", matched_file: "gst.pdf" },
                         { document: "ISO 9001", status: "need", matched_file: null }] },
    draft: { cover_letter: "Dear Sir, we apply.", sections: [{ title: "Experience", body: "200 desks for KSEB" }] },
    review: { matrix: [{ rule_text: "Turnover of Rs 1 crore", must_have: true, covered: true, where: "Experience" }],
              gaps: [] },
  };
  return { ...base, ...overrides, tender: { ...base.tender, ...(overrides.tender || {}) } };
}

export const NEW_TENDER = result({ tender: { status: "new", deadline: null, emd: null, payment_terms: null },
                                   facts: null, verdicts: null, checklist: null, draft: null, review: null });
