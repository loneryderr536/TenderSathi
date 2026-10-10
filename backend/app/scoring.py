"""Bid / no-bid score: one number per tender, from what the agents found. No AI call, so it is instant."""
from datetime import datetime


def bid_score(output: dict, deadline_at: str | None, now: datetime | None = None) -> dict | None:
    """{"score": 0-100, "decision": "bid" / "bid_with_care" / "no_bid", "reasons": [...]}; None before a run."""
    verdicts, checklist = output.get("verdicts"), output.get("checklist")
    if verdicts is None:
        return None
    reasons, score = [], 100
    fails = [v for v in verdicts.verdicts if v.must_have and v.verdict == "fail"]
    if fails:
        return {"score": 0, "decision": "no_bid",
                "reasons": [f"Fails a must-have rule: {v.rule_text} (clause {v.clause})" for v in fails]}
    for v in verdicts.verdicts:
        if v.verdict == "missing":
            score -= 15 if v.must_have else 5
            reasons.append(f"Not shown in your profile: {v.rule_text} (clause {v.clause})")
        elif v.verdict == "fail":
            score -= 5
            reasons.append(f"Optional rule not met: {v.rule_text}")
    if checklist:
        need = [i.document for i in checklist.items if i.status == "need"]
        score -= 8 * len(need)
        if need:
            reasons.append(f"{len(need)} document(s) still to arrange: " + ", ".join(need))
    if deadline_at:
        days = (datetime.fromisoformat(deadline_at) - (now or datetime.now())).total_seconds() / 86400
        if days < 0:
            return {"score": 0, "decision": "no_bid", "reasons": ["The deadline has passed"]}
        if days < 3:
            score -= 30
            reasons.append("Less than 3 days left")
        elif days < 7:
            score -= 15
            reasons.append("Less than a week left")
    if output.get("concessions") and output["concessions"].items:
        score += 5
        reasons.append("You can claim: " + "; ".join(c.benefit for c in output["concessions"].items))
    score = max(0, min(100, score))
    decision = "bid" if score >= 70 else "bid_with_care" if score >= 40 else "no_bid"
    if not reasons:
        reasons.append("You meet every rule and hold every document")
    return {"score": score, "decision": decision, "reasons": reasons}
