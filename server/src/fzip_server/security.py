"""Password hashing, token issuance and verification.

Three deliberate departures from the 2022 implementation:

* **Passwords are hashed, not encrypted.** The old server encrypted them with
  a key computed as ``pickle.dumps(creation_time)[7:39]`` -- and stored
  ``creation_time`` in plaintext in the same document, so anyone who could
  read the database could reverse every password. Argon2id is one-way; there
  is nothing to reverse.

* **Tokens are signed with Ed25519, not a shared secret.** An HS256 secret has
  to be known by every party that verifies a token. An asymmetric key means
  the private half never has to leave this service.

* **Refresh tokens rotate and detect reuse.** A token presented twice means it
  was captured, so the entire family is revoked.
"""

from __future__ import annotations

import contextlib
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from .config import Settings
from .errors import AuthenticationRequiredError, TokenExpiredError

ISSUER = "fzip-locker"
AUDIENCE = "fzip-client"

TokenType = Literal["access", "face"]


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def build_hasher(settings: Settings) -> PasswordHasher:
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_kib,
        parallelism=settings.argon2_parallelism,
        hash_len=32,
        salt_len=16,
    )


def hash_password(hasher: PasswordHasher, password: str) -> str:
    return hasher.hash(password)


def verify_password(
    hasher: PasswordHasher, stored_hash: str, password: str
) -> tuple[bool, str | None]:
    """Verify a password, returning ``(ok, upgraded_hash)``.

    ``upgraded_hash`` is non-None when the stored hash used weaker parameters
    than the current settings, letting the caller transparently re-hash on a
    successful login. This is how the cost factor gets raised over time
    without forcing a password reset.
    """
    try:
        hasher.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, None

    if hasher.check_needs_rehash(stored_hash):
        return True, hasher.hash(password)
    return True, None


#: A real Argon2id hash of a fixed dummy password, used to burn the same CPU
#: time when an account does not exist. Without it, a failed login for an
#: unknown email returns measurably faster than one for a known email, which
#: is enough to enumerate accounts.
_DUMMY_PASSWORD = "fzip-timing-equaliser"  # noqa: S105 - not a credential
_dummy_hash_cache: dict[int, str] = {}


def burn_password_time(hasher: PasswordHasher) -> None:
    key = id(hasher)
    stored = _dummy_hash_cache.get(key)
    if stored is None:
        stored = hasher.hash(_DUMMY_PASSWORD)
        _dummy_hash_cache[key] = stored
    with contextlib.suppress(VerifyMismatchError, VerificationError, InvalidHashError):
        hasher.verify(stored, "wrong")


# --------------------------------------------------------------------------
# JWTs
# --------------------------------------------------------------------------
def _private_key(settings: Settings) -> Any:
    return load_pem_private_key(settings.jwt_private_key_pem, password=None)


def _public_key(settings: Settings) -> Any:
    return _private_key(settings).public_key()


def create_token(
    settings: Settings,
    subject: str,
    token_type: TokenType,
    ttl_seconds: int,
    **claims: Any,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        # `typ` stops a short-lived face token being presented as an access
        # token, or vice versa. Without it the two are interchangeable.
        "typ": token_type,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
        "jti": secrets.token_urlsafe(16),
        **claims,
    }
    return jwt.encode(
        payload,
        _private_key(settings),
        algorithm="EdDSA",
        headers={"kid": settings.jwt_key_id},
    )


def decode_token(settings: Settings, token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            _public_key(settings),
            # Pinning the algorithm list is what prevents the classic "alg:
            # none" and HS256-confusion attacks, where an attacker re-signs a
            # token using the public key as an HMAC secret.
            algorithms=["EdDSA"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationRequiredError("Invalid token.") from exc

    if payload.get("typ") != expected_type:
        raise AuthenticationRequiredError("Token is not valid for this operation.")
    return payload


# --------------------------------------------------------------------------
# Refresh tokens
# --------------------------------------------------------------------------
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Store only the digest.

    A refresh token is high-entropy random data, not a password, so a fast
    hash is correct here: there is no dictionary to attack. Argon2 would add
    latency to every refresh for no security gain.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
