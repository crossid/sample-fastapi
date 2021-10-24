import httpx
from urllib.parse import urlencode
import jwt
from json import dumps
# from jwt import PyJWKClient

from dataclasses import dataclass
from typing import List
from typing import Dict

@dataclass
class Token:
  access_token: str
  id_token: str
  refresh_token: str
  expires_in: int
  token_type: str
  scope: List[str]

class OIDCClient:
  def __init__(self, issuer, client_id, client_secret, redirect_uri) -> None:
    self.issuer = issuer
    self.client_id = client_id
    self.client_secret = client_secret
    self.redirect_uri = redirect_uri
    
    config = httpx.get(issuer + '.well-known/openid-configuration').json()
    self.authorization_endpoint = config['authorization_endpoint']
    self.token_endpoint = config['token_endpoint']
    self.userinfo_endpoint = config['userinfo_endpoint']
    self.jwks_uri = config['jwks_uri']
    self.end_session_endpoint = config['end_session_endpoint']
    # self.jwks_client = PyJWKClient(self.jwks_uri)


  def auth_url(self, state: str, audience: str = '', scope: List[str] = ['openid', 'profile'], nonce: str = '', response_type: str = 'code') -> str:
    
    data = {
      'state': state,
      'scope': ' '.join(scope),
      'response_type': response_type,
      'redirect_uri': self.redirect_uri,
      'client_id': self.client_id
    }

    if audience != '':
      data['audience'] = audience

    if nonce != '':
      data['nonce'] = nonce

    return self.authorization_endpoint + '?' + urlencode(data) 

  async def exchange_token(self, code: str) -> Token:
    async with httpx.AsyncClient() as client:
      tokenJ = (await client.post(self.token_endpoint, data={
          'client_id': self.client_id,
          'client_secret': self.client_secret,
          'redirect_uri': self.redirect_uri,
          'code': code,
          'grant_type': 'authorization_code'
        })).json()

      token = Token(access_token=tokenJ.get('access_token', ''), 
                    id_token=tokenJ.get('id_token', ''), 
                    refresh_token=tokenJ.get('refresh_token', ''), 
                    token_type=tokenJ['token_type'], 
                    expires_in=tokenJ['expires_in'],
                    scope=tokenJ['scope'].split(' ')
                  )

      return token
    
  async def refresh_token(self, refresh_token: str) -> Token:
    async with httpx.AsyncClient() as client:

      tokenJ = (await client.post(self.token_endpoint, data={
          'client_id': self.client_id,
          'client_secret': self.client_secret,
          'refresh_token': refresh_token,
          'grant_type': 'refresh_token'
        })).json()

      token = Token(access_token=tokenJ.get('access_token', ''), 
                    id_token=tokenJ.get('id_token', ''), 
                    refresh_token=tokenJ.get('refresh_token', ''), 
                    token_type=tokenJ['token_type'], 
                    expires_in=tokenJ['expires_in'],
                    scope=tokenJ['scope'].split(' ')
              )

      return token

         
  async def decode(self, token: str, nonce: str = '', audience: str = '') -> Dict[str, any]:  
    header = jwt.get_unverified_header(token)
    signing_key = None

    async with httpx.AsyncClient() as client:
      keyset = (await client.get(self.jwks_uri)).json()['keys']
      signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(next(key for key in keyset if key['kid'] == header['kid']))

    data = jwt.decode(
      token,
      signing_key,
      algorithms=['RS256'],
      options={'verify_aud': False}
    )

    if data['iss'] != self.issuer:
      raise Exception('Mismatched issuer') 

    if nonce != '' and data['nonce'] != nonce:
      raise Exception('Mismatched nonce')

    if audience != '' and data['aud'] != audience:
      raise Exception('Mismatched audience') 

    return data