# FZIP Locker — desktop client

PyQt6 client for [FZIP Locker](../README.md). Locks files into encrypted `.lck`
archives and unlocks them behind an account password, an archive password, and
a face check.

## Run

```bash
uv run fzip-client
```

`uv` provisions Python 3.13, PyQt6 and OpenCV on first launch (~200 MB, a few
minutes). Later starts are instant.

The backend must be up — see the [root README](../README.md):

```bash
docker compose up -d --build
```

## Configuration

Both are optional; the defaults work when the backend runs on the same machine.

| Variable | Default | Purpose |
|---|---|---|
| `FZIP_API_URL` | `https://localhost:8443` | Backend address |
| `FZIP_CA_BUNDLE` | `certs/root.crt`, searched upward | Caddy's local root CA |

Without a CA bundle the client falls back to the system trust store rather than
disabling verification, so a self-signed backend will be refused — deliberately.

## Tests

```bash
uv run --extra dev pytest -q
```

The crypto, archive, vault and operations suites import nothing from Qt, so
they also run without the GUI dependencies:

```bash
PYTHONPATH=src uv run --no-project --with cryptography --with argon2-cffi --with pytest pytest tests -q
```

## Layout

```
src/fzip_client/
  crypto.py      Argon2id + chunked AES-256-GCM primitives
  vault.py       .lck v2 container read/write
  archive.py     ZIP packing, with zip-slip validation on extract
  operations.py  lock() and unlock() - what the UI calls
  api.py         REST client over TLS
  session.py     Session state; refresh token in the OS keyring
  camera.py      Webcam capture on a QThread
  passwords.py   Generation, entropy estimation, validation
  ui/            Qt widgets, theme, screens
```

Files are encrypted **here**, never server-side. The archive password never
leaves this process, and cannot be recovered if lost — see
[docs/SECURITY.md](../docs/SECURITY.md).
