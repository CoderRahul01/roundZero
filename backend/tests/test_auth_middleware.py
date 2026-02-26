import time
import unittest
from unittest.mock import patch

import jwt

from middleware import (
    AuthTokenVerifier,
    TokenValidationConfig,
    _decode_neon_jwt,
    _audience_variants,
    _issuer_variants,
    _resolve_neon_jwks_url,
)


class AuthMiddlewareTests(unittest.TestCase):
    @patch("middleware.jwt.decode")
    def test_decode_neon_jwt_retries_without_issuer_on_mismatch(self, mock_decode) -> None:
        mock_decode.side_effect = [jwt.InvalidIssuerError("Invalid issuer"), {"sub": "user_123"}]

        payload = _decode_neon_jwt(
            token="header.payload.sig",
            signing_key="test-signing-key",
            audiences=["authenticated"],
            issuers=["https://issuer.example/auth"],
        )

        self.assertEqual(payload["sub"], "user_123")
        self.assertEqual(mock_decode.call_count, 2)

        first_kwargs = mock_decode.call_args_list[0].kwargs
        second_kwargs = mock_decode.call_args_list[1].kwargs

        self.assertTrue(first_kwargs["options"]["verify_iss"])
        self.assertIn("issuer", first_kwargs)
        self.assertFalse(second_kwargs["options"]["verify_iss"])
        self.assertNotIn("issuer", second_kwargs)

    def test_audience_variants_appends_authenticated(self) -> None:
        self.assertEqual(_audience_variants(None), ["authenticated"])
        self.assertEqual(_audience_variants("authenticated"), ["authenticated"])
        self.assertEqual(
            _audience_variants("https://neon.example,custom"),
            ["https://neon.example", "custom", "authenticated"],
        )

    def test_issuer_variants_supports_trailing_slash(self) -> None:
        self.assertEqual(
            _issuer_variants("https://neon.example/auth"),
            ["https://neon.example/auth", "https://neon.example/auth/"],
        )
        self.assertEqual(
            _issuer_variants("https://neon.example/auth/"),
            ["https://neon.example/auth/", "https://neon.example/auth"],
        )
        self.assertEqual(_issuer_variants(None), [])

    def test_resolve_jwks_url_prefers_explicit_value(self) -> None:
        config = TokenValidationConfig(
            jwt_secret="secret",
            neon_auth_url="https://auth.neon.example",
            neon_auth_jwks_url="https://jwks.neon.example/keys.json",
            neon_auth_issuer=None,
            neon_auth_audience=None,
            allow_legacy_hs256_auth=True,
        )

        self.assertEqual(_resolve_neon_jwks_url(config), "https://jwks.neon.example/keys.json")

    def test_resolve_jwks_url_derives_from_auth_url(self) -> None:
        config = TokenValidationConfig(
            jwt_secret="secret",
            neon_auth_url="https://auth.neon.example/",
            neon_auth_jwks_url=None,
            neon_auth_issuer=None,
            neon_auth_audience=None,
            allow_legacy_hs256_auth=True,
        )

        self.assertEqual(
            _resolve_neon_jwks_url(config),
            "https://auth.neon.example/.well-known/jwks.json",
        )

    def test_verify_legacy_hs256_token(self) -> None:
        config = TokenValidationConfig(
            jwt_secret="roundzero-secret",
            neon_auth_url=None,
            neon_auth_jwks_url=None,
            neon_auth_issuer=None,
            neon_auth_audience=None,
            allow_legacy_hs256_auth=True,
        )
        verifier = AuthTokenVerifier(config)

        token = jwt.encode(
            {"sub": "user_123", "exp": int(time.time()) + 120},
            config.jwt_secret,
            algorithm="HS256",
        )

        payload = verifier.verify(token)

        self.assertEqual(payload["sub"], "user_123")

    def test_verify_rejects_legacy_token_when_fallback_disabled(self) -> None:
        config = TokenValidationConfig(
            jwt_secret="roundzero-secret",
            neon_auth_url=None,
            neon_auth_jwks_url=None,
            neon_auth_issuer=None,
            neon_auth_audience=None,
            allow_legacy_hs256_auth=False,
        )
        verifier = AuthTokenVerifier(config)

        token = jwt.encode(
            {"sub": "user_123", "exp": int(time.time()) + 120},
            "different-secret",
            algorithm="HS256",
        )

        with self.assertRaises(jwt.InvalidTokenError):
            verifier.verify(token)


if __name__ == "__main__":
    unittest.main()
