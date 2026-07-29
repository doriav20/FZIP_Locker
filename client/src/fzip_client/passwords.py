"""Password generation, strength estimation and input validation.

Carried over from the original ``details_generator.py``, with three fixes:

* ``random.choices`` replaced by :mod:`secrets`. The old generator used the
  Mersenne Twister, which is fully predictable from a few hundred outputs --
  an unfortunate property for something generating archive passwords.
* Every selected character class is now guaranteed to appear. The old version
  sampled uniformly, so "include symbols" could still produce a password with
  no symbols in it.
* Strength is reported as entropy in bits rather than left to the user to
  guess.

The visually ambiguous characters ``0 O o 1 I l i`` stay excluded, as in the
original -- these passwords get read off screens and retyped.
"""

from __future__ import annotations

import math
import re
import secrets
from dataclasses import dataclass

LOWERCASE = "abcdefghjkmnpqrstuvwxyz"
UPPERCASE = "ABCDEFGHJKLMNPQRSTUVWXYZ"
NUMBERS = "23456789"
SYMBOLS = "!@#$*+-._"

MIN_LENGTH = 12
MAX_LENGTH = 128

#: The 2022 client capped archive passwords at 32 characters and allowed 6.
#: Six characters is trivially brute-forced; the floor is now 12. Argon2id
#: makes each guess expensive, but it cannot rescue a genuinely tiny keyspace.
DEFAULT_LENGTH = 20


def generate_password(
    length: int = DEFAULT_LENGTH,
    *,
    include_uppercase: bool = True,
    include_numbers: bool = True,
    include_symbols: bool = True,
) -> str:
    """Generate a password with at least one character from each enabled class."""
    if length < MIN_LENGTH:
        raise ValueError(f"length must be at least {MIN_LENGTH}")
    if length > MAX_LENGTH:
        raise ValueError(f"length must be at most {MAX_LENGTH}")

    classes = [LOWERCASE]
    if include_uppercase:
        classes.append(UPPERCASE)
    if include_numbers:
        classes.append(NUMBERS)
    if include_symbols:
        classes.append(SYMBOLS)

    alphabet = "".join(classes)

    # One guaranteed character per class, then fill, then shuffle so the
    # guaranteed characters are not always at the front.
    chars = [secrets.choice(group) for group in classes]
    chars += [secrets.choice(alphabet) for _ in range(length - len(classes))]

    # secrets has no shuffle; Fisher-Yates driven by randbelow is the
    # cryptographically sound equivalent of random.shuffle.
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]

    return "".join(chars)


@dataclass(frozen=True, slots=True)
class Strength:
    bits: float
    label: str

    @property
    def fraction(self) -> float:
        """0.0-1.0, saturating at 128 bits, for driving a progress bar."""
        return min(self.bits / 128.0, 1.0)


def estimate_strength(password: str) -> Strength:
    """Rough entropy estimate from the character classes actually used.

    This measures the keyspace a brute-force attacker faces, which is the
    right model for a randomly generated password. It deliberately does not
    try to detect dictionary words or keyboard walks, so a human-chosen
    password like "Password123!" will score far higher here than it deserves.
    The UI says as much next to the meter.
    """
    if not password:
        return Strength(0.0, "empty")

    pool = 0
    if any(c.islower() for c in password):
        pool += 26
    if any(c.isupper() for c in password):
        pool += 26
    if any(c.isdigit() for c in password):
        pool += 10
    if any(not c.isalnum() for c in password):
        pool += len(SYMBOLS)

    bits = len(password) * math.log2(pool) if pool else 0.0

    if bits < 45:
        label = "weak"
    elif bits < 70:
        label = "fair"
    elif bits < 100:
        label = "strong"
    else:
        label = "excellent"
    return Strength(bits, label)


def is_valid_password(password: str) -> bool:
    """Length check only.

    Character-set restrictions were removed. The old version rejected any
    password containing a character outside its own hardcoded list, which
    silently blocked spaces, accented letters and anything a password manager
    might produce -- punishing users for having better passwords.
    """
    return MIN_LENGTH <= len(password) <= MAX_LENGTH


#: Deliberately permissive. Exhaustive RFC 5322 validation by regex is a known
#: dead end; the registration flow proves the address by mailing it instead.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


def is_valid_email(address: str) -> bool:
    return len(address) <= 254 and _EMAIL_RE.match(address) is not None
