import pytest
from pydantic import ValidationError

from src.interfaces.api.schemas.target_schemas import TargetCredentialsRequest


def test_email_required_for_email_password_login_type():
    with pytest.raises(ValidationError):
        TargetCredentialsRequest(login_type="email_password", email=None, password="x")


def test_email_password_login_type_accepts_email():
    req = TargetCredentialsRequest(login_type="email_password", email="a@b.com", password="x")
    assert req.email == "a@b.com"


def test_single_password_login_type_does_not_require_email():
    req = TargetCredentialsRequest(login_type="single_password", password="shop123")
    assert req.email is None
    assert req.password == "shop123"


def test_login_type_defaults_to_email_password():
    req = TargetCredentialsRequest(email="a@b.com", password="x")
    assert req.login_type == "email_password"
