#PyJWKClient fetches and caches Supabase's public keys from /auth/v1/.well-known/jwks.json, verifies ES256/RS256 signatures, and scopes the Postgres transaction to the authenticated role using SET LOCAL
import json
import os
from typing import Annotated # Annoted[type,param] <==> specify the type of the second parameter

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy import text
from sqlmodel import Session

from database import engine

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not configured in environment variables")

BASE_AUTH_URL = f"{SUPABASE_URL.rstrip('/')}/auth/v1"
JWKS_URL = f"{BASE_AUTH_URL}/.well-known/jwks.json"  #JWKS stands for Json Web key Set

# Fetches and caches public signing keys (auto-refreshes if Supabase rotates keys)
jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)  ##server
security = HTTPBearer() #request #reading the header # allows swagger as well to set a field for the bearer


def get_jwt_claims(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """Verifies a Supabase Bearer JWT using ES256 / RS256 public keys."""
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=BASE_AUTH_URL,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.PyJWKClientError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unable to verify token signing key: {e}",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


def get_rls_session(
    claims: Annotated[dict, Depends(get_jwt_claims)],
):
    """
    Opens a transactional SQLModel Session scoped to the authenticated user.
    Supabase's auth.uid() and auth.jwt() read these transaction-local variables.
    """
    with Session(engine) as session:
        with session.begin():
            # 1. Switch from 'postgres' (BYPASSRLS) to 'authenticated'
            session.exec(text("SET LOCAL role = 'authenticated';"))

            # 2. Inject verified JWT claims so auth.uid() resolves to claims['sub']
            session.exec(
                text("SELECT set_config('request.jwt.claims', :claims, true);"),
                params={"claims": json.dumps(claims)},
            )

            yield session
            # Automatically commits (or rolls back on exception) and resets role/claims


RLSSessionDep = Annotated[Session, Depends(get_rls_session)] # RLSSessionDep should be passed on routes that need authentication(RLS enforced) instead  of using  default "postgre" account which doesn't enforce RLS by default

#When a route uses RLSSessionDep, PostgreSQL automatically enforces your RLS policies (USING ((SELECT auth.uid()) = id)) on every query: