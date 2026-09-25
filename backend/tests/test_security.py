from datetime import timedelta

import jwt
import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct horse")
    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong horse", hashed)


def test_verify_against_malformed_hash_returns_false() -> None:
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_roundtrip() -> None:
    token = create_access_token(subject="42", role="seller")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "seller"


def test_expired_token_is_rejected() -> None:
    token = create_access_token(subject="42", role="customer", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_is_rejected() -> None:
    token = create_access_token(subject="42", role="customer")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token[:-2] + ("AA" if not token.endswith("AA") else "BB"))
