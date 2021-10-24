import os
from fastapi import FastAPI, FastAPI, HTTPException, status, Depends, Security, Header
from typing import List, Optional
from fastapi.security import (
    SecurityScopes
)
from jose import JWTError
from pydantic import BaseModel, ValidationError


from client import OIDCClient

class TokenData(BaseModel):
    user_id: Optional[str] = None
    scopes: List[str] = []

app = FastAPI()

class OidcClientInject:
    def __init__(self):
        self.oidc_client =  OIDCClient(os.getenv('ISSUER_BASE_URL'), 
                      os.getenv('CLIENT_ID'), 
                      os.getenv('CLIENT_SECRET'), 
                      os.getenv('REDIRECT_URI'))

    def __call__(self):
       return self.oidc_client

client_injector = OidcClientInject()

async def get_user_from_token(
    security_scopes: SecurityScopes, authorization: str = Header(None), client: OIDCClient = Depends(client_injector)):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = f"Bearer"
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        token = authorization.replace('Bearer ', '')
        payload = await client.decode(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_scopes = payload.get("scp", [])
        token_data = TokenData(scopes=token_scopes, user_id=user_id)
    except (JWTError, ValidationError):
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    return token_data


@app.get('/protected')
async def protected(current_user: TokenData = Security(get_user_from_token, scopes=["profile"])):
  return 'you are authorized'