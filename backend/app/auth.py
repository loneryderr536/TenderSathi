"""Small login system: salted password hashes, random session tokens, and role checks for the routes.

Roles: "business" (a small business owner), "government" (a buyer department), "platform" (the TenderSathi team).
"""
import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request

from app import db
from app.routes.deps import get_conn

ROLES = ("business", "government", "platform")
ITERATIONS = 200_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f"{salt}${digest}"


def check_password(password: str, stored: str) -> bool:
    salt, _, _ = stored.partition("$")
    return hmac.compare_digest(hash_password(password, salt), stored)


def start_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db.create_session(conn, token, user_id)
    return token


def token_from(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    return header[len("Bearer "):].strip() if header.startswith("Bearer ") else ""


def optional_user(request: Request, conn=Depends(get_conn)) -> dict | None:
    token = token_from(request)
    return db.user_for_token(conn, token) if token else None


def current_user(user=Depends(optional_user)) -> dict:
    if user is None:
        raise HTTPException(401, "Please log in")
    return user


def government_user(user=Depends(current_user)) -> dict:
    """Government buyers, and the platform team (who can see every view)."""
    if user["role"] not in ("government", "platform"):
        raise HTTPException(403, "This page is for government buyers")
    return user


def platform_user(user=Depends(current_user)) -> dict:
    if user["role"] != "platform":
        raise HTTPException(403, "This page is for the TenderSathi platform team")
    return user
