import uuid

import pytest

from src.application.use_cases.target_credentials_use_cases import (
    CREDENTIALS_CONFIG_KEY,
    DeleteTargetCredentialsUseCase,
    SetTargetCredentialsUseCase,
)
from src.domain.entities.target import Target
from src.domain.interfaces.target_repository import TargetRepository
from src.infrastructure.security.encryption import decrypt_json


class FakeTargetRepository(TargetRepository):
    """In-memory stand-in — enough to exercise the use cases' read-modify-write
    logic without a real database."""

    def __init__(self, targets: dict[uuid.UUID, Target]) -> None:
        self._targets = targets

    async def add(self, target: Target) -> Target:
        self._targets[target.id] = target
        return target

    async def get(self, target_id: uuid.UUID) -> Target | None:
        return self._targets.get(target_id)

    async def get_by_base_url(self, base_url: str) -> Target | None:
        return next((t for t in self._targets.values() if t.base_url == base_url), None)

    async def list_all(self) -> list[Target]:
        return list(self._targets.values())

    async def update_basic_info(self, target_id, *, name=None, base_url=None, target_type=None) -> None:
        target = self._targets[target_id]
        if name is not None:
            target.name = name
        if base_url is not None:
            target.base_url = base_url
        if target_type is not None:
            target.target_type = target_type

    async def delete(self, target_id) -> None:
        del self._targets[target_id]

    async def update_config(self, target_id: uuid.UUID, config: dict) -> None:
        self._targets[target_id].config = config


@pytest.fixture
def target() -> Target:
    return Target(name="Example", base_url="https://example.com")


@pytest.fixture
def repo(target: Target) -> FakeTargetRepository:
    return FakeTargetRepository({target.id: target})


async def test_set_credentials_stores_an_encrypted_blob_not_plaintext(repo, target):
    await SetTargetCredentialsUseCase(repo).execute(target.id, "user@example.com", "hunter2")

    stored = target.config[CREDENTIALS_CONFIG_KEY]
    assert "hunter2" not in stored
    assert "user@example.com" not in stored
    assert decrypt_json(stored) == {
        "email": "user@example.com",
        "password": "hunter2",
        "login_type": "email_password",
    }


async def test_set_credentials_single_password_mode_ignores_email(repo, target):
    """Shopify storefront / cPanel-style forms — no email field at all."""
    await SetTargetCredentialsUseCase(repo).execute(target.id, None, "shop123", login_type="single_password")

    stored = decrypt_json(target.config[CREDENTIALS_CONFIG_KEY])
    assert stored == {"email": None, "password": "shop123", "login_type": "single_password"}


async def test_set_credentials_preserves_other_config_keys(repo, target):
    target.config = {"viewport": {"width": 1024, "height": 768}}
    await SetTargetCredentialsUseCase(repo).execute(target.id, "user@example.com", "hunter2")

    assert target.config["viewport"] == {"width": 1024, "height": 768}
    assert CREDENTIALS_CONFIG_KEY in target.config


async def test_delete_credentials_removes_only_the_credentials_key(repo, target):
    target.config = {"viewport": {"width": 1024, "height": 768}, CREDENTIALS_CONFIG_KEY: "whatever"}
    await DeleteTargetCredentialsUseCase(repo).execute(target.id)

    assert CREDENTIALS_CONFIG_KEY not in target.config
    assert target.config["viewport"] == {"width": 1024, "height": 768}


async def test_delete_credentials_is_a_no_op_when_none_were_set(repo, target):
    await DeleteTargetCredentialsUseCase(repo).execute(target.id)  # should not raise
    assert target.config == {}


async def test_set_credentials_raises_for_unknown_target(repo):
    with pytest.raises(ValueError):
        await SetTargetCredentialsUseCase(repo).execute(uuid.uuid4(), "a@b.com", "x")
