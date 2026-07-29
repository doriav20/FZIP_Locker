#!/usr/bin/env python3
"""Create the root .env, generating any secrets that are missing.

    uv run --no-project --with cryptography python scripts/init_env.py

Docker Compose reads `.env` from the directory holding compose.yaml -- the
repository root -- and nowhere else. A `.env` inside `server/` is *not* picked
up for `${VAR}` substitution, which is a easy and confusing mistake to make.
This script always writes to the right place.

Existing values are preserved. It reuses secrets already present in the root
`.env` or in `server/.env`, so running it twice is safe and will not orphan
data encrypted under an earlier key.

Values are never printed -- only variable names.
"""

from __future__ import annotations

import base64
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)

ROOT = Path(__file__).resolve().parent.parent

#: Variables that must hold a generated secret, with their generators.
GENERATORS = {
    "MONGO_ROOT_PASSWORD": lambda: secrets.token_urlsafe(32),
    "MONGO_APP_PASSWORD": lambda: secrets.token_urlsafe(32),
    "FZIP_BIOMETRIC_KEY": lambda: base64.b64encode(secrets.token_bytes(32)).decode(),
    "FZIP_JWT_PRIVATE_KEY": lambda: base64.b64encode(
        Ed25519PrivateKey.generate().private_bytes(
            Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
        )
    ).decode(),
}


def read_text_any_encoding(path: Path) -> str:
    """Read a text file that may not be UTF-8.

    PowerShell 5.1's `>` and `Out-File` default to UTF-16LE, so a file created
    with `python gen_secrets.py > .env` on Windows arrives UTF-16 with a BOM.
    Docker Compose cannot read that either, which makes detecting it here
    doubly worthwhile - the rewritten file is always UTF-8.
    """
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise SystemExit(f"error: cannot decode {path}; rewrite it as UTF-8")


def parse(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line in read_text_any_encoding(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        value = value.strip()
        if value and "CHANGE_ME" not in value:
            values[key.strip()] = value
    return values


def main() -> int:
    example = ROOT / ".env.example"
    target = ROOT / ".env"

    if not example.is_file():
        print(f"error: {example} is missing", file=sys.stderr)
        return 1

    # Precedence: the root .env wins, then server/.env, then generate fresh.
    existing = parse(ROOT / "server" / ".env") | parse(target)

    reused: list[str] = []
    created: list[str] = []
    for key, generate in GENERATORS.items():
        if key in existing:
            reused.append(key)
        else:
            existing[key] = generate()
            created.append(key)

    out: list[str] = []
    for line in read_text_any_encoding(example).splitlines():
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.partition("=")[0].strip()
            if key in existing:
                out.append(f"{key}={existing[key]}")
                continue
        out.append(line)

    target.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"wrote {target.relative_to(ROOT)}")
    if reused:
        print("  reused existing:", ", ".join(sorted(reused)))
    if created:
        print("  generated new:  ", ", ".join(sorted(created)))

    leftover = [
        ln.partition("=")[0] for ln in out if "CHANGE_ME" in ln and not ln.strip().startswith("#")
    ]
    if leftover:
        print("  STILL PLACEHOLDER:", ", ".join(leftover))
        return 1

    print("\nNext:  docker compose up -d --build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
