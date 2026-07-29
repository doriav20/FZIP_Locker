# FZIP Locker

Lock files into an encrypted `.lck` archive, gated by three factors: your
account password, an archive password, and your face.

Originally a 2022 high-school cyber final project. Rebuilt in 2026 — the
product concept and screen flow are the same; the security model was replaced
outright, for reasons documented in [docs/SECURITY.md](docs/SECURITY.md).

**The server never receives your files or your archive password.** Archives are
sealed on your machine with AES-256-GCM under a key derived from your password
via Argon2id. A fully compromised server has nothing to decrypt.

---

## Requirements

| To run | You need |
|---|---|
| Backend (API, database, TLS, mail) | Docker Desktop — nothing else |
| Desktop client | [`uv`](https://docs.astral.sh/uv/) — a single binary that provisions its own Python, Qt and OpenCV |

No system Python, MongoDB, or Qt installation is required. If you don't have
`uv`:

```bash
winget install --id=astral-sh.uv -e
```

The desktop client is deliberately **not** a Compose service: it needs your
webcam and a display, neither of which a Linux container on Windows can reach.

---

## 1. Start the backend

Create `.env` with freshly generated secrets:

```bash
uv run --no-project --with cryptography python scripts/init_env.py
```

> **The `.env` must live in the repository root**, next to `compose.yaml`.
> Compose reads it from there and nowhere else — a `.env` inside `server/` is
> silently ignored for `${VAR}` substitution. `init_env.py` always writes to
> the right place, and reuses any secrets it finds in `server/.env` or an
> existing root `.env`, so it is safe to re-run.

Then bring the stack up:

```bash
docker compose up -d --build
```

First build takes a few minutes — it downloads and checksum-verifies the two
ONNX face models. Check everything is healthy:

```bash
docker compose ps
```

| Service | Purpose | Reachable at |
|---|---|---|
| `caddy` | TLS termination, local CA | `https://localhost:8443` |
| `api` | FastAPI backend | via Caddy only |
| `mongo` | Database | private network only |
| `mailpit` | Catches outbound mail | `http://localhost:8025` |

Only Caddy and Mailpit's web UI are published to the host. Mongo has no `ports:`
entry at all, and the API is reachable only through Caddy, so TLS can't be
bypassed.

Verify the API is up:

```bash
curl --cacert certs/root.crt https://localhost:8443/healthz
```

`certs/root.crt` is Caddy's locally-generated root CA, exported on first start.
The client trusts it explicitly rather than disabling verification.

## 2. Run the desktop client

```bash
cd client && uv run fzip-client
```

`uv` resolves Python 3.13 and every dependency on first run, then launches the
GUI. Subsequent starts are instant.

To point at a non-default backend:

```bash
FZIP_API_URL=https://localhost:8443 FZIP_CA_BUNDLE=../certs/root.crt uv run fzip-client
```

---

## Using it

**Register** — email, account password, and three face captures. A welcome mail
lands in Mailpit at `http://localhost:8025`.

**Lock files** — pick files or a folder, choose where to save the `.lck`, then
set an archive password (or generate one). No face scan needed, so you can
always lock files even with the backend down.

**Unlock** — pick the `.lck`, pass a face challenge (the server asks you to turn
your head in a randomly chosen direction), then enter the archive password.

> The archive password cannot be recovered. That's the point of the design —
> the server never sees it. Write it down.

---

## Tests

Backend, inside Compose (needs the real Mongo):

```bash
docker compose run --rm api pytest -q
```

Client crypto core — no GUI dependencies needed:

```bash
cd client && uv run --extra dev pytest -q
```

Lint and type-check everything:

```bash
uv tool run ruff check . && uv tool run ruff format --check .
```

---

## What changed since 2022

| Area | 2022 | 2026 |
|---|---|---|
| Transport | Custom 3-byte handshake over plaintext TCP, payload via `pickle` | REST/JSON over TLS 1.3; Pydantic validation; **no pickle anywhere** |
| Archive crypto | AES-**OFB** (no integrity) over ZipCrypto, one static key committed to the repo | Chunked AES-256-**GCM**, key derived per-file from your password |
| Passwords | Encrypted reversibly; key was `pickle.dumps(creation_time)[7:39]`, and `creation_time` sat in plaintext in the same document | Argon2id hashes, transparently upgraded as cost parameters rise |
| Face auth | Haar cascade + LBPH, `100 - confidence >= 62`, replayable forever | YuNet + SFace embeddings, calibrated 0.363 cosine threshold, single-use nonce + head-turn challenge |
| Biometrics at rest | Trained LBPH model stored as a plain blob | AES-256-GCM envelope encryption, bound to the owning user |
| Sessions | A module-global `USER_EMAIL` | Ed25519 JWTs + rotating refresh tokens with reuse detection; refresh token in the OS keyring |
| Errors | ~40 bare `except:`, all collapsing to "Unknown Error" | Typed exceptions → RFC 9457 problem documents; structured logs with request IDs |
| Database | MongoDB Atlas as `admin`, URI hardcoded in source | Containerised Mongo, least-privilege app user, unique + TTL indexes created at startup |
| Client | 1,535-line `GUI.py` with absolute pixel geometry, plus 68,513 lines of compiled Qt resource blobs | PyQt6, layout-driven and resizable, one stylesheet, assets as plain files, all work off the UI thread |
| Portability | `ctypes.windll` DPI, `\\` hardcoded as path separator | `pathlib` and native HiDPI throughout |
| Secrets | Gmail password and DB URI in source; no `.gitignore` had ever existed | All config via `.env`; `.gitignore` + `.dockerignore` + a `gitleaks` pre-commit hook |

`pyminizip` and `opencv-contrib-python` are gone entirely — the first because
the outer AEAD makes inner zip encryption redundant, the second because YuNet
and SFace ship in mainline OpenCV.

---

## Documentation

- [docs/SECURITY.md](docs/SECURITY.md) — threat model, key management, and the
  limits of the face factor
- [docs/FORMAT.md](docs/FORMAT.md) — the `.lck` v2 container, byte by byte

## Layout

```
compose.yaml          Backend stack
server/               FastAPI app, Dockerfile, model fetcher
client/               PyQt6 desktop client
docker/               Caddyfile, Mongo init script
docs/                 Security notes and format spec
```

The 2022 implementation is preserved on the `main` branch and in git history.

## Licence

MIT
