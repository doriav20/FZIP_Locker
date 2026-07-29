"""Pure-function tests for the face pipeline's arithmetic.

These need no ONNX models and no database: they cover the yaw geometry and the
liveness decision, which is where the logic that could silently accept a spoof
actually lives.
"""

from __future__ import annotations

import numpy as np
import pytest

from fzip_server.biometrics import (
    YAW_TURN_RATIO,
    FaceEngine,
    TurnDirection,
    check_head_turn,
    decode_image,
)
from fzip_server.errors import NoFaceDetectedError

from .conftest import make_detected_face


# --------------------------------------------------------------------------
# Yaw geometry
# --------------------------------------------------------------------------
@pytest.mark.parametrize("yaw", [-0.5, -0.25, 0.0, 0.25, 0.5])
def test_yaw_ratio_recovers_the_constructed_value(yaw):
    assert make_detected_face(yaw).yaw_ratio == pytest.approx(yaw, abs=1e-4)


def test_yaw_ratio_is_scale_invariant():
    """Sitting closer to the camera must not read as a head turn."""
    near = make_detected_face(0.3)
    far = near.raw.copy()
    far[4:14] *= 0.5  # halve every landmark coordinate

    from fzip_server.biometrics import DetectedFace

    scaled = DetectedFace(
        box=(0, 0, 100, 100), landmarks=far[4:14].reshape(5, 2), score=0.9, raw=far
    )
    assert scaled.yaw_ratio == pytest.approx(near.yaw_ratio, abs=1e-4)


def test_degenerate_landmarks_do_not_divide_by_zero():
    from fzip_server.biometrics import DetectedFace

    row = np.zeros(15, dtype=np.float32)
    face = DetectedFace(box=(0, 0, 10, 10), landmarks=row[4:14].reshape(5, 2), score=0.5, raw=row)
    assert face.yaw_ratio == 0.0


# --------------------------------------------------------------------------
# Liveness decision
# --------------------------------------------------------------------------
def test_neutral_then_left_turn_passes():
    faces = [make_detected_face(y) for y in (0.0, 0.02, 0.15, 0.30, 0.30)]
    passed, info = check_head_turn(faces, TurnDirection.LEFT)
    assert passed, info


def test_neutral_then_right_turn_passes():
    faces = [make_detected_face(y) for y in (0.0, -0.02, -0.15, -0.30, -0.30)]
    passed, _ = check_head_turn(faces, TurnDirection.RIGHT)
    assert passed


def test_identical_frames_fail():
    """A repeated still frame is the exact 2022 replay payload."""
    faces = [make_detected_face(0.0) for _ in range(5)]
    passed, info = check_head_turn(faces, TurnDirection.LEFT)
    assert not passed
    assert info["reason"] == "insufficient-turn"


def test_turn_in_the_wrong_direction_fails():
    faces = [make_detected_face(y) for y in (0.0, 0.0, -0.3, -0.3, -0.3)]
    passed, _ = check_head_turn(faces, TurnDirection.LEFT)
    assert not passed


def test_a_single_frame_cannot_pass():
    passed, info = check_head_turn([make_detected_face(0.4)], TurnDirection.LEFT)
    assert not passed
    assert info["reason"] == "too-few-frames"


def test_no_neutral_baseline_fails():
    """Every frame already turned: we cannot tell a turn from a fixed pose."""
    faces = [make_detected_face(y) for y in (0.4, 0.42, 0.45, 0.43, 0.44)]
    passed, info = check_head_turn(faces, TurnDirection.LEFT)
    assert not passed
    assert info["reason"] == "no-neutral-frame"


def test_turn_is_measured_relative_to_the_users_own_baseline():
    """An off-centre nose must not bias the result.

    Someone whose neutral pose reads 0.08 should need the same *change* as
    someone centred at 0.0, not a smaller one.
    """
    faces = [make_detected_face(y) for y in (0.08, 0.08, 0.08 + YAW_TURN_RATIO + 0.02)]
    passed, _ = check_head_turn(faces, TurnDirection.LEFT)
    assert passed

    insufficient = [make_detected_face(y) for y in (0.08, 0.08, 0.08 + 0.05)]
    passed, _ = check_head_turn(insufficient, TurnDirection.LEFT)
    assert not passed


def test_just_below_the_threshold_fails():
    faces = [make_detected_face(y) for y in (0.0, 0.0, YAW_TURN_RATIO - 0.01)]
    passed, _ = check_head_turn(faces, TurnDirection.LEFT)
    assert not passed


def test_exactly_at_the_threshold_passes():
    faces = [make_detected_face(y) for y in (0.0, 0.0, YAW_TURN_RATIO)]
    passed, _ = check_head_turn(faces, TurnDirection.LEFT)
    assert passed


# --------------------------------------------------------------------------
# Similarity
# --------------------------------------------------------------------------
def test_identical_embeddings_are_perfectly_similar():
    vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert FaceEngine.similarity(vector, vector) == pytest.approx(1.0)


def test_orthogonal_embeddings_score_zero():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    assert FaceEngine.similarity(a, b) == pytest.approx(0.0)


def test_zero_vector_similarity_is_defined():
    a = np.zeros(4, dtype=np.float32)
    b = np.ones(4, dtype=np.float32)
    assert FaceEngine.similarity(a, b) == 0.0


# --------------------------------------------------------------------------
# Image decoding bounds
# --------------------------------------------------------------------------
def test_empty_upload_is_rejected():
    with pytest.raises(NoFaceDetectedError):
        decode_image(b"")


def test_non_image_upload_is_rejected():
    with pytest.raises(NoFaceDetectedError):
        decode_image(b"this is definitely not a JPEG")


def test_oversized_upload_is_rejected_before_decoding():
    """Bounded first, so a decompression bomb never reaches the decoder."""
    with pytest.raises(NoFaceDetectedError, match="too large"):
        decode_image(b"\xff\xd8\xff" + b"\x00" * (9 * 1024 * 1024))
