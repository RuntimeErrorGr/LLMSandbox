from alembic import op
import sqlalchemy as sa


revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('chat_messages')


def downgrade() -> None:
    op.create_table('chat_messages',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('role', sa.VARCHAR(length=16), nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('created_at', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
