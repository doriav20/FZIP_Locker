from __future__ import annotations

import secrets

import pytest

from fzip_client import crypto

#: Deliberately cheap Argon2id parameters so the suite stays fast. Production
#: defaults (64 MiB, t=3) are exercised separately in test_crypto.py.
CHEAP_KDF_KWARGS = {"time_cost": 1, "memory_kib": 8192, "parallelism": 1}


@pytest.fixture
def cheap_kdf() -> crypto.KdfParams:
    return crypto.KdfParams(salt=secrets.token_bytes(crypto.SALT_SIZE), **CHEAP_KDF_KWARGS)


@pytest.fixture
def password() -> str:
    return "correct horse battery staple"
