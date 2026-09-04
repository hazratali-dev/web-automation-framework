from cryptography.fernet import Fernet

from src.config.settings import get_settings


def _fernet() -> Fernet:
    return Fernet(get_settings().fernet_key.encode())


def encrypt_password(plaintext: str) -> bytes:
    """§8 — proxy passwords are Fernet-encrypted at rest, never stored/logged
    as plaintext."""
    return _fernet().encrypt(plaintext.encode())


def decrypt_password(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode()
