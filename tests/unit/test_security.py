"""Unit tests for core security helpers."""

from __future__ import annotations

import pytest

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_verify_roundtrip() -> None:
    h = hash_password("hello-world-123")
    assert h != "hello-world-123"
    assert verify_password("hello-world-123", h) is True
    assert verify_password("wrong", h) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token("user-id-1")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-id-1"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_refresh_token_roundtrip() -> None:
    token, jti, _ = create_refresh_token("user-id-2")
    assert jti
    payload = decode_token(token, expected_type="refresh")
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_rejects_wrong_type() -> None:
    token = create_access_token("user-id-3")
    with pytest.raises(UnauthorizedError):
        decode_token(token, expected_type="refresh")


def test_decode_rejects_invalid_token() -> None:
    with pytest.raises(UnauthorizedError):
        decode_token("not.a.jwt", expected_type="access")
