#!/usr/bin/env python3
"""Generate the secrets required by .env.

    docker compose run --rm --no-deps --entrypoint python api scripts/gen_secrets.py

Prints ready-to-paste lines. Nothing is written to disk, so this never
accidentally creates a file that a future commit could pick up -- which is
precisely how the 2022 version's key.key ended up in git history.
"""

from __future__ import annotations

import base64
import secrets
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)


def biometric_key() -> str:
    """32 bytes for AES-256-GCM wrapping of face embeddings."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


def jwt_private_key() -> str:
    """Ed25519 private key as base64-wrapped PKCS#8 PEM.

    Base64 so the multi-line PEM survives a single-line .env entry.
    """
    pem = Ed25519PrivateKey.generate().private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )
    return base64.b64encode(pem).decode("ascii")


def password(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def main() -> int:
    print("# --- generated secrets: paste into .env, then keep .env out of git ---")
    print(f"MONGO_ROOT_PASSWORD={password()}")
    print(f"MONGO_APP_PASSWORD={password()}")
    print(f"FZIP_BIOMETRIC_KEY={biometric_key()}")
    print(f"FZIP_JWT_PRIVATE_KEY={jwt_private_key()}")
    print()
    print("# Rotating FZIP_BIOMETRIC_KEY makes existing enrolled faces unreadable")
    print("# until they are rewrapped. Rotating FZIP_JWT_PRIVATE_KEY invalidates")
    print("# every access token immediately; refresh tokens keep working.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
