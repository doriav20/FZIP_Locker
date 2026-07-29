"""Entry point: ``uv run fzip-client`` or ``python -m fzip_client``."""

from __future__ import annotations

import sys


def main() -> int:
    # Imported lazily so `--help`-style failures and missing-Qt diagnostics do
    # not surface as an import traceback before anything is set up.
    from .ui.app import main as run_app

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
