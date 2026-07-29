"""Welcome email delivery.

Keeps the original's template and visual identity. Three things changed: the
Gmail credentials are no longer hardcoded in source, the username is HTML-
escaped before interpolation, and sending is asynchronous so a slow SMTP
server cannot stall the request that triggered it.
"""

from __future__ import annotations

import html
from email.message import EmailMessage

import aiosmtplib
import structlog

from .config import Settings

log = structlog.get_logger()

SUBJECT = "Welcome to FZIP Locker"

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>
    table {
        max-width: 400px; width: 100%; border: 0; border-spacing: 0;
        border-collapse: collapse; margin: 0 auto; text-align: center;
        color: rgb(0, 0, 0); background-color: rgb(245, 245, 220);
    }
    h1 {
        margin-top: 0; font-family: Bahnschrift SemiBold, Gadugi, sans-serif;
        font-size: xxx-large; background-color: rgba(95, 158, 160, 0.5);
    }
    em {
        margin-top: 10px; display: inline-block;
        font-family: Bahnschrift SemiBold, Gadugi, sans-serif;
        font-size: x-large; font-style: normal;
        background-color: rgba(0, 255, 255, 0.2);
    }
</style>
</head>
<body>
<table>
    <tr>
        <td>
            <h1>Hey {username}</h1>
            <em>
                We are glad you joined FZIP Locker
                <br>
                Now you can scan your face and start encrypting your files securely...
            </em>
        </td>
    </tr>
</table>
</body>
</html>
"""

_PLAIN = """\
Hey {username}

We are glad you joined FZIP Locker.
Now you can scan your face and start encrypting your files securely.
"""


def build_message(settings: Settings, recipient: str) -> EmailMessage:
    local_part = recipient.split("@", 1)[0]
    # The old version interpolated this straight into the HTML. An address
    # like `<img onerror=...>@x.com` would have been injected verbatim into
    # every mail client that rendered it.
    username = html.escape(local_part)

    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message.set_content(_PLAIN.format(username=local_part))
    message.add_alternative(_TEMPLATE.replace("{username}", username), subtype="html")
    return message


async def send_welcome_email(settings: Settings, recipient: str) -> bool:
    """Best-effort send. Returns success, never raises.

    Registration must not fail because the mail server is down -- the account
    already exists at this point. The failure is logged instead of silently
    swallowed, which is what the old bare `except: return False` did.
    """
    try:
        await aiosmtplib.send(
            build_message(settings, recipient),
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
            timeout=10,
        )
    except (aiosmtplib.SMTPException, OSError) as exc:
        log.warning(
            "welcome_email_failed", error=str(exc), recipient_domain=recipient.rsplit("@", 1)[-1]
        )
        return False

    log.info("welcome_email_sent", recipient_domain=recipient.rsplit("@", 1)[-1])
    return True
