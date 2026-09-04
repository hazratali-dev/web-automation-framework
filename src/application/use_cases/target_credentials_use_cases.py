import uuid

from src.domain.interfaces.target_repository import TargetRepository
from src.infrastructure.security.encryption import encrypt_json

CREDENTIALS_CONFIG_KEY = "credentials_encrypted"


class SetTargetCredentialsUseCase:
    """§Product-readiness — dashboard-managed login credentials, never in
    code/.env. The whole {"email", "password"} object is encrypted as one
    opaque token before it ever touches `targets.config` (§8)."""

    def __init__(self, target_repo: TargetRepository) -> None:
        self._target_repo = target_repo

    async def execute(self, target_id: uuid.UUID, email: str, password: str) -> None:
        target = await self._target_repo.get(target_id)
        if target is None:
            raise ValueError(f"Target {target_id} not found")

        config = dict(target.config or {})
        config[CREDENTIALS_CONFIG_KEY] = encrypt_json({"email": email, "password": password})
        await self._target_repo.update_config(target_id, config)


class DeleteTargetCredentialsUseCase:
    def __init__(self, target_repo: TargetRepository) -> None:
        self._target_repo = target_repo

    async def execute(self, target_id: uuid.UUID) -> None:
        target = await self._target_repo.get(target_id)
        if target is None:
            raise ValueError(f"Target {target_id} not found")

        config = dict(target.config or {})
        config.pop(CREDENTIALS_CONFIG_KEY, None)
        await self._target_repo.update_config(target_id, config)
