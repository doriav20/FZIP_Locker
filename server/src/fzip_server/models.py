"""Request and response schemas.

Every inbound payload is parsed by Pydantic. This is the structural fix for
the 2022 server's worst flaw: it called ``pickle.loads()`` on bytes read
straight off a socket, which hands an unauthenticated attacker arbitrary code
execution. Pickle appears nowhere in this codebase.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .biometrics import TurnDirection

#: Matches the client's floor. Twelve characters with Argon2id behind it is a
#: meaningful barrier; the old six-character minimum was not.
Password = Annotated[str, Field(min_length=12, max_length=128)]


class _Strict(BaseModel):
    """Reject unknown fields rather than ignoring them.

    A typo'd field name should fail loudly instead of silently taking a
    default.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
class RegisterRequest(_Strict):
    email: EmailStr
    password: Password

    @field_validator("email")
    @classmethod
    def _normalise(cls, value: str) -> str:
        # Stored lowercase so the unique index is effectively case-insensitive
        # and "User@x.com" cannot register alongside "user@x.com".
        return value.lower()


class LoginRequest(RegisterRequest):
    pass


class RefreshRequest(_Strict):
    refresh_token: str = Field(min_length=16, max_length=512)


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    user_id: str


class UserResponse(BaseModel):
    user_id: str
    email: EmailStr
    created_at: datetime
    has_enrolled_face: bool


# --------------------------------------------------------------------------
# Face
# --------------------------------------------------------------------------
class ChallengeResponse(BaseModel):
    nonce: str
    direction: TurnDirection
    frames_required: int
    expires_in: int


class FaceVerifyResponse(BaseModel):
    face_token: str
    expires_in: int
    #: Rounded before it leaves the server. Returning full precision would let
    #: an attacker hill-climb toward the threshold by measuring how each
    #: submitted image moved the score.
    similarity: float


class EnrollResponse(BaseModel):
    enrolled_templates: int


class ProblemResponse(BaseModel):
    """Documents the RFC 9457 shape in the generated OpenAPI schema."""

    type: str
    title: str
    status: int
    detail: str
