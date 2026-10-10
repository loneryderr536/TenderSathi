"""Sign up, log in, log out, and who is logged in."""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app import auth, db
from app.routes.deps import get_conn

router = APIRouter(prefix="/auth", tags=["auth"])

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupIn(BaseModel):
    name: str
    email: str
    password: str
    role: str
    department: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str
    role: str | None = None   # the dashboard the person chose; the account must belong to it


def _session(conn, user_id: int) -> dict:
    return {"token": auth.start_session(conn, user_id), "user": db.get_user(conn, user_id)}


@router.post("/signup")
def signup(body: SignupIn, conn=Depends(get_conn)):
    """Business owners, government buyers and private owners sign up here; platform accounts come only from the seed."""
    email = body.email.strip().lower()
    if body.role not in ("business", "government", "private"):
        raise HTTPException(400, "Choose a business, government or private owner account")
    if not body.name.strip():
        raise HTTPException(400, "Please enter your name")
    if not EMAIL.match(email):
        raise HTTPException(400, "Please enter a valid email address")
    if len(body.password) < 8:
        raise HTTPException(400, "Use a password of at least 8 characters")
    if body.role == "government" and not (body.department or "").strip():
        raise HTTPException(400, "Please enter your department")
    if body.role == "private" and not (body.department or "").strip():
        raise HTTPException(400, "Please enter your organisation")
    if db.user_by_email(conn, email):
        raise HTTPException(409, "An account with this email already exists")
    user_id = db.create_user(conn, email, body.name.strip(), body.role, auth.hash_password(body.password),
                             department=(body.department or "").strip() or None)
    return _session(conn, user_id)


@router.post("/login")
def login(body: LoginIn, conn=Depends(get_conn)):
    user = db.user_by_email(conn, body.email.strip().lower())
    if user is None or not auth.check_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    if body.role is not None and user["role"] != body.role:
        raise HTTPException(403, f"This is not a {body.role} account. "
                                 "Choose the dashboard that matches your account.")
    return _session(conn, user["id"])


@router.get("/me")
def me(user=Depends(auth.current_user)):
    return user


@router.post("/logout")
def logout(request: Request, conn=Depends(get_conn)):
    token = auth.token_from(request)
    if token:
        db.delete_session(conn, token)
    return {"ok": True}
