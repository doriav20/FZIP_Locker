"""Face detection, embedding and matching.

Replaces the 2022 pipeline (Haar cascade detection + LBPH recognition) with
YuNet and SFace, both from mainline OpenCV's ``objdetect`` module. The old
approach had three problems this addresses:

* LBPH compares local binary pattern histograms, which are highly sensitive to
  lighting and pose. Its "confidence" is a distance with no calibrated scale,
  which is why the old threshold was the invented ``100 - confidence >= 62``.
  SFace produces a 128-dimensional embedding with a published cosine
  threshold of 0.363.
* The old server stored a trained LBPH *model* per user. Anyone with database
  access could load it and, with a little work, reconstruct approximate face
  data. Embeddings are one-way and stored encrypted (see :mod:`.crypto`).
* Verification accepted a single image, forever. Here a verification submits a
  short sequence of frames and must exhibit a server-requested head movement.

**On anti-spoofing:** the head-turn check defeats a static captured payload
being replayed, which is what the old protocol allowed. It does *not* defeat a
determined presentation attack -- a video replay on a phone screen, or a
printed photo moved by hand, can still pass. Real presentation-attack
detection needs depth, infrared or a trained PAD model. See docs/SECURITY.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .errors import MultipleFacesError, NoFaceDetectedError

#: YuNet emits one row per face:
#: [x, y, w, h, reye_x, reye_y, leye_x, leye_y, nose_x, nose_y,
#:  rmouth_x, rmouth_y, lmouth_x, lmouth_y, score]
_RIGHT_EYE = slice(4, 6)
_LEFT_EYE = slice(6, 8)
_NOSE = slice(8, 10)

#: Reject oversized uploads before decoding. A 50 MB "image" that expands to
#: gigabytes of raw pixels is a cheap denial of service otherwise.
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 4096 * 4096

#: A face smaller than this is too low-resolution to embed reliably.
MIN_FACE_PIXELS = 80

#: How far the nose must shift, as a fraction of inter-eye distance, before a
#: frame counts as "turned". Measured relative to each user's own neutral
#: frame, so an off-centre nose does not bias the result.
YAW_TURN_RATIO = 0.18
YAW_NEUTRAL_RATIO = 0.10


class TurnDirection(StrEnum):
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class DetectedFace:
    box: tuple[int, int, int, int]
    landmarks: np.ndarray
    score: float
    raw: np.ndarray

    @property
    def yaw_ratio(self) -> float:
        """Horizontal nose offset from the eye midpoint, scaled by eye spacing.

        Negative when the subject turns to their own right (their nose moves
        toward the left of a non-mirrored image), positive when they turn
        left. Scaling by inter-eye distance makes it independent of how far
        the user is sitting from the camera.
        """
        right_eye = self.raw[_RIGHT_EYE].astype(np.float64)
        left_eye = self.raw[_LEFT_EYE].astype(np.float64)
        nose = self.raw[_NOSE].astype(np.float64)

        eye_mid_x = (right_eye[0] + left_eye[0]) / 2.0
        eye_distance = float(np.linalg.norm(left_eye - right_eye))
        if eye_distance < 1e-6:
            return 0.0
        return float((nose[0] - eye_mid_x) / eye_distance)


def decode_image(data: bytes) -> np.ndarray:
    """Decode an uploaded image, with bounds checks before and after."""
    if not data:
        raise NoFaceDetectedError("The uploaded image was empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise NoFaceDetectedError("The uploaded image is too large.")

    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise NoFaceDetectedError("The upload was not a readable image.")
    if image.shape[0] * image.shape[1] > MAX_IMAGE_PIXELS:
        raise NoFaceDetectedError("The uploaded image has too many pixels.")
    return image


class FaceEngine:
    """Wraps the two ONNX models. Construct once and reuse - loading is slow."""

    def __init__(
        self,
        model_dir: Path,
        match_threshold: float = 0.363,
        detect_score_threshold: float = 0.85,
    ) -> None:
        detector_path = model_dir / "face_detection_yunet_2023mar.onnx"
        recognizer_path = model_dir / "face_recognition_sface_2021dec.onnx"

        for path in (detector_path, recognizer_path):
            if not path.exists():
                raise FileNotFoundError(
                    f"Missing model {path}. Run scripts/fetch_models.py."
                )

        self._detector = cv2.FaceDetectorYN.create(
            model=str(detector_path),
            config="",
            input_size=(320, 320),
            score_threshold=detect_score_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(
            model=str(recognizer_path), config=""
        )
        self.match_threshold = match_threshold

    # -- detection ---------------------------------------------------------
    def detect_all(self, image: np.ndarray) -> list[DetectedFace]:
        height, width = image.shape[:2]
        self._detector.setInputSize((width, height))
        _, raw = self._detector.detect(image)
        if raw is None:
            return []

        faces: list[DetectedFace] = []
        for row in raw:
            x, y, w, h = (int(v) for v in row[:4])
            faces.append(
                DetectedFace(
                    box=(x, y, w, h),
                    landmarks=row[4:14].reshape(5, 2),
                    score=float(row[14]),
                    raw=row,
                )
            )
        return faces

    def detect_single(self, image: np.ndarray) -> DetectedFace:
        """Detect exactly one face, or raise.

        Rejecting multi-face frames matters for enrolment: silently picking
        the largest face would let someone enrol a bystander by accident, or
        deliberately.
        """
        faces = self.detect_all(image)
        if not faces:
            raise NoFaceDetectedError
        if len(faces) > 1:
            raise MultipleFacesError

        face = faces[0]
        if min(face.box[2], face.box[3]) < MIN_FACE_PIXELS:
            raise NoFaceDetectedError(
                "Your face is too small in frame. Move closer to the camera."
            )
        return face

    # -- embedding ---------------------------------------------------------
    def embed(self, image: np.ndarray, face: DetectedFace) -> np.ndarray:
        """Align the crop and produce a 128-d embedding, L2-normalised."""
        aligned = self._recognizer.alignCrop(image, face.raw)
        feature: np.ndarray = self._recognizer.feature(aligned)
        vector = np.asarray(feature, dtype=np.float32).ravel()

        norm = float(np.linalg.norm(vector))
        if norm < 1e-9:
            raise NoFaceDetectedError("Could not extract facial features.")
        # Pre-normalising means matching is a plain dot product, and stored
        # embeddings are directly comparable regardless of image scale.
        return vector / norm

    def embed_bytes(self, data: bytes) -> tuple[np.ndarray, DetectedFace]:
        image = decode_image(data)
        face = self.detect_single(image)
        return self.embed(image, face), face

    # -- matching ----------------------------------------------------------
    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity. Inputs are already L2-normalised by `embed`."""
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom < 1e-9:
            return 0.0
        return float(np.dot(a, b) / denom)

    def best_match(
        self, probe: np.ndarray, enrolled: list[np.ndarray]
    ) -> tuple[bool, float]:
        """Compare against every enrolled template, returning the best score.

        Three templates are captured at enrolment, so a user whose appearance
        varies (glasses, lighting) has more than one chance to match.
        """
        if not enrolled:
            return False, 0.0
        best = max(self.similarity(probe, candidate) for candidate in enrolled)
        return best >= self.match_threshold, best


# --------------------------------------------------------------------------
# Liveness
# --------------------------------------------------------------------------
def check_head_turn(
    faces: list[DetectedFace], direction: TurnDirection
) -> tuple[bool, dict[str, Any]]:
    """Require a neutral frame and a turned frame in the requested direction.

    Measuring the turn as a *change* from the user's own neutral pose, rather
    than against an absolute threshold, keeps the check fair to people whose
    features are not perfectly symmetric.

    Returns ``(passed, diagnostics)``; the diagnostics are logged, never
    returned to the client, since telling an attacker exactly how far they
    need to turn would make the check easier to defeat.
    """
    if len(faces) < 2:
        return False, {"reason": "too-few-frames", "frames": len(faces)}

    ratios = [face.yaw_ratio for face in faces]

    neutral_candidates = [r for r in ratios if abs(r) < YAW_NEUTRAL_RATIO]
    if not neutral_candidates:
        return False, {"reason": "no-neutral-frame", "ratios": ratios}
    baseline = float(np.median(neutral_candidates))

    deltas = [r - baseline for r in ratios]
    if direction is TurnDirection.LEFT:
        achieved = max(deltas)
        passed = achieved >= YAW_TURN_RATIO
    else:
        achieved = min(deltas)
        passed = achieved <= -YAW_TURN_RATIO

    return passed, {
        "reason": "ok" if passed else "insufficient-turn",
        "baseline": baseline,
        "achieved": achieved,
        "ratios": ratios,
    }
