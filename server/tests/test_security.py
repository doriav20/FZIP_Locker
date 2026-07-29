"""Password hashing and token tests."""

from __future__ import annotations

import base64
import time

import jwt
import pytest
from argon2 import PasswordHasher

from fzip_server.config import Settings, get_settings
from fzip_server.errors import AuthenticationRequiredError, TokenExpiredError
from fzip_server.security import (
    AUDIENCE,
    ISSUER,
    build_hasher,
    create_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


@pytest.fixture
def hasher(settings: Settings) -> PasswordHasher:
    return build_hasher(settings)


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def test_hash_is_argon2id(hasher):
    assert hash_password(hasher, "a-long-enough-password").startswith("$argon2id$")


def test_hashes_are_salted(hasher):
    """Identical passwords must not produce identical hashes."""
    a = hash_password(hasher, "same-password-here")
    b = hash_password(hasher, "same-password-here")
    assert a != b


def test_correct_password_verifies(hasher):
    stored = hash_password(hasher, "a-long-enough-password")
    ok, upgraded = verify_password(hasher, stored, "a-long-enough-password")
    assert ok
    assert upgraded is None


def test_wrong_password_fails(hasher):
    stored = hash_password(hasher, "a-long-enough-password")
    ok, _ = verify_password(hasher, stored, "not-the-password")
    assert not ok


def test_corrupt_hash_fails_closed(hasher):
    """A mangled stored hash must be a failure, not an exception."""
    ok, _ = verify_password(hasher, "$argon2id$garbage", "anything")
    assert not ok


def test_weaker_stored_parameters_trigger_a_rehash(settings: Settings):
    """This is how the cost factor rises without forcing a password reset."""
    weak = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
    stored = weak.hash("a-long-enough-password")

    strong = PasswordHasher(time_cost=4, memory_cost=65536, parallelism=2)
    ok, upgraded = verify_password(strong, stored, "a-long-enough-password")

    assert ok
    assert upgraded is not None
    assert upgraded != stored
    # And the upgraded hash still verifies.
    assert verify_password(strong, upgraded, "a-long-enough-password")[0]


def test_unicode_passwords_round_trip(hasher):
    secret = "пароль-с-юникодом-🔒"
    assert verify_password(hasher, hash_password(hasher, secret), secret)[0]


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------
def test_access_token_round_trips(settings: Settings):
    token = create_token(settings, "user-1", "access", 60)
    payload = decode_token(settings, token, "access")
    assert payload["sub"] == "user-1"
    assert payload["typ"] == "access"


def test_token_is_signed_with_eddsa(settings: Settings):
    header = jwt.get_unverified_header(create_token(settings, "u", "access", 60))
    assert header["alg"] == "EdDSA"
    assert header["kid"] == settings.jwt_key_id


def test_face_token_is_not_accepted_as_access(settings: Settings):
    """Without the `typ` claim the two kinds would be interchangeable."""
    token = create_token(settings, "user-1", "face", 60)
    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, token, "access")


def test_access_token_is_not_accepted_as_face(settings: Settings):
    token = create_token(settings, "user-1", "access", 60)
    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, token, "face")


def test_expired_token_is_rejected(settings: Settings):
    token = create_token(settings, "user-1", "access", -1)
    with pytest.raises(TokenExpiredError):
        decode_token(settings, token, "access")


def test_tampered_token_is_rejected(settings: Settings):
    token = create_token(settings, "user-1", "access", 60)
    head, payload, signature = token.split(".")
    forged = f"{head}.{payload}.{signature[:-4]}AAAA"
    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, forged, "access")


def test_unsigned_token_is_rejected(settings: Settings):
    """The classic `alg: none` downgrade. Pinning algorithms blocks it."""
    forged = jwt.encode(
        {"sub": "user-1", "typ": "access", "iss": ISSUER, "aud": AUDIENCE,
         "iat": int(time.time()), "exp": int(time.time()) + 60},
        key="",
        algorithm="none",
    )
    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, forged, "access")


def test_token_signed_by_another_key_is_rejected(settings: Settings):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    attacker_pem = Ed25519PrivateKey.generate().private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    other = settings.model_copy(
        update={"jwt_private_key": base64.b64encode(attacker_pem).decode()}
    )
    forged = create_token(other, "user-1", "access", 60)

    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, forged, "access")


def test_wrong_audience_is_rejected(settings: Settings):
    """A token minted by us but for a different audience must not be accepted."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    forged = jwt.encode(
        {
            "sub": "u",
            "typ": "access",
            "iss": ISSUER,
            "aud": "somewhere-else",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        },
        load_pem_private_key(settings.jwt_private_key_pem, password=None),
        algorithm="EdDSA",
    )
    with pytest.raises(AuthenticationRequiredError):
        decode_token(settings, forged, "access")


def test_tokens_have_unique_ids(settings: Settings):
    jtis = {
        decode_token(settings, create_token(settings, "u", "access", 60), "access")["jti"]
        for _ in range(20)
    }
    assert len(jtis) == 20


# --------------------------------------------------------------------------
# Refresh tokens
# --------------------------------------------------------------------------
def test_refresh_tokens_are_high_entropy_and_unique():
    tokens = {generate_refresh_token() for _ in range(500)}
    assert len(tokens) == 500
    assert all(len(t) >= 32 for t in tokens)


def test_refresh_hash_is_deterministic_and_not_the_token():
    token = generate_refresh_token()
    assert hash_refresh_token(token) == hash_refresh_token(token)
    assert hash_refresh_token(token) != token
    assert len(hash_refresh_token(token)) == 64  # sha256 hex


# --------------------------------------------------------------------------
# Settings validation
# --------------------------------------------------------------------------
def test_short_biometric_key_is_refused(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("FZIP_BIOMETRIC_KEY", base64.b64encode(b"too-short").decode())
    with pytest.raises(ValueError, match="32 bytes"):
        Settings()  # type: ignore[call-arg]
    get_settings.cache_clear()


def test_non_base64_biometric_key_is_refused(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("FZIP_BIOMETRIC_KEY", "not base64 at all !!!")
    with pytest.raises(ValueError, match="base64"):
        Settings()  # type: ignore[call-arg]
    get_settings.cache_clear()


def test_argon2_memory_below_owasp_floor_is_refused(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("FZIP_ARGON2_MEMORY_KIB", "4096")
    with pytest.raises(ValueError):
        Settings()  # type: ignore[call-arg]
    get_settings.cache_clear()
