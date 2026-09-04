import json

from cryptography.fernet import Fernet

from src.config.settings import get_settings


def _fernet() -> Fernet:
    # Same FERNET_KEY / same algorithm as infrastructure/proxy/encryption.py
    # (Phase 2) — a separate tiny module rather than reusing that one
    # directly because proxies store the ciphertext as raw BYTEA
    # (`password_encrypted: LargeBinary`), while target credentials must live
    # inside a JSON column as a plain string. Same key material either way.
    return Fernet(get_settings().fernet_key.encode())


def encrypt_str(plaintext: str) -> str:
    """Returns a JSON-safe (ASCII text) Fernet token."""
    return _fernet().encrypt(plaintext.encode()).decode("ascii")


def decrypt_str(token: str) -> str:
    return _fernet().decrypt(token.encode("ascii")).decode()


def encrypt_json(data: dict) -> str:
    """§Product-readiness credentials feature — encrypts an entire dict (e.g.
    {"email": ..., "password": ...}) as one opaque token, so nothing in it
    (not even the email) ever touches the DB in plaintext."""
    return encrypt_str(json.dumps(data))


def decrypt_json(token: str) -> dict:
    return json.loads(decrypt_str(token))
