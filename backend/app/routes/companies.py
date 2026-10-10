"""Endpoints for the business profile and its documents."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import auth, db
from app.routes.deps import get_conn

router = APIRouter(prefix="/companies", tags=["companies"])


class PastOrder(BaseModel):
    buyer: str
    item: str
    value: str
    year: int


class CompanyIn(BaseModel):
    id: int | None = None
    name: str
    products: str
    location: str
    turnover: str
    udyam: bool
    documents: list[str] = []
    past_orders: list[PastOrder] = []


@router.post("")
def save_company(body: CompanyIn, conn=Depends(get_conn), user=Depends(auth.optional_user)):
    """Create the profile, or update it when an id is given. A logged-in owner's first profile becomes theirs."""
    fields = body.model_dump(exclude={"id"})
    if body.id is None:
        company_id = db.create_company(conn, **fields)
        if user and user["role"] == "business" and user["company_id"] is None:
            db.set_user_company(conn, user["id"], company_id)
        return {"id": company_id}
    if not db.update_company(conn, body.id, **fields):
        raise HTTPException(404, "Company not found")
    return {"id": body.id}


@router.get("/{company_id}")
def read_company(company_id: int, conn=Depends(get_conn)):
    company = db.get_company(conn, company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    return {**company, "udyam": bool(company["udyam"])}
