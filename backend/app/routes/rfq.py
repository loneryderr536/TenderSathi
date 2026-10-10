"""Private owners' requests for quotation (RFQ): post one, receive businesses' quotations, accept one."""
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import auth, db, rfq
from app.routes.deps import get_conn, get_storage
from app.routes.tenders import _tender_or_404

router = APIRouter(prefix="/rfq", tags=["private owners"])


class RfqIn(BaseModel):
    title: str
    scope: str
    requirements: list[str] = []
    documents: list[str] = []
    deadline: str
    delivery_days: int
    advance_percent: int


def post_rfq(conn, storage, user: dict, body: RfqIn) -> int:
    """Checks the form, writes the RFQ document and puts it in businesses' inboxes."""
    if not rfq.MIN_ADVANCE <= body.advance_percent <= rfq.MAX_ADVANCE:
        raise HTTPException(400, f"The advance must be between {rfq.MIN_ADVANCE}% and {rfq.MAX_ADVANCE}% of the order value")
    if not body.title.strip() or not body.scope.strip() or not body.deadline.strip():
        raise HTTPException(400, "Please fill in the title, scope and deadline")
    if body.delivery_days <= 0:
        raise HTTPException(400, "Delivery days must be more than 0")
    buyer = user["department"] or user["name"]
    folder = Path(storage) / "tenders"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"rfq-{uuid4().hex}.pdf"
    rfq.write_rfq_pdf(path, rfq.rfq_lines(
        buyer, body.title.strip(), body.scope.strip(), [r.strip() for r in body.requirements if r.strip()],
        [d.strip() for d in body.documents if d.strip()], body.deadline.strip(), body.delivery_days, body.advance_percent))
    return db.create_tender(conn, str(path), body.title.strip(), kind="private", portal="Private RFQ", buyer=buyer,
                            published=date.today().isoformat(), owner_user_id=user["id"],
                            advance_percent=body.advance_percent)


def _own_rfq(conn, tender_id: int, user: dict) -> dict:
    tender = _tender_or_404(conn, tender_id)
    if tender["kind"] != "private" or (user["role"] == "private" and tender["owner_user_id"] != user["id"]):
        raise HTTPException(404, "Request not found")
    return tender


@router.post("")
def create(body: RfqIn, conn=Depends(get_conn), storage=Depends(get_storage), user=Depends(auth.private_user)):
    return {"id": post_rfq(conn, storage, user, body)}


@router.get("/mine")
def mine(conn=Depends(get_conn), user=Depends(auth.private_user)):
    """The owner's requests, newest first, with how many quotations each has."""
    out = []
    for t in db.list_tenders(conn, kinds=("private",)):
        if user["role"] == "private" and t["owner_user_id"] != user["id"]:
            continue
        quotes = db.list_quotations(conn, t["id"])
        out.append({**t, "quotations": len(quotes),
                    "lowest": min((q["amount"] for q in quotes), default=None),
                    "accepted": next((q["company_name"] for q in quotes if q["status"] == "accepted"), None)})
    return out


@router.get("/{tender_id}/quotations")
def quotations(tender_id: int, conn=Depends(get_conn), user=Depends(auth.private_user)):
    _own_rfq(conn, tender_id, user)
    return db.list_quotations(conn, tender_id)


@router.post("/{tender_id}/quotations/{quotation_id}/accept")
def accept(tender_id: int, quotation_id: int, conn=Depends(get_conn), user=Depends(auth.private_user)):
    tender = _own_rfq(conn, tender_id, user)
    if tender["status"] == "awarded":
        raise HTTPException(409, "A quotation has already been accepted")
    if not db.accept_quotation(conn, tender_id, quotation_id):
        raise HTTPException(404, "Quotation not found")
    return {"status": "awarded"}


class QuoteIn(BaseModel):
    amount: float
    delivery_days: int
    note: str = ""


@router.post("/{tender_id}/quote")
def send_quote(tender_id: int, body: QuoteIn, conn=Depends(get_conn), user=Depends(auth.business_user)):
    """A business sends (or replaces) its quotation. The price is the business's own; TenderSathi never sets it."""
    tender = _tender_or_404(conn, tender_id)
    if tender["kind"] != "private":
        raise HTTPException(400, "Quotations are only for private requests")
    if tender["status"] == "awarded":
        raise HTTPException(409, "This request has already been awarded")
    if user["company_id"] is None:
        raise HTTPException(400, "Fill in your business profile before sending a quotation")
    if body.amount <= 0 or body.delivery_days <= 0:
        raise HTTPException(400, "Enter a price and delivery days above 0")
    db.save_quotation(conn, tender_id, user["company_id"], body.amount, body.delivery_days, body.note.strip())
    return my_quote(tender_id, conn, user)


@router.get("/{tender_id}/my-quote")
def my_quote(tender_id: int, conn=Depends(get_conn), user=Depends(auth.business_user)):
    return next((q for q in db.list_quotations(conn, tender_id) if q["company_id"] == user["company_id"]), None)
