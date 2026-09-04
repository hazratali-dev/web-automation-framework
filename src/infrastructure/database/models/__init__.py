"""All SQLAlchemy models, imported here so `Base.metadata` is complete for
Alembic autogenerate and for `Base.metadata.create_all()`."""

from src.infrastructure.database.models.alert import Alert, AlertRule
from src.infrastructure.database.models.audit_log import AuditLog
from src.infrastructure.database.models.base import Base
from src.infrastructure.database.models.metric import Metric
from src.infrastructure.database.models.proxy import Proxy
from src.infrastructure.database.models.runtime_config import RuntimeConfig
from src.infrastructure.database.models.session import BrowserSession
from src.infrastructure.database.models.target import Target
from src.infrastructure.database.models.task import Task
from src.infrastructure.database.models.task_run import TaskRun
from src.infrastructure.database.models.user import User

__all__ = [
    "Base",
    "User",
    "Proxy",
    "Target",
    "Task",
    "TaskRun",
    "BrowserSession",
    "Metric",
    "AlertRule",
    "Alert",
    "AuditLog",
    "RuntimeConfig",
]
