"""LangGraph StateGraph: agent nodes, the stop-on-fail branch, the review loop (max 2 send-backs)."""
from datetime import date, datetime
from typing import Callable, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app import db, pdf_reader
from app.agents import checklist as checklist_agent
from app.agents import drafter as drafter_agent
from app.agents import eligibility as eligibility_agent
from app.agents import reader as reader_agent
from app.agents import reviewer as reviewer_agent
from app.agents import tracker as tracker_agent
from app.schemas import BidDraft, Checklist, EligibilityResult, ReviewResult, TenderFacts

MAX_SEND_BACKS = 2

NODE_NAMES = ("reader", "tracker", "eligibility", "stop", "checklist", "drafter", "reviewer", "await_approval")


class TenderState(TypedDict, total=False):
    tender_id: int
    company_id: int
    facts: TenderFacts
    deadline_at: datetime | None  # the Tracker's reading of facts.deadline
    verdicts: EligibilityResult
    checklist: Checklist
    draft: BidDraft
    review: ReviewResult
    review_rounds: int  # send-backs so far; the drafter bumps it on each redraft
    status: str         # running / stopped / awaiting_approval / failed
    stop_reason: str    # why the run stopped or failed


Node = Callable[[TenderState], dict]


class NodeFailed(Exception):
    """A node failed twice; the message names the node, e.g. "checklist failed: boom"."""


def build_graph(nodes: dict[str, Node]):
    g = StateGraph(TenderState)
    for name in NODE_NAMES:
        g.add_node(name, nodes[name])

    g.add_edge(START, "reader")
    g.add_edge("reader", "tracker")
    g.add_edge("tracker", "eligibility")
    g.add_conditional_edges(  # decision 1: stop on a clear must-have fail
        "eligibility", lambda s: "stop" if s["verdicts"].has_must_have_fail else "checklist")
    g.add_edge("stop", END)
    g.add_edge("checklist", "drafter")
    g.add_edge("drafter", "reviewer")
    g.add_conditional_edges(  # decision 2: send the draft back, at most twice
        "reviewer",
        lambda s: "drafter" if not s["review"].all_covered and s.get("review_rounds", 0) < MAX_SEND_BACKS
        else "await_approval")
    g.add_edge("await_approval", END)
    return g.compile()


def _logged(conn, tender_id: int, run_id: str, name: str, fn: Node) -> Node:
    """Write start/finish lines to the agent log and retry the node once on error."""
    def wrapped(state: TenderState) -> dict:
        db.add_log(conn, tender_id, run_id, name, "started")
        try:
            update = fn(state)
        except Exception as e:
            db.add_log(conn, tender_id, run_id, name, f"error, retrying: {e}")
            try:
                update = fn(state)
            except Exception as e:
                db.add_log(conn, tender_id, run_id, name, f"failed: {e}")
                raise NodeFailed(f"{name} failed: {e}") from e
        db.add_log(conn, tender_id, run_id, name, "finished")
        return update
    return wrapped


def run_pipeline(conn, mem, tender_id: int, company_id: int, nodes: dict[str, Node] | None = None,
                 run_id: str | None = None) -> TenderState:
    """Run the whole graph for one tender. Never raises: a broken run ends with status "failed".

    Pass run_id to know it before the run starts (the API polls the log by it).
    """
    nodes = nodes or make_nodes(conn, mem)
    run_id = run_id or uuid4().hex
    graph = build_graph({name: _logged(conn, tender_id, run_id, name, fn) for name, fn in nodes.items()})

    state: TenderState = {"tender_id": tender_id, "company_id": company_id, "review_rounds": 0, "status": "running"}
    db.set_current_run(conn, tender_id, run_id)
    db.set_tender_status(conn, tender_id, "running")
    try:
        for state in graph.stream(state, stream_mode="values"):
            pass
    except Exception as e:
        state = {**state, "status": "failed", "stop_reason": str(e)}
    db.save_run_output(conn, tender_id, state)
    db.set_tender_status(conn, tender_id, state["status"], reason=state.get("stop_reason"))
    return state


def business_lines(company: dict) -> list[str]:
    """The business profile as short facts, for memory search and the drafter."""
    lines = [
        f"Company: {company['name']}",
        f"Products: {company['products']}",
        f"Location: {company['location']}",
        f"Yearly turnover: {company['turnover']}",
        f"Udyam/MSE registered: {'yes' if company['udyam'] else 'no'}",
    ]
    lines += [f"Past order: {o['item']} for {o['buyer']}, {o['value']}, {o['year']}" for o in company["past_orders"]]
    lines += [f"Holds document: {d}" for d in company["documents"]]
    return lines


def make_nodes(conn, mem) -> dict[str, Node]:
    """The real nodes: glue between storage, memory and the agent functions."""
    def company(state):
        return db.get_company(conn, state["company_id"])

    def reader(state):
        tender = db.get_tender(conn, state["tender_id"])
        clauses = pdf_reader.pages_to_clauses(pdf_reader.pdf_to_pages(tender["pdf_path"]))
        mem.add_clauses(state["tender_id"], clauses)
        text = reader_agent.reader_input(reader_agent.select_key_clauses(clauses))
        return {"facts": reader_agent.extract_facts(text)}

    def tracker(state):
        # A countdown is a nice-to-have: if the deadline can't be read, the bid still goes ahead.
        try:
            return {"deadline_at": tracker_agent.parse_deadline(state["facts"].deadline, today=date.today())}
        except Exception:
            return {"deadline_at": None}

    def eligibility(state):
        # The whole profile (a dozen short lines): a top-k search could miss the one line a rule needs.
        evidence = business_lines(company(state))
        return {"verdicts": eligibility_agent.judge_eligibility(state["facts"].rules, evidence)}

    def stop(state):
        fails = [v for v in state["verdicts"].verdicts if v.must_have and v.verdict == "fail"]
        reason = "Fails must-have rule(s): " + "; ".join(
            f"{v.rule_text} (clause {v.clause}, page {v.page}): {v.reason}" for v in fails)
        return {"status": "stopped", "stop_reason": reason}

    def checklist(state):
        return {"checklist": checklist_agent.build_checklist(
            state["facts"].required_documents, company(state)["documents"])}

    def drafter(state):
        review = state.get("review")
        draft = drafter_agent.draft_bid(state["facts"], business_lines(company(state)), review.gaps if review else [])
        return {"draft": draft, "review_rounds": state.get("review_rounds", 0) + (1 if review else 0)}

    def reviewer(state):
        return {"review": reviewer_agent.review_draft(state["draft"], state["facts"].rules)}

    def await_approval(state):
        return {"status": "awaiting_approval"}

    return {"reader": reader, "tracker": tracker, "eligibility": eligibility, "stop": stop, "checklist": checklist,
            "drafter": drafter, "reviewer": reviewer, "await_approval": await_approval}
