import base64
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from mercaribot.scraper.dpop import DPoPGenerator


def test_dpop_token_structure():
    gen = DPoPGenerator()
    url = "https://api.mercari.jp/v2/entities:search"
    token = gen.generate(url=url, method="POST")

    parts = token.split(".")
    assert len(parts) == 3, "DPoP token must have 3 dot-separated parts."

    # Decode header
    header_b64 = parts[0] + "=" * (-len(parts[0]) % 4)
    header = json.loads(base64.urlsafe_b64decode(header_b64).decode("utf-8"))
    assert header["typ"] == "dpop+jwt"
    assert header["alg"] == "ES256"
    assert header["jwk"]["crv"] == "P-256"
    assert header["jwk"]["kty"] == "EC"
    assert "x" in header["jwk"]
    assert "y" in header["jwk"]

    # Decode payload
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
    assert payload["htu"] == url
    assert payload["htm"] == "POST"
    assert "iat" in payload
    assert "jti" in payload


def test_dpop_signature_validity():
    gen = DPoPGenerator()
    url = "https://api.mercari.jp/v2/entities:search"
    token = gen.generate(url=url, method="POST")

    parts = token.split(".")
    data_to_sign = f"{parts[0]}.{parts[1]}".encode()

    # Reconstruct public key from JWK
    header_b64 = parts[0] + "=" * (-len(parts[0]) % 4)
    header = json.loads(base64.urlsafe_b64decode(header_b64).decode("utf-8"))
    jwk = header["jwk"]

    x_bytes = base64.urlsafe_b64decode(jwk["x"] + "=" * (-len(jwk["x"]) % 4))
    y_bytes = base64.urlsafe_b64decode(jwk["y"] + "=" * (-len(jwk["y"]) % 4))

    x = int.from_bytes(x_bytes, byteorder="big")
    y = int.from_bytes(y_bytes, byteorder="big")

    public_numbers = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())
    public_key = public_numbers.public_key()

    # Decode IEEE P1363 signature (r || s)
    sig_b64 = parts[2] + "=" * (-len(parts[2]) % 4)
    raw_sig = base64.urlsafe_b64decode(sig_b64)
    assert len(raw_sig) == 64

    r = int.from_bytes(raw_sig[:32], byteorder="big")
    s = int.from_bytes(raw_sig[32:], byteorder="big")

    dss_signature = utils.encode_dss_signature(r, s)

    # Cryptographic verification
    public_key.verify(dss_signature, data_to_sign, ec.ECDSA(hashes.SHA256()))
