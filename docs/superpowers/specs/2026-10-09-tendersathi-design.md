# TenderSathi: Design Spec

**Date:** 9 October 2026
**Event:** 24-hour hackathon, Track 1: Autonomous AI Agents
**Builder:** solo
**Status:** draft for review

---

## 1. Summary

TenderSathi is a website where a team of AI agents helps small businesses bid for government tenders.
The agents read a tender document, check whether the business qualifies (rule by rule, with the page
each rule came from), list the documents needed, draft the bid, and check the draft before the owner
sees it.

The owner stays in control: they review the bid, add their own price, and submit it themselves on the
government portal. TenderSathi never contacts the government and never submits anything.

**One line:** *Free to check if you qualify. Pay a small fee only when you decide to bid.*

---

## 2. The problem

Government offices publish **tenders** when they want to buy something: "We need 200 school desks.
Here are the rules. Apply by 30 October." Small businesses could supply many of these, but:

- **Finding tenders is hard.** Hundreds appear every day across many government websites.
- **Tenders are long and legal.** Key rules (turnover, past experience, certificates) are buried deep inside.
- **One mistake means rejection.** A single missing document disqualifies the bid.
- **Help is expensive.** Consultants charge per bid, so small firms bid rarely or never.
- **Work is repeated.** The same company details and certificates are retyped for every bid.

The scale is real: in FY 2025-26, micro and small enterprises handled 68% of orders and 47.1% of order
value on the Government e-Marketplace (GeM), with over 11 lakh of them registered there
([IBEF, citing PIB, Apr 2026](https://www.ibef.org/news/government-e-marketplace-gem-achieves-rs-18-4-lakh-crore-us-197-72-billion-gmv-emerges-as-key-digital-public-procurement-platform)).

---

## 3. Who it is for

**Focus user:** a small business that **can already do the work** but loses or skips government
tenders **because of the paperwork**.

*Example:* a furniture workshop in Ernakulam that already makes tables for shops and offices. It has
workers and enough money to buy wood for an order, but nobody who understands tenders.

**Not the first focus:** firms with no money to start any order. Their main problem is cash, not
paperwork (see Section 9).

**Who is who:**

| Party | Role | Uses TenderSathi? |
|---|---|---|
| Government office | Publishes the tender, picks the winner, pays | No |
| Small business | Bids for the tender | **Yes, this is our user** |
| TenderSathi | The business's assistant for reading and preparing the bid | n/a |

**TenderSathi is a tool, not a middleman.** It never talks to the government, never submits bids and
never takes a share of a contract. Think "tax software", not "tax agent".

---

## 4. How a tender flows

1. The government publishes a tender on its portal (GeM, CPPP, Kerala e-tender).
2. The owner downloads the tender PDF and uploads it to TenderSathi. (Automatic discovery is future scope.)
3. TenderSathi's agents read it, check eligibility, list documents, draft and review the bid.
4. The owner reviews, edits, adds their price, and **submits on the government portal themselves**.
5. The government compares all bids and picks a winner.
6. If the business wins, **only then** does it buy materials, make the goods and deliver.

TenderSathi covers steps 2 to 4.

---

## 5. Features

### MVP (built in the 24 hours)

| # | Feature | What the owner sees |
|---|---|---|
| F1 | **Business profile** | A one-time form: what you make, location, yearly turnover, past orders, certificates held |
| F2 | **Tender upload** | Upload a tender PDF; it appears in the Tender Inbox |
| F3 | **Tender summary** | Deadline, deposit (EMD), key rules, required documents and **payment terms** on one screen |
| F4 | **Eligibility report** | Each rule marked **pass / fail / missing**, with the clause and page it came from |
| F5 | **Document checklist** | Every required document, marked "you have it" or "you still need it" |
| F6 | **Drafted bid** | Cover letter and technical sections written from the business's own details |
| F7 | **Compliance matrix** | Table proving every mandatory rule is answered in the draft |
| F8 | **Live agent log** | Each agent's step shown on screen as it happens |
| F9 | **Approve & export** | Owner approves, edits if needed, and downloads the bid pack |

### Stretch (only if time allows)

- **Payment-type label and filter:** tag each tender "pay after delivery", "paid in stages" or
  "advance allowed (with bank guarantee)", and filter the inbox by it.
- **Cash-need warning:** "You'll spend about ₹X before payment arrives, roughly N days after delivery."
- **Deadline reminders** by email (Tracker agent).

### Future scope (slides only)

- Automatic tender discovery from official portals.
- **Private buyers:** schools, hospitals, colleges and companies send RFQs (requests for quotation).
  The owner uploads the RFQ and the same agents prepare a quotation, including a suggested advance-payment
  term, which private buyers can often negotiate.
- Malayalam and Hindi interface.
- Price guidance from past winning bids.
- Pointers to working-capital options after a win.
- LangGraph checkpointing so long runs can pause and resume across server restarts.

---

## 6. The agents

Each agent is a **LangGraph node**: a normal Python function `(state) -> updates` with one job, its own
short prompt, and a **checked output**. Inside each node, a **LangChain chat model** is called with
`.with_structured_output(PydanticModel)`, so the LLM must return the exact shape the next agent expects.

LangGraph is used in a **thin** way: one `StateGraph`, five nodes, two conditional edges. No LangChain
tool-calling agents, no supervisor agent, no checkpointer.

| Agent | Reads | Does | Returns |
|---|---|---|---|
| **Reader** | Tender PDF text | Splits it into clauses, stores them in ChromaDB, extracts the key facts | Deadline, EMD, list of rules (each with clause + page), required documents, payment terms |
| **Eligibility** | Each rule + matching business details (searched from ChromaDB) | Judges each rule | `pass / fail / missing` per rule, with reason and citation; an overall verdict |
| **Checklist** | Required documents + the business's stored documents | Matches each requirement to a stored file | Have / need list |
| **Drafter** | Tender facts + business memory | Writes the bid | Cover letter + technical sections |
| **Reviewer** | Draft + full rule list | Checks every mandatory rule is covered | Compliance matrix + list of gaps |
| **Tracker** *(stretch)* | Deadlines | Sends reminders | Emails |

### Two decisions that make it "autonomous"

1. **Eligibility can stop the run.** If the business clearly **fails a must-have rule**, a conditional
   edge sends the graph to a Stop node that explains why. This saves time and money.
2. **Reviewer can send the draft back.** If a mandatory rule is not covered, the draft goes back to the
   Drafter with notes, **up to 2 rounds**. If gaps remain, they are shown to the owner.

### The graph

```
START → Reader → Eligibility ──must-have fail──→ Stop (explain why) → END
                     │ qualifies
                     ▼
                 Checklist → Drafter → Reviewer ──gaps and rounds < 2──→ Drafter
                                           │ all covered, or 2 rounds done
                                           ▼
                                   Awaiting approval → END
```

### Graph code (sketch)

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class TenderState(TypedDict, total=False):
    tender_id: int
    company_id: int
    facts: TenderFacts            # Pydantic models from schemas.py
    verdicts: EligibilityResult
    checklist: Checklist
    draft: BidDraft
    review: ReviewResult
    review_rounds: int
    status: str                   # running / stopped / awaiting_approval / failed

g = StateGraph(TenderState)
g.add_node("reader", reader_node)
g.add_node("eligibility", eligibility_node)
g.add_node("stop", stop_node)
g.add_node("checklist", checklist_node)
g.add_node("drafter", drafter_node)
g.add_node("reviewer", reviewer_node)
g.add_node("await_approval", await_approval_node)

g.add_edge(START, "reader")
g.add_edge("reader", "eligibility")
g.add_conditional_edges("eligibility",            # decision 1
    lambda s: "stop" if s["verdicts"].has_must_have_fail else "checklist")
g.add_edge("stop", END)
g.add_edge("checklist", "drafter")
g.add_edge("drafter", "reviewer")
g.add_conditional_edges("reviewer",               # decision 2
    lambda s: "drafter" if (not s["review"].all_covered and s["review_rounds"] < 2)
              else "await_approval")
g.add_edge("await_approval", END)

graph = g.compile()
```

**Approval:** the graph simply ends with `status = "awaiting_approval"`. The `/approve` endpoint marks
the tender approved. This avoids LangGraph's interrupt/checkpointer machinery.

**Agent log:** each node writes one line to the SQLite `agent_log` table when it starts and finishes,
which the website polls.

**Fallback:** nodes are plain functions, so if LangGraph causes trouble, a 20-line Python loop can call
the same functions in the same order.

### Where RAG and vector memory are used

- **Tender clauses** are embedded into ChromaDB, so each agent pulls **only the clauses it needs**
  instead of the whole PDF.
- **Business memory** (profile, past orders, certificate names) is embedded too, so the Eligibility and
  Drafter agents find the right evidence for each rule.
- Every verdict carries its **clause and page number**, so the owner can check it.

---

## 7. Tech stack

Chosen to be **simple, reliable and doable solo** by someone new to multi-agent systems. LangChain and
LangGraph are used only for the parts they make easier: structured LLM output and a visible graph.

| Part | Choice | Why |
|---|---|---|
| Frontend | **React (JavaScript) + Vite + Tailwind CSS** | Simple single-page app; fast dev loop; no TypeScript to fight |
| Pages / API calls | React Router, TanStack Query | Easy routing and loading states |
| Backend | **Python + FastAPI** | Builder has shipped FastAPI before; Python has the best PDF and AI libraries |
| Orchestration | **LangGraph** (`StateGraph`) | The flow has a branch and a loop; a graph shows them clearly and is easy to explain to judges |
| LLM calls | **LangChain chat model** (`langchain-anthropic` or `langchain-openai`) | One interface for any provider; built-in retries |
| Agent outputs | **Pydantic** via `.with_structured_output()` | Every agent must return a fixed shape; malformed output is caught |
| AI model | Paid LLM API, chosen in `llm.py` | Best reasoning quality; switch provider in one line |
| PDF reading | **PyMuPDF** | One install, fast, reliable for text PDFs |
| Vector memory | **ChromaDB** (embedded) | No server to run; builder has used it before |
| App data + agent log | **SQLite** | A single file, zero setup |
| Live progress | Frontend polls the agent log every 2 seconds | Simplest way to show agents working |
| Background work | FastAPI `BackgroundTasks` | Pipeline runs without freezing the page |
| Testing | pytest | Standard |
| Running | Two terminals: `uvicorn` and `npm run dev` | No Docker needed |

**Embeddings note:** ChromaDB's default embedding model is fine for English tenders. If the API key is
Claude (which has no embeddings API), keep Chroma's default or use a local model; switch to a
multilingual model when Hindi/Malayalam tenders are supported.

---

## 8. Architecture

```
React app  ──HTTP──►  FastAPI  ──►  LangGraph graph  ──►  Agent nodes  ──►  LLM API (via LangChain)
   │                    │                  │
   │  poll /log         │                  ├──► ChromaDB (clauses + business memory)
   └────────────────────┘                  └──► SQLite (data + agent log)
```

### Folder layout (already created in the repo)

```
backend/app/
  main.py          FastAPI app
  config.py        settings from .env
  llm.py           returns the LangChain chat model for the chosen provider
  db.py            SQLite tables
  memory.py        ChromaDB helpers
  pdf_reader.py    PDF → pages → clauses
  schemas.py       Pydantic output models
  graph.py         LangGraph StateGraph: nodes, edges, decisions
  agents/          one node function each: reader, eligibility, checklist, drafter, reviewer, tracker
  routes/          companies, tenders
frontend/          React app
data/              sample tender PDFs and demo business profile
storage/           SQLite file and ChromaDB data (not committed)
```

### Data (SQLite)

| Table | Holds |
|---|---|
| `companies` | Profile fields: name, products, location, turnover, Udyam/MSE status |
| `company_documents` | Certificate and document names the business holds |
| `past_orders` | Buyer, item, value, year |
| `tenders` | Uploaded PDF path, title, deadline, EMD, payment terms, status |
| `rules` | One row per extracted rule: text, clause, page, must-have flag |
| `verdicts` | Rule verdicts: pass/fail/missing, reason |
| `checklist_items` | Required document, have/need |
| `drafts` | Bid text, round number |
| `agent_log` | Run id, agent, message, time (shown live on screen) |

### API

| Method | Path | Purpose |
|---|---|---|
| POST | `/companies` | Create or update the business profile |
| GET | `/companies/{id}` | Read the profile |
| POST | `/tenders` | Upload a tender PDF |
| GET | `/tenders` | Tender inbox |
| POST | `/tenders/{id}/run` | Start the agent pipeline (background) |
| GET | `/tenders/{id}/log` | Agent log (polled every 2 s) |
| GET | `/tenders/{id}/result` | Summary, eligibility, checklist, draft, compliance matrix |
| POST | `/tenders/{id}/approve` | Owner approves (with edits) |
| GET | `/tenders/{id}/export` | Download the bid pack |

### Screens

1. **Business Profile:** one-time form.
2. **Tender Inbox:** uploaded tenders with status and deadline.
3. **Tender Detail:** tabs for Summary, Eligibility, Checklist, Draft, Compliance, plus the live agent log.
4. **Approve & Export:** edit, approve, download.

---

## 9. Payment reality (and what TenderSathi does about it)

**The fact:** governments usually pay **after** the goods are delivered and accepted. TenderSathi
cannot change that; the government sets payment terms in the tender before anyone bids.

Some tenders do pay in **stages**, or allow an **advance** against a bank guarantee. So TenderSathi:

- **Reads the payment clause** of every tender and shows it clearly in the summary (MVP, F3).
- *(Stretch)* **Labels and filters** tenders by payment type, so a cash-tight business can see
  advance or staged-payment tenders first.
- *(Stretch)* **Warns about the cash gap** before bidding.

This is why the focus user (Section 3) is a business that can already fund an order. It is stated
honestly in the pitch.

---

## 10. Business model

**The owner never pays for idle months, and never pays a share of a contract.**

| Tier | Who | Price model | Includes |
|---|---|---|---|
| **Free** | Small businesses | Free | Upload tenders, tender summary, eligibility check |
| **Per bid** | Small businesses | Small one-time fee per bid | Checklist, drafted bid, compliance check, export |
| **Pro** *(later)* | CA firms and bid consultants | Monthly | Many client workspaces |

**Why owners pay:** today they either skip tenders or pay a consultant per bid. TenderSathi costs a
fraction of that, is faster, and is paid **only when there is a tender they actually want**.

**Why it isn't a middleman:** no commission on contracts, no contact with the government, the owner
submits.

---

## 11. Benefit to society

- Small, rural and women-led businesses compete on equal terms with firms that can afford consultants.
- More bidders per tender means better value for public money.
- Clause-cited decisions make the process easier to check.

---

## 12. Error handling

| Situation | What happens |
|---|---|
| PDF has no extractable text (scanned) | Upload is rejected with "This looks like a scanned PDF; please use a text PDF" |
| LLM returns malformed output | Structured-output parsing fails → node retries once → if it fails again, status becomes `failed` with a clear message in the agent log |
| LLM API error / timeout | Retry once after a short wait; then mark the run failed and show the error |
| Business clearly fails a must-have rule | Run stops after Eligibility, with the reason (by design) |
| Reviewer still finds gaps after 2 rounds | Draft is shown with the gaps highlighted for the owner |
| Missing API key | Server refuses to start, naming the missing setting |

The final bid is **never** produced without the owner's approval.

---

## 13. Testing

- **Unit tests (pytest)** for the non-AI parts: PDF → clauses, database helpers, and the **graph's
  routing** (stop on a must-have fail, max 2 review rounds) using fake node functions that return set
  values.
- **Fixture test:** one real tender PDF with a known answer sheet (expected rules and verdicts),
  checked by hand after each prompt change.
- **Demo rehearsal:** run the full demo end to end at least twice before judging.

---

## 14. 24-hour plan (solo)

| Hours | Work |
|---|---|
| 0–1 | **Spike:** one real tender PDF → a 2-node LangGraph (Reader → Eligibility). Confirms the core and LangGraph both work. |
| 1–2 | Collect 3 demo tender PDFs (text PDFs) and write the sample business profile |
| 2–7 | Backend: SQLite, ChromaDB, PDF reader, all agent nodes, the graph with both decisions |
| 7–9 | API routes, background run, agent log |
| 9–15 | Frontend: four screens, polling log, approve & export |
| 15–17 | Tests and error handling |
| 17–19 | Stretch: payment-type label/filter, cash-need warning |
| 19–21 | Polish UI, screenshots, README |
| 21–22 | Optional deploy |
| 22–24 | Rehearse the demo, buffer, sleep |

**Cut first if behind:** stretch features, then export polish, then the Reviewer's second round.

---

## 15. Demo script (3 minutes)

1. **Problem (20 s):** a furniture workshop can make 200 desks but can't read an 80-page tender.
2. **Upload (20 s):** upload a real government tender PDF.
3. **Agents at work (40 s):** live log: Reader → Eligibility → Checklist → Drafter → Reviewer.
4. **Results (60 s):** eligibility report with page citations, the one missing certificate, payment terms, drafted bid, compliance matrix.
5. **Autonomy (20 s):** a second tender the business fails, where the run stops and explains why.
6. **Close (20 s):** "Free to check. Pay only when you bid. You stay in control." Mention private RFQs as next.

---

## 16. Risks and open questions

| Risk / question | Plan |
|---|---|
| Messy or scanned tender PDFs | Choose clean text PDFs for the demo; OCR is future scope |
| Long tenders exceed context | Clause chunks in ChromaDB; agents read only relevant clauses |
| "Is it really multi-agent?" | Show the LangGraph diagram and the two decisions (stop on fail, reviewer send-back) live |
| LangGraph learning curve | Thin usage only; tested in the hour-0 spike; plain-Python loop as fallback |
| "Isn't this a middleman?" | No commission, no government contact, owner submits |
| "What if they can't fund the order?" | Payment terms shown up front; focus user stated honestly |
| Per-bid price | Exact amount not decided; set before any real launch |
