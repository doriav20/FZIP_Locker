"""Client configuration.

Resolved from environment variables with sensible local defaults, so the
common case (`docker compose up` on the same machine) needs no configuration
at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API_URL = "https://localhost:8443"

#: Caddy exports its locally-generated root CA here on first run. Trusting it
#: explicitly is what lets the client verify TLS properly instead of setting
#: `verify=False`, which would reduce the connection to the 2022 version's
#: plaintext-equivalent trust level.
DEFAULT_CA_BUNDLE = Path("certs/root.crt")


@dataclass(frozen=True, slots=True)
class ClientConfig:
    api_url: str
    ca_bundle: Path | None
    request_timeout: float = 30.0

    @classmethod
    def load(cls) -> ClientConfig:
        api_url = os.environ.get("FZIP_API_URL", DEFAULT_API_URL).rstrip("/")

        bundle_env = os.environ.get("FZIP_CA_BUNDLE")
        if bundle_env:
            bundle: Path | None = Path(bundle_env)
        else:
            # Search upward so the client works from either the repo root or
            # the client/ directory.
            bundle = None
            for base in (Path.cwd(), *Path.cwd().parents[:3]):
                candidate = base / DEFAULT_CA_BUNDLE
                if candidate.is_file():
                    bundle = candidate
                    break

        return cls(api_url=api_url, ca_bundle=bundle)

    @property
    def verify(self) -> str | bool:
        """What to hand httpx as its `verify` argument.

        Falls back to the system trust store when no local CA is found, rather
        than silently disabling verification.
        """
        if self.ca_bundle and self.ca_bundle.is_file():
            return str(self.ca_bundle)
        return True


def state_dir() -> Path:
    """Per-user directory for non-secret client state."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    path = base / "fzip-locker"
    path.mkdir(parents=True, exist_ok=True)
    return path
