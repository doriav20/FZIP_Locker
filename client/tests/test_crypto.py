from __future__ import annotations

import pytest

from fzip_client import crypto
from fzip_client.errors import DecryptionError, MalformedVaultError


def test_key_derivation_is_deterministic(cheap_kdf):
    assert crypto.derive_key("pw", cheap_kdf) == crypto.derive_key("pw", cheap_kdf)


def test_different_salts_give_different_keys():
    a = crypto.KdfParams(salt=b"A" * 16, time_cost=1, memory_kib=8192, parallelism=1)
    b = crypto.KdfParams(salt=b"B" * 16, time_cost=1, memory_kib=8192, parallelism=1)
    assert crypto.derive_key("pw", a) != crypto.derive_key("pw", b)


def test_derived_key_is_256_bits(cheap_kdf):
    assert len(crypto.derive_key("pw", cheap_kdf)) == crypto.KEY_SIZE == 32


def test_production_defaults_meet_owasp_floor():
    """OWASP's current Argon2id floor is t=2, m=19 MiB, p=1. Stay above it."""
    assert crypto.DEFAULT_TIME_COST >= 2
    assert crypto.DEFAULT_MEMORY_KIB >= 19 * 1024
    assert crypto.DEFAULT_PARALLELISM >= 1


def test_secure_zero_clears_the_buffer():
    buf = bytearray(b"sensitive key material")
    crypto.secure_zero(buf)
    assert set(buf) == {0}


def test_nonces_are_unique_per_chunk():
    base = b"12345678"
    nonces = {crypto._nonce(base, i) for i in range(10_000)}
    assert len(nonces) == 10_000
    assert all(len(n) == crypto.NONCE_SIZE for n in nonces)


def test_chunk_round_trip():
    key = bytes(range(32))
    base = b"nonce123"
    aad = b"header"
    plain = [b"one", b"two", b"three"]

    sealed = list(crypto.encrypt_chunks(key, base, aad, plain))
    assert list(crypto.decrypt_chunks(key, base, aad, sealed)) == plain


def test_wrong_aad_fails():
    key = bytes(range(32))
    sealed = list(crypto.encrypt_chunks(key, b"nonce123", b"header-a", [b"data"]))
    with pytest.raises(DecryptionError):
        list(crypto.decrypt_chunks(key, b"nonce123", b"header-b", sealed))


def test_wrong_key_fails():
    sealed = list(crypto.encrypt_chunks(bytes(32), b"nonce123", b"aad", [b"data"]))
    with pytest.raises(DecryptionError):
        list(crypto.decrypt_chunks(bytes(range(32)), b"nonce123", b"aad", sealed))


def test_ciphertext_expands_by_exactly_the_tag_size():
    sealed = list(crypto.encrypt_chunks(bytes(32), b"nonce123", b"", [b"x" * 1000]))
    assert len(sealed[0]) == 1000 + crypto.GCM_TAG_SIZE


# --------------------------------------------------------------------------
# Header parameter validation - a hostile file must not be able to make us
# allocate unbounded memory or spin forever before the password is checked.
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "override",
    [
        pytest.param({"m": 4096}, id="memory-too-low"),
        pytest.param({"m": 2 * 1024 * 1024}, id="memory-too-high"),
        pytest.param({"t": 0}, id="time-zero"),
        pytest.param({"t": 999}, id="time-too-high"),
        pytest.param({"p": 0}, id="parallelism-zero"),
        pytest.param({"p": 999}, id="parallelism-too-high"),
        pytest.param({"salt": "c2hvcnQ="}, id="salt-too-short"),
        pytest.param({"alg": "scrypt"}, id="unknown-algorithm"),
    ],
)
def test_hostile_kdf_parameters_are_rejected(override, cheap_kdf):
    payload = cheap_kdf.to_json() | override
    with pytest.raises(MalformedVaultError):
        crypto.KdfParams.from_json(payload)


def test_kdf_params_survive_a_json_round_trip(cheap_kdf):
    assert crypto.KdfParams.from_json(cheap_kdf.to_json()) == cheap_kdf


def test_generated_salts_are_random():
    salts = {crypto.KdfParams.generate().salt for _ in range(200)}
    assert len(salts) == 200
