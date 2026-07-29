"""Test package.

Present so the test modules can share helpers via `from .conftest import ...`.
Without it, pytest imports each test file as a top-level module and the
relative imports fail.
"""
