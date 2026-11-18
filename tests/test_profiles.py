import time
import uuid
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import SUPABASE_URL, jwks_client
from app.database import engine
from app.main import app
from app.models import UserProfile

# 1. Generate a temporary ES256 keypair for testing
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()


def mint_test_jwt(user_id: uuid.UUID, email: str) -> str:
    """Creates a valid ES256 Supabase-shaped JWT signed by our test private key."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "iss": f"{SUPABASE_URL.rstrip('/')}/auth/v1",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, private_key, algorithm="ES256")


@pytest.fixture
def mock_jwks(monkeypatch):
    """Points PyJWKClient to our test ES256 public key instead of hitting Supabase over HTTP."""
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    monkeypatch.setattr(
        jwks_client,
        "get_signing_key_from_jwt",
        lambda token: mock_signing_key,
    )


def test_get_my_profile_enforces_rls(mock_jwks):
    client = TestClient(app)

    # Note: user_a_id must exist in auth.users if testing against live Supabase
    # Replace with two real test user UUIDs from Supabase Auth -> Users
    user_a_id = uuid.UUID("03f52d14-e162-4aef-9d64-481ce4820cfc")
    user_b_id = uuid.UUID("f884523c-49bc-4622-8e10-75fc367274fc")

    # Seed User A's profile (User B has no profile or a separate profile)
    with Session(engine) as session:
        profile_a = UserProfile(id=user_a_id, email="user_a@example.com", username="alice")
        session.merge(profile_a)
        session.commit()

    # 1. Request as User A -> Should return Alice's profile
    token_a = mint_test_jwt(user_a_id, "user_a@example.com")
    res_a = client.get("/profiles/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["username"] == "alice"

    # 2. Request as User B -> Postgres RLS hides Alice's row -> Returns 404
    token_b = mint_test_jwt(user_b_id, "user_b@example.com")
    res_b = client.get("/profiles/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 404
