"""Isolate the exact line inside middleware.py that blocks."""
import subprocess, time

lines = [
    ("jwt+starlette", "import jwt; from starlette.middleware.base import BaseHTTPMiddleware; from settings import get_settings"),
    ("AuthTokenVerifier full", """
import jwt
from settings import get_settings

def _resolve_neon_jwks_url(neon_auth_jwks_url, neon_auth_url):
    if neon_auth_jwks_url:
        return neon_auth_jwks_url.rstrip("/")
    if neon_auth_url:
        return f"{neon_auth_url.rstrip('/')}/.well-known/jwks.json"
    return None

s = get_settings()
jwks_url = _resolve_neon_jwks_url(s.neon_auth_jwks_url, s.neon_auth_url)
print(f'JWKS URL: {jwks_url[:40]}...')
"""),
    ("PyJWKClient", """
import jwt
from settings import get_settings

s = get_settings()
jwks_url = s.neon_auth_jwks_url
print(f'Creating PyJWKClient for {jwks_url[:30]}...')
client = jwt.PyJWKClient(jwks_url)
print('PyJWKClient created (no fetch yet)')
"""),
    ("PyJWKClient.get_jwk_data", """
import jwt
from settings import get_settings

s = get_settings()
jwks_url = s.neon_auth_jwks_url
client = jwt.PyJWKClient(jwks_url)
print('Fetching JWKS...')
data = client.fetch_data()
print(f'Got JWKS data: {str(data)[:60]}')
"""),
]

for name, stmt in lines:
    t0 = time.time()
    try:
        result = subprocess.run(
            ["python", "-c", stmt.strip()],
            capture_output=True, text=True, timeout=5, cwd="."
        )
        elapsed = time.time() - t0
        out = (result.stdout + result.stderr).strip()[:150]
        print(f"[{elapsed:.1f}s] {name}: {out}")
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"[{elapsed:.1f}s] 🚨 HUNG: {name}")
