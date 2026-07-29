"""RFC 9457 problem responses.

The 2022 server answered every request with a single digit from a four-value
enum, so the client could not tell a wrong password from a dead database and
showed "Unknown Error" for both. Here each failure has a stable ``type`` slug
the client can branch on, plus human-readable text it can display as-is.

Messages are written on the assumption that an attacker reads them too: the
authentication failures below are deliberately uniform about *why* they
failed, so they cannot be used to enumerate accounts.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROBLEM_CONTENT_TYPE = "application/problem+json"
_BASE_URI = "https://fziplocker.local/problems"


class ProblemError(Exception):
    """Base class for anything that should reach the client as a problem doc."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    slug: str = "internal-error"
    title: str = "Internal Server Error"
    default_detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, **extra: Any) -> None:
        self.detail = detail or self.default_detail
        self.extra = extra
        super().__init__(self.detail)

    def to_response(self) -> JSONResponse:
        body: dict[str, Any] = {
            "type": f"{_BASE_URI}/{self.slug}",
            "title": self.title,
            "status": self.status_code,
            "detail": self.detail,
        }
        body.update(self.extra)
        return JSONResponse(
            status_code=self.status_code,
            content=body,
            media_type=PROBLEM_CONTENT_TYPE,
        )


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
class InvalidCredentialsError(ProblemError):
    """Wrong email or wrong password - deliberately indistinguishable.

    Returning a different message for "no such account" would turn the login
    endpoint into an account-existence oracle.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "invalid-credentials"
    title = "Invalid Credentials"
    default_detail = "That email and password combination is not correct."


class AuthenticationRequiredError(ProblemError):
    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "authentication-required"
    title = "Authentication Required"
    default_detail = "Sign in to continue."


class TokenExpiredError(ProblemError):
    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "token-expired"
    title = "Token Expired"
    default_detail = "Your session expired. Sign in again."


class TokenReusedError(ProblemError):
    """A refresh token was presented twice.

    Refresh tokens rotate on every use, so a second presentation means the
    token was captured. The whole token family is revoked in response, which
    logs the legitimate user out too - the safe direction to fail.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "token-reused"
    title = "Token Reuse Detected"
    default_detail = "This session was revoked for security reasons. Sign in again."


class AccountLockedError(ProblemError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    slug = "account-locked"
    title = "Too Many Attempts"
    default_detail = "Too many failed attempts. Try again later."


class EmailAlreadyRegisteredError(ProblemError):
    status_code = status.HTTP_409_CONFLICT
    slug = "email-already-registered"
    title = "Email Already Registered"
    default_detail = "An account already exists for that email address."


# --------------------------------------------------------------------------
# Face verification
# --------------------------------------------------------------------------
class NoFaceDetectedError(ProblemError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    slug = "no-face-detected"
    title = "No Face Detected"
    default_detail = "No face was found in the image. Face the camera in good light."


class MultipleFacesError(ProblemError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    slug = "multiple-faces"
    title = "Multiple Faces Detected"
    default_detail = "More than one face is visible. Make sure you are alone in frame."


class FaceMismatchError(ProblemError):
    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "face-mismatch"
    title = "Face Not Recognised"
    default_detail = "That face does not match the enrolled account."


class ChallengeInvalidError(ProblemError):
    """Nonce unknown, expired, or already spent.

    The single-use nonce is what stops a captured verification payload from
    being replayed forever, which the 2022 protocol allowed.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    slug = "challenge-invalid"
    title = "Challenge Invalid"
    default_detail = "This face challenge has expired or was already used."


class LivenessFailedError(ProblemError):
    status_code = status.HTTP_401_UNAUTHORIZED
    slug = "liveness-failed"
    title = "Liveness Check Failed"
    default_detail = "The requested head movement was not detected. Try again."


class NoEnrolledFaceError(ProblemError):
    status_code = status.HTTP_409_CONFLICT
    slug = "no-enrolled-face"
    title = "No Enrolled Face"
    default_detail = "This account has no enrolled face."


# --------------------------------------------------------------------------
# Generic
# --------------------------------------------------------------------------
class ValidationProblem(ProblemError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    slug = "validation-error"
    title = "Validation Error"
    default_detail = "The request body was not valid."


class ServiceUnavailableError(ProblemError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    slug = "service-unavailable"
    title = "Service Unavailable"
    default_detail = "A dependency is unavailable. Try again shortly."


# --------------------------------------------------------------------------
# Wiring
# --------------------------------------------------------------------------
def install_exception_handlers(app: FastAPI) -> None:
    import structlog

    log = structlog.get_logger()

    @app.exception_handler(ProblemError)
    async def _problem_handler(_: Request, exc: ProblemError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Field-level errors are safe to expose: they describe the caller's own
        # request, not server state.
        return ValidationProblem(
            errors=[
                {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                for e in exc.errors()
            ]
        ).to_response()

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log the detail, return none of it. The 2022 code did the reverse of
        # both: it swallowed the exception entirely with a bare `except:` and
        # logged nothing, so failures were invisible on the server and opaque
        # on the client.
        log.exception(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=type(exc).__name__,
        )
        return ProblemError().to_response()
