"""Typed error hierarchy for the client.

The 2022 client funnelled every failure through a four-value enum
(``OperationResultType``), so a wrong password, a corrupt file, a dead network
and a genuine bug all surfaced to the user as "Unknown Error". Distinct
exception types let the UI say something true about what went wrong.
"""

from __future__ import annotations


class FzipError(Exception):
    """Base class for every error this client raises deliberately."""

    #: Message safe to show a user verbatim. Subclasses override.
    user_message = "Something went wrong."


# --------------------------------------------------------------------------
# Vault / crypto
# --------------------------------------------------------------------------
class VaultError(FzipError):
    """Base class for `.lck` container failures."""

    user_message = "This locked file could not be opened."


class NotAVaultError(VaultError):
    """The file does not begin with the FZIP magic bytes."""

    user_message = "This is not an FZIP Locker file."


class UnsupportedVersionError(VaultError):
    """The container version is newer than this client understands."""

    user_message = "This file was created by a newer version of FZIP Locker."


class MalformedVaultError(VaultError):
    """Structurally invalid: bad header length, truncated body, bad JSON."""

    user_message = "This locked file is damaged."


class DecryptionError(VaultError):
    """AEAD tag verification failed.

    This means one of two things and we deliberately cannot distinguish them:
    the password was wrong, or the file was modified. Both are authentication
    failures. Reporting them separately would leak information to an attacker
    probing a stolen file.
    """

    user_message = "Wrong password, or the file has been tampered with."


class OwnershipError(VaultError):
    """The vault's owner tag does not match the signed-in account.

    Advisory only - see docs/SECURITY.md. The archive password is the actual
    access control; this check exists so the UI can give a clearer message than
    a generic decryption failure.
    """

    user_message = "This file belongs to a different account."


# --------------------------------------------------------------------------
# Archive
# --------------------------------------------------------------------------
class ArchiveError(FzipError):
    user_message = "The archive could not be read or written."


class UnsafeArchiveEntryError(ArchiveError):
    """An entry tried to escape the extraction directory (zip-slip)."""

    user_message = "This archive contains unsafe file paths and was not extracted."


# --------------------------------------------------------------------------
# API / transport
# --------------------------------------------------------------------------
class ApiError(FzipError):
    """A structured RFC 9457 problem response from the server."""

    user_message = "The server rejected the request."

    def __init__(self, status: int, type_slug: str, detail: str) -> None:
        super().__init__(f"{status} {type_slug}: {detail}")
        self.status = status
        self.type_slug = type_slug
        self.detail = detail
        self.user_message = detail or self.user_message


class NetworkError(FzipError):
    user_message = "Could not reach the server. Is it running?"


class AuthRequiredError(FzipError):
    user_message = "Your session expired. Please sign in again."


# --------------------------------------------------------------------------
# Camera
# --------------------------------------------------------------------------
class CameraError(FzipError):
    user_message = "No camera detected, or it is in use by another program."
