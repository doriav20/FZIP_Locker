"""Application settings.

Every secret is required and validated at import time. There are deliberately
no fallback defaults for key material: a missing ``FZIP_BIOMETRIC_KEY`` stops
the process with a clear error rather than quietly starting up with a
predictable value. The 2022 server did the opposite -- credentials were
hardcoded in source, so there was nothing to forget and nothing to rotate.
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FZIP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- app ---------------------------------------------------------------
    env: Literal["development", "production"] = "development"
    log_level: str = "INFO"

    # --- database ----------------------------------------------------------
    #: Assembled by Compose from the least-privilege app credentials. The app
    #: user has readWrite on this database only - never the root account.
    mongo_uri: str
    mongo_db: str = "fzip"

    # --- key material ------------------------------------------------------
    #: 32 random bytes, base64. Wraps face embeddings at rest.
    biometric_key: str
    #: Ed25519 private key, PKCS#8 PEM, base64-encoded to survive .env.
    jwt_private_key: str
    jwt_key_id: str = "k1"

    # --- token lifetimes ---------------------------------------------------
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 2_592_000
    face_challenge_ttl_seconds: int = 60
    face_token_ttl_seconds: int = 120

    # --- face recognition --------------------------------------------------
    #: SFace's calibrated cosine threshold. Above this counts as a match.
    face_match_threshold: float = Field(default=0.363, ge=0.0, le=1.0)
    #: Frames a client must supply to satisfy a head-turn liveness challenge.
    face_liveness_frames: int = Field(default=5, ge=2, le=30)
    model_dir: Path = Path("/app/models")

    # --- rate limiting -----------------------------------------------------
    login_max_attempts: int = Field(default=6, ge=1)
    login_lockout_seconds: int = Field(default=900, ge=1)

    # --- password hashing --------------------------------------------------
    argon2_time_cost: int = Field(default=3, ge=2)
    argon2_memory_kib: int = Field(default=65536, ge=19456)  # OWASP floor
    argon2_parallelism: int = Field(default=4, ge=1)

    # --- smtp --------------------------------------------------------------
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from: str = "noreply@fziplocker.local"

    # ----------------------------------------------------------------------
    @field_validator("biometric_key")
    @classmethod
    def _validate_biometric_key(cls, value: str) -> str:
        try:
            raw = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                "FZIP_BIOMETRIC_KEY must be base64. "
                "Generate one with: python -m scripts.gen_secrets"
            ) from exc
        if len(raw) != 32:
            raise ValueError(f"FZIP_BIOMETRIC_KEY must decode to exactly 32 bytes, got {len(raw)}")
        return value

    @field_validator("jwt_private_key")
    @classmethod
    def _validate_jwt_key(cls, value: str) -> str:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        try:
            pem = base64.b64decode(value, validate=True)
            key = load_pem_private_key(pem, password=None)
        except Exception as exc:
            raise ValueError(
                "FZIP_JWT_PRIVATE_KEY must be a base64-encoded PKCS#8 PEM Ed25519 key. "
                "Generate one with: python -m scripts.gen_secrets"
            ) from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("FZIP_JWT_PRIVATE_KEY must be an Ed25519 key")
        return value

    # --- decoded accessors -------------------------------------------------
    @property
    def biometric_key_bytes(self) -> bytes:
        return base64.b64decode(self.biometric_key)

    @property
    def jwt_private_key_pem(self) -> bytes:
        return base64.b64decode(self.jwt_private_key)

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Field values come from the environment; the pydantic mypy plugin knows
    # this constructor takes no arguments.
    return Settings()
