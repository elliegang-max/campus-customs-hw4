"""Password storage and session tokens.

Everything that touches a password lives in this module, so there is exactly one
place to audit. Two rules hold throughout:

1. A plaintext password is never stored, never logged, and never returned by an
   endpoint. It exists only as a local variable for the microseconds it takes to
   hash it.
2. The stored hash is never returned by an endpoint either, and no query in this
   project does `SELECT *` on the users table.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

# --- Password hashing ------------------------------------------------------

ALGORITHM = "pbkdf2_sha256"

# PBKDF2-HMAC-SHA256 is in the standard library, which keeps this dependency
# free, and is an accepted choice when the iteration count is high enough.
# 600,000 is the current OWASP recommendation for SHA-256.
ITERATIONS = 600_000

SALT_BYTES = 16

# Rows that shipped with the database use a three-part `algorithm$salt$hash`
# string with no iteration count in it. The count is not recorded anywhere, so
# it was recovered empirically: deriving the seed test user's known password
# against the stored salt reproduces the stored digest only at 120,000
# iterations. New hashes written by this app use a four-part string that states
# its own count, so a future change to ITERATIONS cannot silently invalidate
# stored passwords.
LEGACY_ITERATIONS = 120_000

MIN_PASSWORD_LENGTH = 8

# Hashing cost is paid by the server, so an unbounded password is a cheap way to
# tie up a worker. Long passphrases still fit comfortably.
MAX_PASSWORD_LENGTH = 256


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """Return `pbkdf2_sha256$iterations$salt$hash`, with a fresh random salt.

    The salt is per-password, so two users who choose the same password still
    get different hashes and a precomputed table is useless.
    """
    salt = secrets.token_hex(SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return f"{ALGORITHM}${iterations}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time.

    Returns False rather than raising on a malformed or unknown-format hash, so
    a damaged row fails closed instead of crashing the login endpoint.
    """
    if not stored:
        return False

    parts = stored.split("$")
    if len(parts) == 4:
        algorithm, raw_iterations, salt, expected = parts
        try:
            iterations = int(raw_iterations)
        except ValueError:
            return False
    elif len(parts) == 3:
        algorithm, salt, expected = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False

    if algorithm != ALGORITHM:
        return False

    digest = _derive(password, salt, iterations)
    # compare_digest, not ==, so the time taken does not leak how much of the
    # hash matched.
    return hmac.compare_digest(digest, expected)


def needs_rehash(stored: str) -> bool:
    """True when a stored hash is weaker than what we write today."""
    parts = stored.split("$")
    if len(parts) != 4:
        return True
    try:
        return int(parts[1]) < ITERATIONS
    except ValueError:
        return True


def _derive(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()


# --- Session tokens --------------------------------------------------------

SESSION_TTL_SECONDS = 14 * 24 * 60 * 60  # two weeks

_SECRET_ENV_VAR = "CAMPUS_CUSTOMS_SECRET_KEY"

# A random secret means tokens are valid only for the life of the process. That
# is fine for development; set the environment variable to keep sessions across
# restarts.
SECRET_KEY = os.environ.get(_SECRET_ENV_VAR) or secrets.token_hex(32)
SECRET_IS_EPHEMERAL = _SECRET_ENV_VAR not in os.environ


def create_session_token(user_id: int, *, ttl: int = SESSION_TTL_SECONDS) -> str:
    """Sign `user_id|expiry` so the cookie cannot be edited by the client.

    The token carries no secret material — only an id and an expiry — so the
    signature is what makes it trustworthy, not obscurity.
    """
    payload = f"{user_id}|{int(time.time()) + ttl}"
    return f"{_b64(payload.encode())}.{_b64(_sign(payload))}"


def read_session_token(token: str) -> int | None:
    """Return the user id in a valid, unexpired token, else None."""
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = _unb64(encoded_payload).decode("utf-8")
        signature = _unb64(encoded_signature)
    except (ValueError, UnicodeDecodeError):
        return None

    if not hmac.compare_digest(signature, _sign(payload)):
        return None

    try:
        raw_user_id, raw_expiry = payload.split("|", 1)
        user_id, expiry = int(raw_user_id), int(raw_expiry)
    except ValueError:
        return None

    return user_id if expiry > time.time() else None


def _sign(payload: str) -> bytes:
    return hmac.new(
        SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)
