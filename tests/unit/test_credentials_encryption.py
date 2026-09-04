from src.infrastructure.security.encryption import decrypt_json, decrypt_str, encrypt_json, encrypt_str


def test_str_round_trip():
    token = encrypt_str("hunter2")
    assert token != "hunter2"
    assert decrypt_str(token) == "hunter2"


def test_json_round_trip():
    data = {"email": "user@example.com", "password": "hunter2"}
    token = encrypt_json(data)
    assert decrypt_json(token) == data


def test_encrypted_token_never_contains_the_plaintext():
    token = encrypt_json({"email": "user@example.com", "password": "SuperSecret!"})
    assert "SuperSecret!" not in token
    assert "user@example.com" not in token


def test_token_is_json_safe_ascii_text():
    token = encrypt_json({"email": "a@b.com", "password": "p"})
    assert isinstance(token, str)
    token.encode("ascii")  # raises if it isn't pure ASCII
