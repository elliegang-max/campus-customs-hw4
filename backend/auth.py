"""Create-account and log-in endpoints.

The session lives in an HttpOnly cookie, so page JavaScript cannot read it and
an XSS bug cannot exfiltrate it. The cookie holds a signed `user_id|expiry` and
nothing else — no name, no email, and certainly no password material.
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field

from db import get_conn, get_write_conn
from security import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    SESSION_TTL_SECONDS,
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "campus_customs_session"

# Every column of `users` except password_hash. Nothing in this project selects
# the hash into a response model, and `SELECT *` is avoided so a future column
# cannot leak by accident.
USER_COLUMNS = "id, name, first_name, last_name, email, created_at"


# --- Models ----------------------------------------------------------------


class SignUpRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class LogInRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LENGTH)


class User(BaseModel):
    """What the client is allowed to know about an account."""

    id: int
    name: str
    first_name: str | None
    last_name: str | None
    email: str
    created_at: str


# --- Helpers ---------------------------------------------------------------


def _normalise_email(email: str) -> str:
    """Emails are case-insensitive in practice; store and compare one form."""
    return email.strip().lower()


def _set_session_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session_token(user_id),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,  # unreadable from JavaScript
        samesite="lax",  # not sent on cross-site POSTs, which blunts CSRF
        secure=False,  # dev is plain http; set True behind HTTPS
        path="/",
    )


def _load_user(conn: sqlite3.Connection, user_id: int) -> User | None:
    row = conn.execute(
        f"SELECT {USER_COLUMNS} FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return User(**dict(row)) if row else None


def current_user(session: str | None) -> User | None:
    """Resolve the signed cookie to a user, or None."""
    if not session:
        return None
    user_id = read_session_token(session)
    if user_id is None:
        return None
    with get_conn() as conn:
        return _load_user(conn, user_id)


# --- Endpoints -------------------------------------------------------------


@router.post("/signup", response_model=User, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest, response: Response) -> User:
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = _normalise_email(payload.email)

    # Hash before touching the database; the plaintext goes no further than here.
    password_hash = hash_password(payload.password)
    display_name = f"{first_name} {last_name}".strip()

    try:
        with get_write_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (name, first_name, last_name, email, password_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (display_name, first_name, last_name, email, password_hash),
            )
            user_id = int(cursor.lastrowid or 0)
            user = _load_user(conn, user_id)
    except sqlite3.IntegrityError as exc:
        # The UNIQUE constraint on email is the authority here, not a prior
        # SELECT, which two simultaneous signups could both pass.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        ) from exc

    if user is None:  # pragma: no cover - only if the insert vanished
        raise HTTPException(status_code=500, detail="Account could not be created.")

    _set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=User)
def log_in(payload: LogInRequest, response: Response) -> User:
    email = _normalise_email(payload.email)

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()

    # One message and one code path for "no such account" and "wrong password",
    # so the endpoint cannot be used to discover which emails are registered.
    if row is None or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    with get_conn() as conn:
        user = _load_user(conn, int(row["id"]))

    if user is None:  # pragma: no cover
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    _set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def log_out(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=User | None)
def me(campus_customs_session: str | None = Cookie(default=None)) -> User | None:
    """Who the browser is signed in as, if anyone. Never 401s — the front end
    calls this on load and 'nobody' is a normal answer."""
    return current_user(campus_customs_session)
