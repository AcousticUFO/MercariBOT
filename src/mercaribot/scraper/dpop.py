"""DPoP (Demonstrating Proof-of-Possession) token generator for Mercari Japan API."""

from __future__ import annotations

import base64
import json
import time
import uuid

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils


def _int_to_bytes(n: int, length: int = 32) -> bytes:
    """Convert integer to big-endian bytes with fixed length."""
    return n.to_bytes(length, byteorder="big")


def _bytes_to_b64url(b: bytes) -> str:
    """Encode bytes to URL-safe base64 without padding."""
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _str_to_b64url(s: str) -> str:
    """Encode string to URL-safe base64 without padding."""
    return _bytes_to_b64url(s.encode("utf-8"))


class DPoPGenerator:
    """
    Manages ECDSA P-256 key pair and generates compliant DPoP JWTs for Mercari.
    Reuses the private key across requests to save CPU, with support for key rotation.
    """

    def __init__(self, key_lifetime_seconds: float = 3600.0):
        self.key_lifetime_seconds = key_lifetime_seconds
        self._private_key: ec.EllipticCurvePrivateKey | None = None
        self._key_created_at: float = 0.0
        self._cached_jwk_header: str | None = None
        self.rotate_key()

    def rotate_key(self) -> None:
        """Generate a new ECDSA P-256 private key and pre-compute header."""
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._key_created_at = time.time()

        public_numbers = self._private_key.public_key().public_numbers()
        jwk = {
            "crv": "P-256",
            "kty": "EC",
            "x": _bytes_to_b64url(_int_to_bytes(public_numbers.x, 32)),
            "y": _bytes_to_b64url(_int_to_bytes(public_numbers.y, 32)),
        }
        header = {
            "typ": "dpop+jwt",
            "alg": "ES256",
            "jwk": jwk,
        }
        self._cached_jwk_header = _str_to_b64url(json.dumps(header, separators=(",", ":")))

    def generate(self, url: str, method: str = "POST", jti: str | None = None) -> str:
        """
        Generate a signed DPoP token string for the target URL and method.
        """
        now = time.time()
        if (
            self._private_key is None
            or self._cached_jwk_header is None
            or (now - self._key_created_at) > self.key_lifetime_seconds
        ):
            self.rotate_key()

        if jti is None:
            jti = str(uuid.uuid4())

        payload = {
            "iat": int(now),
            "jti": jti,
            "htu": url,
            "htm": method.upper(),
        }
        payload_b64 = _str_to_b64url(json.dumps(payload, separators=(",", ":")))
        data_to_sign = f"{self._cached_jwk_header}.{payload_b64}"

        signature = self._private_key.sign(
            data_to_sign.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )

        r, s = utils.decode_dss_signature(signature)
        raw_sig = _int_to_bytes(r, 32) + _int_to_bytes(s, 32)
        sig_b64 = _bytes_to_b64url(raw_sig)

        return f"{data_to_sign}.{sig_b64}"
