"""seed headless runtime_config default

Revision ID: f09733676eaa
Revises: 44b3551330e1
Create Date: 2026-09-04 20:51:00.999836

"""
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f09733676eaa'
down_revision: Union[str, None] = '44b3551330e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

runtime_config = sa.table(
    "runtime_config",
    sa.column("key", sa.String),
    sa.column("value", sa.String),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    # §UI-update — dashboard-toggleable headless mode (§5.6). Default false:
    # user explicitly wants the browser window visible, not hidden.
    op.bulk_insert(
        runtime_config,
        [{"key": "headless", "value": "false", "updated_at": datetime.now(timezone.utc)}],
    )


def downgrade() -> None:
    op.execute(runtime_config.delete().where(runtime_config.c.key == "headless"))
