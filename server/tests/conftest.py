"""Test fixtures.

Two deliberate choices:

* **Mongo is real.** Tests run against the ``mongo`` service from
  compose.yaml, each in a throwaway database. Unique-index enforcement, TTL
  semantics and ``find_one_and_update`` atomicity are precisely the things a
  mock would fake incorrectly, and they are load-bearing here.

* **The face engine is fake.** Producing real photographs that a CNN detects,
  from inside a test, is not practical. The route tests use a stub driven by
  the uploaded bytes, so a test can state "this frame shows Alice, turned 0.3
  to the left" directly. The real engine's arithmetic is covered as pure
  functions in test_biometrics.py.
"""

from __future__ import annotations

import base64
import os
import secrets
import uuid
from collections.abc import AsyncIterator
from typing import Any

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Environment must be populated before fzip_server.config is imported, because
# Settings validates its key material at construction time.
# ---------------------------------------------------------------------------
def _ed25519_key_b64() -> str:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )

    pem = Ed25519PrivateKey.generate().private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    return base64.b64encode(pem).decode()


os.environ.setdefault("FZIP_MONGO_URI", "mongodb://mongo:27017")
os.environ.setdefault("FZIP_BIOMETRIC_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
os.environ.setdefault("FZIP_JWT_PRIVATE_KEY", _ed25519_key_b64())
# Argon2 at the OWASP floor: enough to exercise the real code path without the
# suite being dominated by key stretching.
os.environ.setdefault("FZIP_ARGON2_TIME_COST", "2")
os.environ.setdefault("FZIP_ARGON2_MEMORY_KIB", "19456")
os.environ.setdefault("FZIP_ARGON2_PARALLELISM", "1")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from pymongo.errors import PyMongoError  # noqa: E402

from fzip_server.biometrics import DetectedFace  # noqa: E402
from fzip_server.config import Settings, get_settings  # noqa: E402
from fzip_server.db import Database  # noqa: E402
from fzip_server.deps import (  # noqa: E402
    get_app_settings,
    get_database,
    get_db,
    get_face_engine,
    get_hasher,
)
from fzip_server.main import create_app  # noqa: E402
from fzip_server.security import build_hasher  # noqa: E402

EMBEDDING_DIM = 128


# ---------------------------------------------------------------------------
# Fake face engine
# ---------------------------------------------------------------------------
def frame(identity: str = "alice", yaw: float = 0.0) -> bytes:
    """Build a synthetic 'frame' that the fake engine interprets."""
    return f"IDENTITY:{identity};YAW:{yaw}".encode()


def make_detected_face(yaw: float) -> DetectedFace:
    """A YuNet-shaped row whose landmarks produce exactly the requested yaw.

    Eyes 100 px apart with their midpoint at x=200, so a nose at
    ``200 + yaw * 100`` yields ``yaw`` from ``DetectedFace.yaw_ratio``.
    Building a real row rather than stubbing the property means the production
    yaw arithmetic runs even in the route tests.
    """
    row = np.zeros(15, dtype=np.float32)
    row[:4] = (100, 100, 200, 200)  # x, y, w, h
    row[4:6] = (150.0, 150.0)  # right eye
    row[6:8] = (250.0, 150.0)  # left eye
    row[8:10] = (200.0 + yaw * 100.0, 200.0)  # nose tip
    row[10:12] = (170.0, 250.0)  # right mouth corner
    row[12:14] = (230.0, 250.0)  # left mouth corner
    row[14] = 0.99  # detection score
    return DetectedFace(
        box=(100, 100, 200, 200),
        landmarks=row[4:14].reshape(5, 2),
        score=0.99,
        raw=row,
    )


def identity_vector(identity: str) -> np.ndarray:
    """Deterministic unit vector per identity, so matching is reproducible."""
    seed = int.from_bytes(identity.encode()[:8].ljust(8, b"\0"), "little") % (2**32)
    rng = np.random.default_rng(seed)
    vector = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    return vector / np.linalg.norm(vector)


class FakeFaceEngine:
    """Stand-in for FaceEngine, driven by the bytes of each uploaded frame."""

    def __init__(self, match_threshold: float = 0.363) -> None:
        self.match_threshold = match_threshold
        self.calls: list[bytes] = []

    def embed_bytes(self, data: bytes) -> tuple[np.ndarray, DetectedFace]:
        from fzip_server.errors import MultipleFacesError, NoFaceDetectedError

        self.calls.append(data)
        text = data.decode(errors="replace")
        if "NOFACE" in text:
            raise NoFaceDetectedError
        if "CROWD" in text:
            raise MultipleFacesError

        identity = "alice"
        yaw = 0.0
        for part in text.split(";"):
            key, _, value = part.partition(":")
            if key == "IDENTITY":
                identity = value
            elif key == "YAW":
                yaw = float(value)
        return identity_vector(identity), make_detected_face(yaw)

    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        return 0.0 if denom < 1e-9 else float(np.dot(a, b) / denom)

    def best_match(self, probe: np.ndarray, enrolled: list[np.ndarray]) -> tuple[bool, float]:
        if not enrolled:
            return False, 0.0
        best = max(self.similarity(probe, c) for c in enrolled)
        return best >= self.match_threshold, best


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def settings() -> Settings:
    """Real settings, pointed at a database name unique to this test."""
    return get_settings().model_copy(update={"mongo_db": f"fzip_test_{uuid.uuid4().hex[:12]}"})


@pytest.fixture
async def database(settings: Settings) -> AsyncIterator[Database]:
    db = Database(settings)
    try:
        await db._client.admin.command("ping")
    except PyMongoError as exc:  # pragma: no cover - environment problem
        await db.close()
        pytest.fail(
            f"MongoDB is not reachable at {settings.mongo_uri}: {exc}\n"
            "Run the suite inside Compose:  docker compose run --rm api pytest"
        )

    await db.ensure_indexes()
    try:
        yield db
    finally:
        await db._client.drop_database(settings.mongo_db)
        await db.close()


@pytest.fixture
def face_engine() -> FakeFaceEngine:
    return FakeFaceEngine()


@pytest.fixture
async def client(
    settings: Settings, database: Database, face_engine: FakeFaceEngine
) -> AsyncIterator[AsyncClient]:
    """HTTP client with infrastructure dependencies overridden.

    ASGITransport does not run the lifespan, so ``app.state`` is never
    populated - which is intended, because every dependency that would read it
    is overridden here. That also means the real ONNX models are never loaded.
    """
    app = create_app()
    hasher = build_hasher(settings)

    app.dependency_overrides[get_db] = lambda: database.db
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_face_engine] = lambda: face_engine
    app.dependency_overrides[get_hasher] = lambda: hasher
    app.dependency_overrides[get_app_settings] = lambda: settings

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver") as http:
        yield http


@pytest.fixture
def credentials() -> dict[str, str]:
    return {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "password": "a-sufficiently-long-password",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def enrolment_files(identity: str = "alice") -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("frames", (f"f{i}.jpg", frame(identity, 0.0), "image/jpeg")) for i in range(3)]


def verification_files(
    identity: str = "alice", direction: str = "left", count: int = 5
) -> list[tuple[str, tuple[str, bytes, str]]]:
    """Frames that satisfy a head-turn challenge: neutral, then turned."""
    turn = 0.30 if direction == "left" else -0.30
    yaws = [0.0, 0.0, turn * 0.5, turn, turn]
    yaws = (yaws * ((count // 5) + 1))[:count]
    return [
        ("frames", (f"v{i}.jpg", frame(identity, yaw), "image/jpeg")) for i, yaw in enumerate(yaws)
    ]


async def register_user(
    http: AsyncClient, credentials: dict[str, str], identity: str = "alice"
) -> dict[str, Any]:
    response = await http.post(
        "/api/v1/auth/register", data=credentials, files=enrolment_files(identity)
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def auth_header(tokens: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def get_challenge(http: AsyncClient, tokens: dict[str, Any]) -> dict[str, Any]:
    response = await http.post("/api/v1/face/challenge", headers=auth_header(tokens))
    assert response.status_code == 200, response.text
    return dict(response.json())


def problem_slug(response: Any) -> str:
    """Last path segment of an RFC 9457 `type` URI."""
    return str(response.json()["type"]).rsplit("/", 1)[-1]
