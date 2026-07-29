from __future__ import annotations

import pytest

from fzip_client import passwords


def test_generated_passwords_have_the_requested_length():
    for length in (12, 20, 64, 128):
        assert len(passwords.generate_password(length)) == length


def test_every_enabled_class_appears():
    """The 2022 generator sampled uniformly, so 'include symbols' was a hint,
    not a guarantee. Over 200 draws, every class must appear every time."""
    for _ in range(200):
        pwd = passwords.generate_password(12)
        assert any(c in passwords.LOWERCASE for c in pwd)
        assert any(c in passwords.UPPERCASE for c in pwd)
        assert any(c in passwords.NUMBERS for c in pwd)
        assert any(c in passwords.SYMBOLS for c in pwd)


def test_disabled_classes_are_absent():
    for _ in range(50):
        pwd = passwords.generate_password(
            16, include_uppercase=False, include_numbers=False, include_symbols=False
        )
        assert set(pwd) <= set(passwords.LOWERCASE)


def test_ambiguous_characters_are_excluded():
    joined = passwords.generate_password(128) + passwords.generate_password(128)
    assert not (set(joined) & set("0Oo1Il"))


def test_generated_passwords_do_not_repeat():
    seen = {passwords.generate_password(20) for _ in range(500)}
    assert len(seen) == 500


def test_guaranteed_characters_are_not_always_leading():
    """Without the shuffle, position 0 would always be lowercase."""
    firsts = {passwords.generate_password(16)[0] for _ in range(200)}
    assert not firsts <= set(passwords.LOWERCASE)


@pytest.mark.parametrize("length", [0, 1, 11, 129, 1000])
def test_out_of_range_lengths_are_refused(length):
    with pytest.raises(ValueError, match="length must be"):
        passwords.generate_password(length)


def test_strength_increases_with_length():
    short = passwords.estimate_strength("aB3!" * 3)
    long = passwords.estimate_strength("aB3!" * 8)
    assert long.bits > short.bits
    assert 0.0 <= short.fraction <= 1.0


def test_strength_of_a_generated_default_is_strong():
    strength = passwords.estimate_strength(passwords.generate_password())
    assert strength.bits >= 100
    assert strength.label == "excellent"


def test_empty_password_has_no_strength():
    assert passwords.estimate_strength("").bits == 0.0


@pytest.mark.parametrize("pwd", ["a" * 12, "x" * 128, "with spaces here"])
def test_valid_passwords_accepted(pwd):
    assert passwords.is_valid_password(pwd)


@pytest.mark.parametrize("pwd", ["", "short", "a" * 11, "a" * 129])
def test_invalid_passwords_rejected(pwd):
    assert not passwords.is_valid_password(pwd)


def test_unicode_passwords_are_allowed():
    """The old validator rejected anything outside its hardcoded ASCII list,
    penalising password managers and non-English users."""
    assert passwords.is_valid_password("пароль-который-длинный")
    assert passwords.is_valid_password("passphrase-with-emoji-\U0001f512-here")


@pytest.mark.parametrize(
    "address",
    ["a@b.co", "first.last+tag@example.com", "user@sub.domain.example.org"],
)
def test_valid_emails_accepted(address):
    assert passwords.is_valid_email(address)


@pytest.mark.parametrize(
    "address",
    [
        "",
        "no-at-sign",
        "@example.com",
        "user@",
        "user@host",
        "a b@example.com",
        "user@@example.com",
        "x" * 250 + "@example.com",
    ],
)
def test_invalid_emails_rejected(address):
    assert not passwords.is_valid_email(address)
