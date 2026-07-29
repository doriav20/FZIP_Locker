#!/usr/bin/env python3
"""Download the YuNet and SFace ONNX models, verifying pinned digests.

Run at image build time so the runtime container never needs network access:

    python scripts/fetch_models.py --dest /app/models

The SHA-256 digests below are the integrity control, not the URL. Upstream
serves these from a moving branch, so if the published bytes ever change the
download fails loudly and a human has to review the new model before updating
the digest here. Failing closed on an unexpected model matters: this file
decides who can unlock an account.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"


@dataclass(frozen=True)
class Model:
    filename: str
    url: str
    sha256: str
    size: int
    purpose: str


MODELS = (
    Model(
        filename="face_detection_yunet_2023mar.onnx",
        url=f"{_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        size=232_589,
        purpose="face detection + 5 landmarks",
    ),
    Model(
        filename="face_recognition_sface_2021dec.onnx",
        url=f"{_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        size=38_696_353,
        purpose="128-d face embeddings",
    ),
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            hasher.update(block)
    return hasher.hexdigest()


def fetch(model: Model, dest_dir: Path) -> None:
    target = dest_dir / model.filename

    if target.exists():
        actual = digest(target)
        if actual == model.sha256:
            print(f"  ok       {model.filename} (cached)")
            return
        print(f"  stale    {model.filename}: digest mismatch, re-downloading")
        target.unlink()

    print(f"  fetching {model.filename} ({model.size / 1e6:.1f} MB) - {model.purpose}")
    tmp = target.with_suffix(".partial")
    try:
        with urllib.request.urlopen(model.url, timeout=120) as response:  # noqa: S310
            tmp.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"error: could not download {model.filename}: {exc}") from exc

    actual = digest(tmp)
    if actual != model.sha256:
        tmp.unlink(missing_ok=True)
        raise SystemExit(
            f"error: digest mismatch for {model.filename}\n"
            f"  expected {model.sha256}\n"
            f"  actual   {actual}\n"
            "Refusing to install an unverified face-recognition model."
        )

    # Only becomes the real filename once verified, so an interrupted run
    # cannot leave a partial model that later looks cached.
    tmp.rename(target)
    print(f"  ok       {model.filename}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("models"))
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    print(f"Fetching face models into {args.dest.resolve()}")
    for model in MODELS:
        fetch(model, args.dest)
    print("All models verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
