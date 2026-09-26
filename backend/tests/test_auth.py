from httpx import AsyncClient

from tests.conftest import PASSWORD

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


def _user(**overrides: str) -> dict[str, str]:
    return {"name": "Asha", "email": "asha@example.com", "password": PASSWORD, **overrides}


async def test_register_returns_user_without_password(client: AsyncClient) -> None:
    resp = await client.post(REGISTER, json=_user(preferred_language="mr"))
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "asha@example.com"
    assert body["role"] == "customer"
    assert body["preferred_language"] == "mr"
    assert "password" not in body and "hashed_password" not in body


async def test_register_duplicate_email_is_conflict(client: AsyncClient) -> None:
    assert (await client.post(REGISTER, json=_user())).status_code == 201
    resp = await client.post(REGISTER, json=_user(email="ASHA@example.com"))  # case-insensitive
    assert resp.status_code == 409


async def test_cannot_self_register_as_admin(client: AsyncClient) -> None:
    resp = await client.post(REGISTER, json=_user(role="admin"))
    assert resp.status_code == 422
    assert "Admin accounts cannot be self-registered" in resp.text


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    resp = await client.post(REGISTER, json=_user(password="short"))
    assert resp.status_code == 422


async def test_login_and_me(client: AsyncClient) -> None:
    await client.post(REGISTER, json=_user(role="seller"))
    resp = await client.post(LOGIN, data={"username": "Asha@Example.com", "password": PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert resp.json()["token_type"] == "bearer"

    me = await client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "asha@example.com"
    assert me.json()["role"] == "seller"


async def test_login_wrong_password_is_unauthorized(client: AsyncClient) -> None:
    await client.post(REGISTER, json=_user())
    resp = await client.post(LOGIN, data={"username": "asha@example.com", "password": "wrong-password"})
    assert resp.status_code == 401


async def test_login_unknown_email_is_unauthorized(client: AsyncClient) -> None:
    resp = await client.post(LOGIN, data={"username": "nobody@example.com", "password": PASSWORD})
    assert resp.status_code == 401


async def test_me_requires_valid_token(client: AsyncClient) -> None:
    assert (await client.get(ME)).status_code == 401
    bad = await client.get(ME, headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


async def test_update_preferred_language(client: AsyncClient) -> None:
    await client.post(REGISTER, json=_user())
    token = (await client.post(LOGIN, data={"username": "asha@example.com", "password": PASSWORD})).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.patch(ME, json={"preferred_language": "hi"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["preferred_language"] == "hi"
    assert (await client.patch(ME, json={"preferred_language": "fr"}, headers=headers)).status_code == 422
