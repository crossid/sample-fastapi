import os
from base64 import b64encode
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, Request, status, Depends, Security, Header
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from fastapi.security import (
    SecurityScopes
)

from starlette.middleware.sessions import SessionMiddleware

from jose import JWTError
from pydantic import BaseModel, ValidationError

templates = Jinja2Templates(directory="templates")
from client import OIDCClient

class TokenData(BaseModel):
    user_id: Optional[str] = None
    scopes: List[str] = []

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="some-random-string")

class OidcClientInject:
    def __init__(self):
        self.oidc_client =  OIDCClient(os.getenv('ISSUER_BASE_URL'), 
                      os.getenv('CLIENT_ID'), 
                      os.getenv('CLIENT_SECRET'), 
                      os.getenv('REDIRECT_URI'))

    def __call__(self):
       return self.oidc_client

client_injector = OidcClientInject()

async def get_user_from_token(security_scopes: SecurityScopes, authorization: str = Header(), client: OIDCClient = Depends(client_injector)):
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

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get('/login')
async def login(request: Request, client: OIDCClient = Depends(client_injector)):
    nonce = b64encode(os.urandom(32)).decode()
    state = b64encode(os.urandom(32)).decode()

    request.session['nonce'] = nonce
    request.session['state'] = state

    auth_url = client.auth_url(state, scope=['openid', 'profile', 'email'], nonce = nonce)

    return RedirectResponse(auth_url)

@app.get("/callback")
async def handle_callback(code: str, state: str, request: Request, client: OIDCClient = Depends(client_injector)):
    if code == '':
        raise HTTPException(status_code=400, detail="bad or missing code")

    saved_state = request.session.get('state', '') 
    if saved_state == '' or saved_state != state:
        raise HTTPException(status_code=400, detail="bad state")

    request.session['state'] = ''

    tokens = await client.exchange_token(code)

    saved_nonce = request.session.get('nonce')

    id_token = await client.decode(tokens.id_token, nonce=saved_nonce)

    logout_redirect_url = os.getenv('REDIRECT_URI').replace('/callback', '')
    logout_url = client.end_session_endpoint + '?id_token_hint=' +  tokens.id_token + '&post_logout_redirect_uri=' + logout_redirect_url

    return templates.TemplateResponse('post_callback.html', {'request': request, 'name': id_token['email'], 'access_token': tokens.access_token, 'logout_url': logout_url})

@app.get('/protected')
async def protected(current_user: TokenData = Security(get_user_from_token, scopes=["profile"])):
  return 'you are authorized'